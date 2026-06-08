# Creative metadata sanitizer for Hera/Ares — 2026-06-08

## When this matters

Use this pattern when Rodolfo asks to implement ExifCleaner-like metadata cleaning for creative assets, or when Hera/Ares workflows add a new asset gate before Drive handoff or campaign use.

## Durable pattern

Do **not** deploy the ExifCleaner Electron GUI on the server for agent workflows. Implement the same server-side capability through deterministic CLI tooling:

- Primary backend: `exiftool` (`libimage-exiftool-perl` on Ubuntu/Debian)
- Optional second pass: `mat2`
- Canonical MGS wrapper: `/root/mgs-agent/scripts/clean-creative-metadata.sh`
- Audit log: `/root/mgs-agent/logs/creative-metadata-sanitizer.jsonl`

The wrapper should support at least:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh inspect /path/to/file --json
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/file
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/file --agent hera
/root/mgs-agent/scripts/clean-creative-metadata.sh batch /path/to/src-dir --out-dir /path/to/clean-dir --agent hera
```

## Company OS integration points

Patch both conceptual routing and agent behavior layers:

```text
/root/mgs-agent/context/agent-map.md
/root/mgs-agent/context/routes.md
/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md
/root/.hermes/profiles/hera/SOUL.md
/root/.hermes/profiles/ares/SOUL.md
```

Hera rule: before handoff/upload/Drive delivery, clean creative assets and deliver the cleaned output.

Ares rule: before campaign/test use, verify the creative; if not clean, clean it first or escalate if the file cannot be safely cleaned.

## Validation recipe

Use a deterministic malicious PNG fixture with a `PNG:Comment` payload similar to the ExifCleaner XSS PoC. Validate:

```text
Before clean: harmful tag detected (e.g. PNG:Comment)
After clean: harmful_tags_after = 0
verify: clean: true
exiftool -Comment: empty
Audit: JSONL event appended with hashes/sizes/status
```

Important verification lesson from the session: ExifTool may report structural non-privacy PNG tags after cleaning (e.g. `PNG:BackgroundColor`). The privacy gate should allowlist structural tags and treat comment/author/software/GPS/IPTC/XMP-style tags as harmful. `file` may be unavailable in the Hermes shell environment; fall back to ExifTool MIMEType when needed.

## Operational report pattern

After implementation, report as a concrete validation matrix:

```text
Item                         Estado
---------------------------- ------------------------------------------------
ExifTool                     installed/version
mat2                         installed/version
Script central               /root/mgs-agent/scripts/clean-creative-metadata.sh
Hera                         SOUL/context updated + gateway reloaded if needed
Ares                         SOUL/context updated + gateway reloaded if needed
Validation                   malicious metadata removed; verify clean=true
Audit                        events-audit + sanitizer JSONL written
Git                          clean; HEAD == origin/main
REPORT-INFRA                 sent when persistent scripts/context/agent files changed
```

Use `[REPORT-INFRA]` when the change adds/modifies persistent scripts, docs, context, or agent SOUL/config.
