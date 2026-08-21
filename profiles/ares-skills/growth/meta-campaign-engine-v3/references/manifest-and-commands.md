# Manifest and commands

## Manifest modes

```text
pure_clone         source campaign copied deeply; no replacement ads
clone_prestaged    campaign/adset shell + exactly 3 ready replacement media assets
```

Every campaign requires:

```text
idempotency_key
app_key
account_id
mode
source_campaign_id
name
start_time with timezone
status PAUSED or future ACTIVE
```

`clone_prestaged` also requires `source_adset_id`, exactly three ads, and for each media: asset ID, checksum, vertical video ID, square video ID and `ready=true`.

Payloads containing `standard_enhancements` or external `https://fb.com/messenger_doc/` are rejected before transport.

## Commands

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py validate --manifest <path>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py plan --manifest <path>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py media-summary
```

Register media only after real Meta readback. Manual registration is for importing already-confirmed IDs; the v3 pre-stage uploader is separately gated by `media_upload_enabled=true` and `--confirm-upload`:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py media-register \
  --account-id <id> --asset-id <id> --checksum <sha256> \
  --vertical-video-id <id> --square-video-id <id> --ready --confirm-readback

python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py prestage-upload \
  --account-id <id> --page-id <id> --asset-id <id> --checksum <sha256> \
  --vertical-file <file> --square-file <file> --confirm-upload
```

The v3 pre-stage uploader is active but still requires `--confirm-upload`, Page `ADVERTISE`, exact checksum and both Meta videos reaching ready before registry commit. Manual registration requires `--confirm-readback`.

Build CPV manifests only when every campaign has three ready media records and the source creative templates are current. `--campaign-numbers` accepts 1–100 values; the planner chunks them into bundles of two automatically:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py build-cpv \
  --assets-json <six-assets.json> \
  --templates-json /root/mgs-agent/data/ares/meta-ads/engine-v3/templates/cpv-c08-source-templates.json \
  --campaign-numbers 14,15 --operational-date YYYY-MM-DD \
  --request-id <unique-id> --status ACTIVE --output <manifest.json>
```

Use `--status PAUSED` only for an explicitly requested technical canary; normal production uses `ACTIVE` with the future `start_time` sealed in the manifest.

The builder emits `prevalidated=false`. Promote only through the deterministic prevalidator, which rechecks the media registry and seals a tamper-evident content digest:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py prevalidate \
  --manifest <draft.json> --registry <media-registry.json> --output <sealed.json>
```

Any post-prevalidation change invalidates execute. Source, templates, media, budget, UTMs, names and future start must be final before sealing.

## Execute gate

Real execute requires all four:

```text
manifest.prevalidated = true
config.enabled = true
config.write_enabled = true
--confirm-execute
```

The installed v3 config is disabled. `--offline-fake` is test-only and never contacts Meta.
