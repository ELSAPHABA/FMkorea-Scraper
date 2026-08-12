# Business Rules - UOW-004 Post Detail And Content Parsing

## Runtime Boundary Rules

### BR-004-001. Import Side Effects

Importing UOW-004 modules must not:

- make network requests
- read `.env`
- read `user-agents.txt`
- prompt terminal input
- write files
- create queues
- create HTTP clients

### BR-004-002. HTTP Boundary

All network I/O must go through an injected UOW-002 `HttpClient` or `HttpPort`.

UOW-004 must not create a separate HTTP client.

### BR-004-003. No Queue Or Storage

UOW-004 must not:

- consume `asyncio.Queue`
- write JSONL
- save media files
- write failure records
- write checkpoints
- call Garage/S3/PostgreSQL adapters

### BR-004-004. No Media Download

UOW-004 extracts media URLs, metadata, and download candidates only.

Actual file download and storage path/object key finalization belong to later storage/worker units.

## Metadata Rules

### BR-004-005. Final Metadata Source

Final saved metadata must be parsed from the detail page whenever available.

UOW-003 candidate metadata is fallback only.

### BR-004-006. Detail Container

Metadata parsing starts from:

- `#bd_capture`

If `#bd_capture` is missing, the parser may use safe local fallbacks only for required fields. It must record a warning.

### BR-004-007. Required Fields

Post-level parse failure occurs when required identity fields cannot be resolved:

- `document_srl` or `document_id_raw`
- canonical/detail URL
- title

### BR-004-008. Title

Title selector priority:

1. `.rd_hd h1 .np_18px_span`
2. `.rd_hd h1`

### BR-004-009. Author

Author parsing uses:

- `.rd_hd .member_plate`
- `member_<member_srl>` class when present
- `img.level[alt]` or `img.level[title]` for level when present

Missing author details do not fail the post.

### BR-004-010. Counters

Views, recommendation count, and comment count are parsed from `.rd_hd .btm_area .side.fr span` by text labels.

Known labels:

- `조회 수`
- `추천 수`
- `댓글`

Missing or unparsable counters become `null` or default reaction values.

### BR-004-011. Category

Category priority:

1. `a.category[href*="category="]` on the detail page
2. UOW-003 candidate category hint

## Model Extension Rules

### BR-004-012. Backward-Compatible Model Extension

UOW-004 Code Generation may add optional fields to existing UOW-001 models.

Allowed examples:

- image `file_srl`, `width`, `height`, `download_url`, `download`
- video `file_srl`, `download_url`, `name`, `upload_date`, `width`, `height`
- YouTube `start_seconds`
- X `tweet_id`, `embed_url`
- attachment `file_srl`, `sid`, `mid`, download text

Required existing schema behavior must remain compatible.

### BR-004-013. Metadata Use

Stable, documented JSONL fields should become typed optional model fields.

Only unknown, experimental, or low-confidence fields should go into `metadata`.

## Content Rules

### BR-004-014. Content Container Priority

Content container priority:

1. `#bd_capture .rd_body article > .xe_content`
2. `#bd_capture .rd_body .xe_content`

The parser must not use global `.xe_content` alone.

### BR-004-015. DOM Order

Content blocks preserve source DOM order.

Each block must have a unique `order`.

### BR-004-016. Ignored Text

Do not store text from:

- empty tags
- `<br>`-only nodes
- `BeforeDocument`
- `AfterDocument`
- `<!-- __LAZY__ -->`
- player UI controls
- attachment list/table UI
- recommendation/comment/view UI
- obvious advertisement UI

### BR-004-017. Text Blocks

Meaningful text-only nodes become `type="text"` blocks.

Whitespace is normalized.

### BR-004-018. Link Blocks

General `a[href]` and bare URLs become `type="link"` blocks unless they are one of:

- image highslide/original URL
- FMKorea video download URL
- YouTube URL
- X/Twitter URL
- attachment download URL

Those URLs use dedicated block types instead.

### BR-004-019. Content Text

`content.text` is derived from:

- `text` blocks
- `link.text`
- bare URL text when no better label exists

It excludes media player UI, counters, attachment table text, and ad text.

## Media Rules

### BR-004-020. URL Normalization

