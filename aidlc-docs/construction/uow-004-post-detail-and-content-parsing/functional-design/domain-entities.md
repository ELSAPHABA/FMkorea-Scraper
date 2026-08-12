# Domain Entities - UOW-004 Post Detail And Content Parsing

## Entity Overview

UOW-004 defines parser services and domain entities for transforming FMKorea detail pages into UOW-001 `PostResult` objects.

These entities describe implementation contracts, not necessarily final file names.

## Service Components

### PostDetailService

Responsibilities:

- accept `PostCandidate` or `PostRequest`
- build or reuse the detail URL
- fetch detail HTML through injected UOW-002 HTTP
- call `PostDetailParser`
- fetch discovered comment pages sequentially when supported
- return final `PostResult`

Does not own:

- queue consumption
- checkpoint save
- JSONL output
- media download
- storage write

### PostDetailParser

Responsibilities:

- coordinate metadata, content, attachment, media, and comment parsers
- validate required identity fields
- merge warnings into `PostResult.metadata`
- produce `PostResult`

### MetadataParser

Responsibilities:

- parse `#bd_capture`
- parse title, author, date, counters, category
- resolve document ID and board ID
- resolve canonical URL
- apply candidate fallback only when detail value is missing

### CanonicalUrlResolver

Responsibilities:

- compare current URL, canonical URL, and `.document_address a.a`
- normalize URL
- extract `document_srl`
- resolve missing `board_id` when possible

### AttachmentParser

Responsibilities:

- parse `.rd_file a[data-href]`
- extract `file_srl`, `sid`, `mid`, filename, URL, and size/download text
- provide attachment lookup by `file_srl`

### ContentParser

Responsibilities:

- locate the content container
- traverse DOM in order
- emit `BodyContent`
- build `content.text`
- collect safe content parse warnings

### MediaBlockParser

Responsibilities:

- parse image blocks
- parse FMKorea video blocks
- parse YouTube blocks
- parse X/Twitter blocks
- avoid duplicate link/media blocks

### CommentParser

Responsibilities:

- parse `.fdb_lst_ul > li`
- create flat `Comment` values
- detect BEST status
- parse reactions
- infer reply depth and parent when safe
- record safe item-level warnings

### MediaSummaryBuilder

Responsibilities:

- derive top-level `media` list from media-bearing content blocks
- keep media metadata aligned with content block order
- leave file path/object key empty until storage unit

### ParseWarningCollector

Responsibilities:

- collect recoverable parser warnings
- keep warning payloads safe
- expose warnings for `PostResult.metadata`

## Data Entities

### PostDetailInput

Logical input shape:

- `candidate`
- or `post_request`
- optional candidate metadata fallback

Purpose:

- lets library callers parse a candidate or a direct post request through the same service path

### PostResult

Existing UOW-001 model used as final output.

UOW-004 fills:

- `schema_version`
- `scraped_at`
- `site_id`
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
- `reactions`
- `comment_count`
- `content`
- `attachments`
- `media`
- `comments`
- `metadata`

### CategoryInfo

Fields:

- `category_id`
- `name`
- `url`

Source:

- `a.category[href*="category="]`
- candidate category hint fallback

### AuthorInfo

Fields:

- `nickname`
- `member_srl`
- `level`
- `profile_url`

Sources:

- `.rd_hd .member_plate`
- `.meta .member_plate` for comments
- `member_<member_srl>` class
- `img.level[alt]`
- `img.level[title]`

### ReactionInfo

Used for:

- post reactions
- comment reactions

Fields:

- `up_count`
- `down_count`
- `score`

Rule:

- `score = up_count - down_count`

## Content Block Entities

### BodyContent

Fields:

- `text`
- `blocks`

Rules:

- block `order` values are unique
- blocks preserve DOM order

### TextBlock

Fields:

- `order`
- `type="text"`
- `text`

### ImageBlock

Existing model, extended during code generation with optional fields:

- `file_srl`
- `width`
- `height`
- `download_url`
- `download`

Existing fields remain:

- `url`
- `original_url`
- `alt`
- `file_path`
- `object_key`

### FmkVideoBlock

Existing model, extended during code generation with optional fields:

- `file_srl`
- `download_url`
- `name`
- `upload_date`
- `width`
- `height`
- `download`

Existing fields remain:

- `video_url`
- `poster_url`
- `description`
- `duration`
- `file_path`
- `object_key`

### YouTubeBlock

Existing model, extended during code generation with optional field:

- `start_seconds`

Existing fields remain:

- `url`
- `video_id`
- `embed_url`
- `title`

### XBlock

Existing model, extended/normalized during code generation with optional fields:

- `tweet_id`
- `embed_url`

Existing fields remain:

- `url`
- `username`
- `status_id`
- `text`

### LinkBlock

Fields:

- `order`
- `type="link"`
- `url`
- `text`
- `title`

### AttachmentBlock

Fields:

- `order`
- `type="attachment"`
- `attachment`

### UnknownEmbedBlock

Used when an embed is recognized as non-text content but not safely classifiable.

Fields:

- `order`
- `provider`
- `url`
- `safe_text`

## Attachment And Media Entities

### Attachment

Existing model, extended during code generation with optional fields:

- `file_srl`
- `sid`
- `mid`
- `download_text`

Existing fields remain:

- `file_name`
- `url`
- `size_text`
- `file_path`
- `object_key`

### MediaItem

Top-level summary entity derived from content blocks.

Existing fields:

- `media_id`
- `media_type`
- `source_block_order`
- `url`
- `file_path`
- `object_key`
- `description`

UOW-004 should not set `file_path` or `object_key` unless a later storage unit supplies them.

## Comment Entities

### Comment

Existing UOW-001 model.

Fields filled by UOW-004:

- `comment_srl`
- `comment_id_raw`
- `source_dom_id`
- `source_order`
- `parent_comment_srl`
- `parent_comment_id_raw`
- `depth`
- `is_best`
- `badges`
- `author`
- `created_at`
- `created_at_raw`
- `content`
- `reactions`
- `permalink`
- `metadata`

### Best Comment

BEST comments are not a separate entity type.

They are `Comment` values with:

- `is_best=true`
- `badges` containing `BEST`

### Reply Comment

Reply comments are `Comment` values with:

- `depth=1`
- `parent_comment_srl` when known

If parent cannot be safely determined, `depth` and parent fields may be null and raw class information is preserved in metadata.

## Warning Entities

### ParseWarning

Logical warning shape:

- `stage`
- `selector`
- `reason`
- `source_order`
- `safe_label`
- `retryable`

Stored under `PostResult.metadata` as a bounded list.

Warnings must be safe to log and must not contain raw HTML.

## Relationships To Other Units

| Unit | Relationship |
|---|---|
| UOW-001 | uses and extends post/comment/content/media models |
| UOW-002 | uses HTTP client/port for detail and comment page requests |
| UOW-003 | consumes `PostCandidate` and candidate metadata fallback |
| UOW-005 | receives `PostResult` or post-level parser failure later |
| UOW-006 | serializes `PostResult`, writes media files, JSONL, failures, reports |
| UOW-009 | consumes parser-stage failure records later |
