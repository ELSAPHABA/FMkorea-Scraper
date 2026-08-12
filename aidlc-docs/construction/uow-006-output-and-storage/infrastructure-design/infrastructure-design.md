# Infrastructure Design - UOW-006 Output And Storage

## Scope

UOW-006 is not a deployable scraper worker. It defines an importable Python output/storage library used by later units:

- local JSONL post output
- local failure JSONL output
- local final report output
- local media byte storage
- local checkpoint file persistence
- S3-compatible object output through optional dependencies
- file-backed S3 JSONL spool behavior
- storage factory creation from `StorageConfig`
- optional Garage/S3 smoke test contract
- optional Polars JSONL-readiness smoke test

Link collection, post parsing, HTTP media download, worker orchestration, PostgreSQL checkpoint storage, queue/DLQ ownership, CLI prompts, container entrypoints, MCP tools, and AWS CDK resources are handled by later units.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Deployment environment | N/A for standalone UOW-006 service/container deployment |
| Local output layout | `StorageConfig.base_output_path` plus `outputs/<job_id>/<run_id>/` |
| Checkpoint infrastructure | local `Checkpoint.json` only; PostgreSQL checkpoint adapter deferred |
| S3-compatible storage | config and object key contract only; Garage is the default example, SeaweedFS remains replaceable |
| Secrets | S3 credentials are runtime config only and must not be written to outputs, checkpoints, reports, or logs |
| S3 smoke | disabled by default; env-gated write/read/delete smoke only |
| Polars smoke | optional `analysis` extra; skipped when Polars is not installed |
| Generated output safety | runtime artifacts stay under configured base output path or test temp directories |
| Factory boundary | `StorageFactory` accepts an already-built `StorageConfig`; env parsing belongs to adapters |
| Deployment docs | document local/S3 layouts and later handoff points only |

## Deployment Environment

UOW-006 is an importable library layer, not a standalone service.

Required environment:

- Python package build/import environment
- local unit/PBT execution environment
- CI unit/PBT execution environment
- filesystem writable temp directory for tests
- optional S3-compatible endpoint only when smoke tests are explicitly enabled
- optional Polars installation only when analysis smoke tests are explicitly enabled

Not required:

- Docker image owned by UOW-006
- Garage server provisioning
- bucket creation or bucket policy management
- PostgreSQL server
- queue consumer
- hosted service
- MCP server process
- AWS account resources

## Local Filesystem Infrastructure

Local output uses the configured base path:

```text
<base_output_path or cwd>/
  outputs/
    <job_id>/
      <run_id>/
        posts.jsonl
        failures.jsonl
        report.json
        media/
          <board_id>/
            <document_srl_or_raw_id>/
              <media_type>/
                <filename>
  Checkpoint.json
```

Rules:

- `StorageConfig.base_output_path` is the only local output root input.
- If `base_output_path` is missing, the runtime working directory is used.
- `job_id`, `run_id`, board identifiers, post identifiers, media type, and filenames must be sanitized before path construction.
- Resume uses the same `job_id` and a new `run_id`; old JSONL files are not appended after resume.
- Tests must write to temp directories, not repository paths.

## Local Checkpoint Infrastructure

UOW-006 defines only local file checkpoint persistence.

Checkpoint location:

```text
<base_output_path or cwd>/Checkpoint.json
```

Allowed behavior:

- load missing checkpoint as empty state
- write checkpoint JSON atomically
- keep enough safe state for later JobRunner resume/checkpoint advancement
- keep PostgreSQL checkpoint config as a deferred model-level capability only

UOW-006 must not create PostgreSQL tables, migrations, connection pools, or checkpoint adapters.

## S3-Compatible Object Storage Infrastructure

UOW-006 defines an S3-compatible storage contract, not a concrete object-store deployment.

Configuration comes from `StorageConfig.s3`:

- `endpoint_url`
- `bucket`
- optional `prefix`
- optional `region`

Credentials are supplied by runtime environment or adapter configuration. They are not domain data and must not be serialized into JSONL, checkpoint, report, failure records, or logs.

Object keys mirror the local relative layout:

```text
<prefix>/outputs/<job_id>/<run_id>/posts.jsonl
<prefix>/outputs/<job_id>/<run_id>/failures.jsonl
<prefix>/outputs/<job_id>/<run_id>/report.json
<prefix>/outputs/<job_id>/<run_id>/media/<board_id>/<document_srl_or_raw_id>/<media_type>/<filename>
```