Protocol-relative URLs starting with `//` must be normalized to `https://`.

Relative URLs must be resolved against `https://www.fmkorea.com`.

### BR-004-021. Image Blocks

Image candidates are content-container `img[src]`.

Exclusions:

- `.mejs__poster-img`
- video player UI images

Image URL priority:

1. parent `a.highslide[href]`
2. `img[src]`

If `data-file-srl` exists, match the same `file_srl` against `.rd_file a[data-href]`.

### BR-004-022. Attachments

Attachment candidates are:

- `.rd_file a[data-href]`

Parse from `data-href` when present:

- `file_srl`
- `sid`
- `mid`

Parse size/download text from `title` or surrounding text when possible.

### BR-004-023. FMKorea Video Blocks

FMKorea video candidates:

- `.auto_media_wrapper`
- `video.mediaelement_video`
- `video > source[type="video/mp4"]`

The parser emits one `fmk_video` block per logical video.

It must not emit each `source` as a duplicate block.

Description is `null` when missing or blank.

### BR-004-024. YouTube Blocks

YouTube candidates:

- `youtube.com/watch`
- `youtu.be/<video_id>`
- `iframe[src*="youtube.com/embed"]` when already in HTML

The parser derives:

- `video_id`
- `embed_url`
- optional `start_seconds`

### BR-004-025. X Blocks

X/Twitter candidates:

- `x.com/<user>/status/<tweet_id>`
- `twitter.com/<user>/status/<tweet_id>`
- `iframe[src*="platform.twitter.com/embed/Tweet.html"]` when already in HTML

The parser derives:

- `tweet_id`
- provider
- `embed_url` when known

## Comment Rules

### BR-004-026. Comment Container

Comment container:

- `.fdb_lst_ul`

Comment items:

- `.fdb_lst_ul > li`

### BR-004-027. Comment ID

Comment ID is parsed from:

- `li[id^="comment_"]`

Only digits are used. Raw DOM ID is stored in `source_dom_id`.

### BR-004-028. Source Order

`source_order` is assigned from encounter order across parsed comment pages.

Polars analysis must not rely on raw array order alone.

### BR-004-029. BEST Comments

BEST detection:

- `li.comment_best`
- or `.icon-hit` text `BEST`

BEST comments remain in the flat `comments` list.

They use:

- `is_best=true`
- `badges=["BEST"]`

### BR-004-030. Comment Author

Author parsing uses:

- `.meta .member_plate`
- `member_<member_srl>` class when present

### BR-004-031. Comment Date

Comment date parsing uses:

- `.meta .date`

Raw text is stored in `created_at_raw`.

Normalized datetime is stored in `created_at` when parseable.

### BR-004-032. Comment Content

Comment content excludes:

- author text
- date text
- recommendation UI
- blame UI
- copy-address UI
- go-to-comment UI

### BR-004-033. Comment Reactions

Reaction selector baseline:

- `li[id^="comment_"] > div.fdb_nav.img_tx span.vote`

Up count:

- `a[title="추천"] .voted_count`

Down count:

- `a[title="비추천"] .blamed_count`

Blank values become `0`.

`score = up_count - down_count`.

### BR-004-034. Replies

If DOM structure safely identifies a reply:

- `depth=1`
- `parent_comment_srl=<parent ID>`

If the parent cannot be determined:

- `depth=null`
- `parent_comment_srl=null`
- raw class/details are preserved in metadata

## Failure Rules

### BR-004-035. Post-Level Failure

Missing required identity fields raises post-level `ParseFailureError`.

This is eligible for later parser-stage retry.

### BR-004-036. Recoverable Warnings

Individual optional parse failures are safe warnings:

- content block parse failure
- one media item parse failure
- one attachment parse failure
- one comment parse failure
- ambiguous optional date

Recoverable warnings are stored in `PostResult.metadata`.

### BR-004-037. Safe Failure Payloads

Warnings and errors must not contain:

- raw HTML
- raw cookies
- proxy credentials
- full secret-bearing query strings

### BR-004-038. CAPTCHA And Block Propagation

CAPTCHA/block/unavailable errors from UOW-002 are not swallowed.

They propagate to UOW-005 so the Job can stop and checkpoint.
