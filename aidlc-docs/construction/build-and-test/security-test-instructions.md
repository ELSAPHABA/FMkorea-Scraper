# Security Test Instructions - UOW-007 CLI Adapter

## Security Scope

UOW-007 security checks focus on terminal adapter behavior:

- import safety
- secret-safe error output
- Proxy password handling
- plaintext `.env` update boundary
- User-Agent import validation
- no live network in default tests
- no raw cookie persistence by CLI

## Default Security Test Command

```powershell
$env:PYTHONPATH='src'
python -m pytest `
  tests\test_cli_adapter.py::test_import_user_agents_rejects_blank_without_overwriting `
  tests\test_cli_adapter.py::test_update_proxy_env_preserves_unrelated_lines `
  tests\test_cli_adapter.py::test_print_error_uses_safe_summary_and_debug_gate `
  tests\test_cli_adapter.py::test_cli_import_has_no_runtime_side_effects `
  -q --tb=short
```

Covered:

- blank User-Agent source does not overwrite existing destination
- `.env` updater changes only documented `FMKOREA_PROXY_*` keys
- safe error output does not expose secret details
- CLI import does not create `.env` or `user-agents.txt`

## Dependency Check

```powershell
python -m pip check
```

Latest result:

```text
No broken requirements found.
```

## Deferred Security Work

Not covered in UOW-007:

- external vulnerability scanning
- live CAPTCHA/block smoke tests
- Docker secret injection
- PostgreSQL credential handling
- MCP server access control
- AWS IAM policy validation
