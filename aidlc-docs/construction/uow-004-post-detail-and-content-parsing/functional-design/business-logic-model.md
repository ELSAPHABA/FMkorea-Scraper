# Business Logic Model - UOW-004 Post Detail And Content Parsing

## Purpose

UOW-004 turns a single FMKorea post candidate/request into a final UOW-001 `PostResult`.

This unit owns post detail HTML fetching, final metadata parsing, ordered body content parsing, media metadata extraction, attachment parsing, comment/reply parsing, BEST comment fields, and safe parser warnings.

It does not own link collection, queue lifecycle, checkpoint persistence, output storage, media file download/write, CLI prompts, containers, or MCP tools.

## Confirmed Decisions

| Area | Decision |
|---|---|
| Service boundary | Accept `PostCandidate` or `PostRequest`, use injected UOW-002 HTTP, return `PostResult` |
| Model schema | Extend existing UOW-001 models with optional media/attachment fields during code generation |
| Final metadata | Parse from detail page; UOW-003 candidate metadata is fallback only |
| Content container | Use `#bd_capture .rd_body article > .xe_content`, then `#bd_capture .rd_body .xe_content` |
| Text/link rules | Preserve meaningful text/link blocks; skip empty/player/UI/attachment table text and media URL duplicates |
| Image/attachment | Prefer `a.highslide[href]`; match image and `.rd_file a[data-href]` by `file_srl` |
| FMKorea video | Parse static video/source/schema.org metadata into one `fmk_video` block |
| YouTube/X | Parse static URLs and available iframe URLs without requiring browser rendering |
| Media download | UOW-004 returns metadata/download candidates only; file writes are later units |
| Comments | Parse `.fdb_lst_ul` and discovered comment page/fragment URLs sequentially through injected HTTP |
| BEST comments | Keep all comments in one flat list with `is_best=true`, `badges=["BEST"]` |
| Parser failures | Required identity fields fail the post; optional block/comment failures become safe warnings |

## Detail Parse Flow

1. Caller passes a UOW-001 `PostCandidate` or `PostRequest`.
2. `PostDetailService` resolves the detail URL.
3. The service fetches HTML through injected UOW-002 `HttpClient`/`HttpPort`.
4. `PostDetailParser` parses the HTML into intermediate pieces:
   - final post identifiers and canonical URL
   - metadata
   - attachments
   - ordered content blocks
   - media summary
   - comments
   - parse warnings
5. Required field validation checks document identity, canonical URL, and title.
6. Parser warnings are stored in `PostResult.metadata`.
7. The service returns `PostResult`.

## Metadata Flow

Source priority:

1. detail page `#bd_capture`
2. canonical/document address/current URL
3. UOW-003 candidate hints

Parsed fields:

- `board_id`
- `board_name`
- `document_srl`
- `document_id_raw`
- `canonical_url`
- `category`
- `title`
- `author`
- `created_at`
- `created_at_raw`
- `views`
- `reactions.up_count`
- `reactions.down_count`
- `comment_count`
- `attachments`

The detailed page value wins whenever present.

## Content Flow

Container lookup:

1. `#bd_capture .rd_body article > .xe_content`
2. `#bd_capture .rd_body .xe_content`

The parser traverses child nodes in DOM order and emits `content.blocks`.

Supported blocks:

- `text`
- `image`
- `fmk_video`
- `youtube`
- `x`
- `link`
- `attachment`
- `unknown_embed`

`content.text` is derived from text-like blocks after filtering UI/player/attachment-table noise.

## Media Flow

UOW-004 extracts media metadata only.

Download candidates:

- image URL and optional download URL
- FMKorea video URL and optional download URL
- attachment download URL

No file is downloaded and no path/object key is finalized in UOW-004.

Top-level `media` is derived from content blocks with media-bearing types:

- `image`
- `fmk_video`
- `youtube`
- `x`

## Comment Flow

Input sources:

- initial detail page HTML
- discovered comment page/fragment URLs when present

Parsing:

1. Find `.fdb_lst_ul`.
2. Iterate `.fdb_lst_ul > li` in DOM order.
3. Extract numeric comment ID from `li[id^="comment_"]`.
4. Store the raw DOM ID in `source_dom_id`.
5. Assign `source_order` from traversal order.
6. Detect BEST status from `li.comment_best` or `.icon-hit` text `BEST`.
7. Extract author, date, content, up/down reactions.
8. Detect reply depth/parent when DOM structure makes it safe.
9. Append every comment to one flat list.

If no extra comment page URL is found, current-page comments are returned and a safe warning may be recorded.

## Parser Warning Flow

Recoverable parse problems are collected as safe warnings.

Examples:

- optional attachment metadata missing
- individual image metadata malformed
- one comment item cannot be parsed
- ambiguous relative comment date
- unknown embed structure

Post-level failure is reserved for missing required identity fields:

- document ID
- canonical URL/detail URL
- title

## Integration Points

| Unit | Relationship |
|---|---|
| UOW-001 | consumes and may extend `PostResult`, content block, media, attachment, comment models |
| UOW-002 | uses injected HTTP client/port for detail and optional comment page fetches |
| UOW-003 | consumes `PostCandidate` and candidate metadata fallback |
| UOW-005 | later owns worker queue, retry, cancellation, checkpoint lifecycle |
| UOW-006 | later owns JSONL/media/failure/report storage and media file writes |
| UOW-009 | later reprocesses parser-stage failures created from UOW-004 failures |

## Testable Properties

- Detail page values override UOW-003 candidate metadata.
- Content block orders are unique and preserve DOM order.
- Media summary is derived from media-bearing content blocks.
- BEST comments always include `BEST` in badges.
- Comment score equals up count minus down count.
- Optional parser warnings do not expose raw HTML or secrets.
