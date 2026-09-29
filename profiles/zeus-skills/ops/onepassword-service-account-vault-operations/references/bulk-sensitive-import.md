# Bulk Sensitive Import Through a 1Password Service Account

## Master Document workflow

Use a master Document when the source is a bounded credential-bearing inventory and item-per-record writes may exceed the current write budget.

1. Build a structured object in memory. Include a schema version, source label, generated timestamp, expected record count, immutable record IDs, safe grouping metadata, and the exact sensitive source field.
2. Serialize in memory and stream it through stdin:

```bash
op document create - \
  --vault '<vault-id>' \
  --title '<clear inventory title>' \
  --file-name '<machine-readable-name>.json' \
  --tags '<comma-separated tags>' \
  --format json
```

3. Capture stdout privately. Document creation may return the identifier as `uuid` rather than `id`; accept only a nonblank identifier whose returned vault identifier matches the target.
4. Download through stdout without writing a file:

```bash
op document get '<document-uuid>' --vault '<vault-id>'
```

5. Parse and require exact object equality, expected record count, unique immutable IDs, and the expected nonempty-sensitive-field count.
6. List the vault and require the Document ID to be present before reporting completion.

Never use a temporary JSON/CSV file as an intermediate. If an external application truly requires a file, create it only under an explicitly approved secure export workflow with its own retention and deletion gate.

## Optional Secure Note per record

Use a deterministic unique title such as:

```text
{profile_no} — {profile_name}
```

Recommended item shape:

```json
{
  "title": "...",
  "category": "SECURE_NOTE",
  "vault": {"id": "<vault-id>"},
  "tags": ["source-system", "source-system/record"],
  "sections": [{"id": "source", "label": "Source system"}],
  "fields": [
    {"id": "notesPlain", "type": "STRING", "purpose": "NOTES", "label": "notesPlain", "value": "<raw sensitive text>"},
    {"id": "record_id", "section": {"id": "source"}, "type": "STRING", "label": "Record ID", "value": "..."},
    {"id": "record_no", "section": {"id": "source"}, "type": "STRING", "label": "Record number", "value": "..."},
    {"id": "group_id", "section": {"id": "source"}, "type": "STRING", "label": "Group ID", "value": "..."},
    {"id": "group_name", "section": {"id": "source"}, "type": "STRING", "label": "Group name", "value": "..."}
  ]
}
```

Pipe the JSON to `op item create --vault <vault-id> --format json -`; capture stdout and stderr privately. Read the item back by returned ID and compare title, vault ID, and every field by field ID.

## Rate-limit discipline

Run:

```bash
op service-account ratelimit --format json
```

Read separate token write, token read, and account counters. Do not assume one item equals one write unit. Start with one create/readback canary, re-read counters, and estimate the actual per-record budget before launching the batch.

Use low bounded concurrency. If a concurrent batch has failures:

1. `op item list --vault <vault-id> --format json` once.
2. Match the failed record's deterministic title.
3. Read back existing matches.
4. Retry only titles proven absent.
5. Lower concurrency or switch to sequential writes.

Keep a credential-free progress map of source record ID to 1Password item ID. Do not store the raw source field in checkpoints.

## Final report contract

Report only:

```text
vault name
operator access verified yes/no
master Document present yes/no
master record count
individual Secure Note count
remaining individual count, if optional view is incomplete
rate-limit or cleanup blocker
secret output exposed yes/no
```

Do not paste vault item contents, Document excerpts, password prefixes, authenticator material, or error output that may echo input.
