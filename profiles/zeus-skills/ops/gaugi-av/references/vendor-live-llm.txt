# Gaudi Public API

> External API for managing Gaudi content programmatically. Authenticate with `Authorization: Bearer <API_KEY_PLACEHOLDER>`.

## Authentication

All `/v1/*` endpoints require an API key created in Gaudi Studio → Settings → Developers API.
Pass the key as a Bearer token:

```
Authorization: Bearer <API_KEY_PLACEHOLDER>
```

**API keys are tenant-scoped.** The tenant is inferred from the key — do not send `tenant_id` in public API requests. Use `GET /v1/sites` to discover site IDs within your tenant before calling site-specific endpoints (articles, categories, assets).

The plaintext key is shown only once at creation. Revoke keys from the Developers API page when no longer needed.

## Base URL

`https://mosaic-api-1453299254.us-east1.run.app`

## Endpoints

### Sites

- [GET /v1/sites](https://mosaic-api-1453299254.us-east1.run.app/v1/sites): List all sites in your tenant. Requires `read:sites` scope.

#### GET /v1/sites

**Example:**

```bash
curl "https://mosaic-api-1453299254.us-east1.run.app/v1/sites" \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>"
```

**Response:** `200` with `{ "sites": [{ "id", "domain", "locales", "default_locale", "multilingual", "tagline" }, ...] }`

### Authors

- [GET /v1/authors](https://mosaic-api-1453299254.us-east1.run.app/v1/authors): List authors for your tenant. Requires `read:authors` scope.
- [POST /v1/authors](https://mosaic-api-1453299254.us-east1.run.app/v1/authors): Create a new author. Requires `write:authors` scope.
- [PUT /v1/authors/:id](https://mosaic-api-1453299254.us-east1.run.app/v1/authors/:id): Update an author. Requires `write:authors` scope.
- [PUT /v1/authors/:id/reassign](https://mosaic-api-1453299254.us-east1.run.app/v1/authors/:id/reassign): Reassign all articles from one author to another. Requires `write:authors` scope.
- [DELETE /v1/authors/:id](https://mosaic-api-1453299254.us-east1.run.app/v1/authors/:id): Delete an author with no linked articles. Requires `write:authors` scope.

#### GET /v1/authors

**Query parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| q | string | — | Search by name or slug |
| cursor | string | — | Pagination cursor from previous response |
| limit | number | 50 | Page size (1–100) |

**Example:**

```bash
curl "https://mosaic-api-1453299254.us-east1.run.app/v1/authors?limit=20" \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>"
```

**Response:** `200` with `{ "authors": [...], "cursor": string | null }`

#### POST /v1/authors

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Display name (max 120 chars) |
| slug | string | no | URL slug (kebab-case). Auto-generated from name if omitted |
| bio | string | no | Short biography (max 2000 chars) |
| avatar_asset_id | string | no | ID of an existing asset in your tenant |
| email | string | no | Contact email |
| social_links | object | no | `{ twitter?, linkedin?, website? }` |

**Example:**

```bash
curl -X POST https://mosaic-api-1453299254.us-east1.run.app/v1/authors \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "bio": "Tech writer"}'
```

**Response:** `201` with `{ "author": { ... } }`

#### PUT /v1/authors/:id

**Path parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Author ID |

**Request body:** same fields as POST — all optional. Slug is immutable after creation.

**Example:**

```bash
curl -X PUT https://mosaic-api-1453299254.us-east1.run.app/v1/authors/AUTHOR_ID \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "bio": "Updated bio"}'
```

**Response:** `200` with `{ "author": { ... } }`

#### PUT /v1/authors/:id/reassign

Moves every article linked to the source author to a different author across all sites in your tenant.

**Path parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | yes | Source author ID (articles will be moved away from this author) |

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| target_author_id | string | yes | Destination author ID (must belong to the same tenant) |

**Example:**

```bash
curl -X PUT https://mosaic-api-1453299254.us-east1.run.app/v1/authors/SOURCE_AUTHOR_ID/reassign \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>" \
  -H "Content-Type: application/json" \
  -d '{"target_author_id": "TARGET_AUTHOR_ID"}'
```

**Response:** `200` with `{ "reassigned_count": number, "site_ids": string[], "source_author_id": string, "target_author_id": string }`

#### DELETE /v1/authors/:id

Deletes an author only when they have **no linked articles**. Returns `409` if any article still references the author.

**Conflict response (`409`):**

```json
{
  "error": "author_has_articles",
  "message": "Cannot delete author while articles are still linked. Reassign them with PUT /v1/authors/:id/reassign before deleting.",
  "article_count": 3,
  "site_ids": ["site-id-1", "site-id-2"]
}
```

**Example:**

```bash
curl -X DELETE https://mosaic-api-1453299254.us-east1.run.app/v1/authors/AUTHOR_ID \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>"
```

**Response:** `204` with empty body

### Categories

- [POST /v1/categories](https://mosaic-api-1453299254.us-east1.run.app/v1/categories): Create a category with an initial locale translation. Requires `write:categories`.
- [PUT /v1/categories/:id](https://mosaic-api-1453299254.us-east1.run.app/v1/categories/:id): Update category metadata (visibility, header, order, parent). Requires `write:categories`.
- [DELETE /v1/categories/:id](https://mosaic-api-1453299254.us-east1.run.app/v1/categories/:id): Delete a category and move its articles to Uncategorized. Requires `write:categories`.

#### POST /v1/categories

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| site_id | string | yes | Target site (must belong to your tenant) |
| slug | string | yes | URL slug for the initial locale translation |
| name | string | yes | Display name for the initial locale translation |
| locale | string | no | Locale code (defaults to site default locale) |
| parent_id | string | no | Parent category ID (must belong to the same site) |
| hidden | boolean | no | Hide from navigation (default false) |
| show_in_header | boolean | no | Show in site header (default false) |
| display_order | number | no | Sort order among siblings (default 0) |
| icon_key | string | no | Optional icon key |

**Example:**

```bash
curl -X POST https://mosaic-api-1453299254.us-east1.run.app/v1/categories \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>" \
  -H "Content-Type: application/json" \
  -d '{"site_id": "SITE_ID", "slug": "tech", "name": "Technology"}'
```

**Response:** `201` with `{ "category": { ... } }`

#### PUT /v1/categories/:id

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| parent_id | string \| null | no | New parent category |
| hidden | boolean | no | Hide from navigation |
| show_in_header | boolean | no | Show in site header |
| display_order | number | no | Sort order among siblings |
| icon_key | string \| null | no | Icon key |

**Response:** `200` with `{ "category": { ... } }`

#### DELETE /v1/categories/:id

Deletes a non-system category. Linked articles are reassigned to the site's Uncategorized category. System categories cannot be deleted.

**Response:** `204` with empty body

### Assets

Tenant media library — images, logos, and favicons. Upload uses `multipart/form-data`.

- [GET /v1/assets](https://mosaic-api-1453299254.us-east1.run.app/v1/assets): List assets for your tenant. Requires `read:assets`.
- [POST /v1/assets](https://mosaic-api-1453299254.us-east1.run.app/v1/assets): Upload an image. Requires `write:assets`.
- [DELETE /v1/assets/:id](https://mosaic-api-1453299254.us-east1.run.app/v1/assets/:id): Delete an asset and its stored variants. Requires `write:assets`.

#### GET /v1/assets

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | no | Filter by `image`, `logo`, or `favicon` |

**Response:** `200` with `{ "assets": [...] }`

#### POST /v1/assets

Multipart fields (plus a `file` part):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | yes | Image file (PNG, JPEG, WebP, SVG) |
| alt_text | string | yes | Accessibility / SEO alt text |
| type | string | no | `image` (default), `logo`, or `favicon` |
| tags | string | no | Comma-separated tags |

**Response:** `201` with `{ "asset": { ... } }`

#### DELETE /v1/assets/:id

**Response:** `200` with `{ "deleted": true, "variants_deleted": number }`

### Articles

Articles are managed in two steps: create the article shell (`POST /v1/articles`), then upsert locale content (`PUT /v1/articles/:id/translations/:locale`).

Call [GET /v1/blocks/catalog](https://mosaic-api-1453299254.us-east1.run.app/v1/blocks/catalog) first to discover available block `type` keys, JSON Schemas, and `default_data` before building `blocks_json`.

- [GET /v1/blocks/catalog](https://mosaic-api-1453299254.us-east1.run.app/v1/blocks/catalog): List available block types with JSON Schema and default data for `blocks_json`. Requires `read:blocks`.
- [GET /v1/articles](https://mosaic-api-1453299254.us-east1.run.app/v1/articles): List articles for a site. Requires `read:articles`.
- [GET /v1/articles/:id](https://mosaic-api-1453299254.us-east1.run.app/v1/articles/:id): Get article + translation. Requires `read:articles`.
- [POST /v1/articles](https://mosaic-api-1453299254.us-east1.run.app/v1/articles): Create article shell. Requires `write:articles`.
- [PUT /v1/articles/:id](https://mosaic-api-1453299254.us-east1.run.app/v1/articles/:id): Update article metadata. Requires `write:articles`.
- [PUT /v1/articles/:id/translations/:locale](https://mosaic-api-1453299254.us-east1.run.app/v1/articles/:id/translations/:locale): Upsert translation (title, blocks, SEO). Requires `write:articles`.
- [DELETE /v1/articles/:id](https://mosaic-api-1453299254.us-east1.run.app/v1/articles/:id): Delete article. Requires `write:articles`.
- [DELETE /v1/articles/:id/translations/:locale](https://mosaic-api-1453299254.us-east1.run.app/v1/articles/:id/translations/:locale): Delete one locale. Requires `write:articles`.

#### GET /v1/blocks/catalog

**Example:**

```bash
curl "https://mosaic-api-1453299254.us-east1.run.app/v1/blocks/catalog" \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>"
```

**Response:** `200` with `{ "blocks": [{ "key", "default_data", "schema" }, ...] }`

Use each item's `key` as the `type` field in `blocks_json`, shape `data` to match `schema`, and start from `default_data` when helpful.

#### POST /v1/articles

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| site_id | string | yes | Target site (must belong to your tenant) |
| author_id | string | yes | Author ID |
| category_id | string | no | Category ID (must belong to the site) |
| status | string | no | `draft` (default), `review`, or `published` |

#### PUT /v1/articles/:id/translations/:locale

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| slug | string | yes | URL slug |
| path | string | yes | URL path (without leading slash) |
| title | string | yes | Article title |
| blocks_json | array | yes | Content blocks — use `GET /v1/blocks/catalog` for types + schemas |
| version | string | yes | Content version id |
| status | string | no | `draft` (default) or `published` |
| excerpt | string | no | Short excerpt (max 300 chars) |

**Example — create + publish:**

```bash
# 1. Create shell
curl -X POST https://mosaic-api-1453299254.us-east1.run.app/v1/articles \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>" \
  -H "Content-Type: application/json" \
  -d '{"site_id":"SITE_ID","author_id":"AUTHOR_ID"}'

# 2. Add content
curl -X PUT https://mosaic-api-1453299254.us-east1.run.app/v1/articles/ARTICLE_ID/translations/pt-BR \
  -H "Authorization: Bearer <API_KEY_PLACEHOLDER>" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "my-article",
    "path": "blog/my-article",
    "title": "My Article",
    "version": "v1",
    "status": "published",
    "blocks_json": [
      {"id":"b1","type":"title-anchor","data":{}},
      {"id":"b2","type":"paragraph","data":{"content":"Hello world","align":"left"}}
    ]
  }'
```

## Scopes

| Scope | Description |
|-------|-------------|
| read:sites | List sites in your tenant |
| read:authors | List authors |
| write:authors | Create, update, reassign, and delete authors |
| read:categories | Read category metadata (via article payloads) |
| write:categories | Create, update, and delete categories |
| read:assets | List tenant media assets |
| write:assets | Upload and delete assets |
| read:articles | List and read articles |
| write:articles | Create, update, and delete articles |
| read:blocks | List block types and schemas for article content |
| read:llm | Access machine-readable documentation |

## Errors

| Status | Meaning |
|--------|---------|
| 401 | Missing, invalid, revoked, or expired API key |
| 403 | Valid key but missing required scope |
| 400 | Validation error |
| 404 | Referenced resource not found |
| 409 | Conflict — e.g. deleting an author linked to articles |