Garage is the default S3-compatible target for project documentation and smoke testing. SeaweedFS can later replace it through the same S3-compatible endpoint/bucket/prefix contract.

UOW-006 must not:

- provision Garage
- create buckets
- configure access policies
- depend on Garage-only APIs
- implement custom S3 signing
- require S3 dependencies for local output mode

## S3 JSONL Spool

S3-compatible storage has no native append contract. UOW-006 therefore uses a local file-backed spool:

1. append one JSON line to the run-local spool file
2. flush the spool file
3. upload the complete spool to the same S3 object key
4. report success only after upload succeeds

This applies to:

- `posts.jsonl`
- `failures.jsonl`

The spool file is an implementation artifact and should not be treated as the canonical output when S3 mode is selected.

## Storage Factory Boundary

`StorageFactory` creates storage implementations from an already-built `StorageConfig`.

Allowed factory behavior:

- inspect `output_mode`
- inspect `checkpoint_mode`
- create local output/checkpoint stores
- create S3-compatible output stores only when selected
- lazy-load optional S3 dependencies
- raise clear configuration errors for missing required S3 config

Not allowed in core factory:

- reading process environment
- reading `.env`
- prompting terminal input
- creating Docker/Compose/CDK resources
- creating object-store buckets
- opening PostgreSQL checkpoint storage in UOW-006

CLI, container, MCP, and future platform adapters map environment variables and user input into `StorageConfig` before calling the factory.

## Smoke Test Infrastructure

Default tests do not require external services.

Default test scope:

- local output path derivation
- JSONL append
- failure JSONL redaction
- media path/key generation
- local checkpoint save/load
- S3 key generation with fake store
- S3 spool behavior with fake uploader
- path traversal rejection

Optional S3 smoke activation:

- `FMKOREA_S3_SMOKE_ENABLED=true`
- S3 endpoint URL
- bucket
- access key
- secret key
- optional region
- optional prefix

S3 smoke scope:

- write a small JSONL object
- read or head the object when supported by the test helper
- delete the smoke object when supported by the test helper
- never use production prefixes by default

Optional Polars smoke:

- runs only when the `analysis` extra or Polars dependency is installed
- reads sample `posts.jsonl` using `polars.read_ndjson`
- verifies top-level identity fields and nested content/comment/media readability
- does not perform common-schema normalization

## Generated Artifact Safety

Generated runtime artifacts include:

- `outputs/`
- `*.jsonl`
- media download results
- `Checkpoint.json`
- `report.json`
- S3 spool temp files

Code generation should ensure examples and tests write generated artifacts under configured output paths or temp directories.

Repository source, docs, and package directories must not be used as implicit runtime output locations unless the user explicitly sets `base_output_path` there.

## Shared Infrastructure

No shared infrastructure is created by UOW-006.

Deferred shared infrastructure:

| Infrastructure | Target Unit |
|---|---|
| worker queue and checkpoint advancement | UOW-005 |
| PostgreSQL checkpoint adapter | UOW-008 or later storage/runtime unit |
| Garage server/container provisioning | container/operations/CDK unit |
| SeaweedFS replacement path | later storage evolution behind S3-compatible port |
| SQS/DLQ | later platform/CDK work |
| container env injection | UOW-008 |
| MCP server hosting | UOW-008 or later adapter unit |
| AWS CDK resources | later infrastructure UOW |

## Implementation Impact

Code generation for UOW-006 should not create Docker, Terraform, AWS CDK, database migrations, object storage buckets, queues, scheduler config, or monitoring configuration.

Code generation may create:

- `src/fmkorea_scraper/outputs/` package modules
- local JSONL writer
- output layout/path sanitizer
- local object/media store
- local checkpoint store
- failure/report writers
- optional S3-compatible store
- file-backed S3 JSONL spool
- storage factory
- fake S3 uploader tests
- env-gated S3 smoke test
- optional Polars smoke test

## Deferred Items

- PostgreSQL checkpoint storage
- shared Garage/SeaweedFS deployment
- SQS/DLQ retry queue
- Docker Compose service topology
- AWS CDK resources
- CLI wizard prompts for storage setup
- MCP server storage adapter exposure
