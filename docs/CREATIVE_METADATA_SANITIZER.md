# MGS Creative Metadata Sanitizer

Server-side metadata cleaning gate for MGS creative assets. This is the approved VPS equivalent of ExifCleaner for agent workflows.

## Canonical command

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh <inspect|verify|clean|batch> ...
```

Backends:

- Primary: `exiftool` (`libimage-exiftool-perl`)
- Secondary: `mat2` when supported by the file type

Audit log:

```text
/root/mgs-agent/logs/creative-metadata-sanitizer.jsonl
```

## Creative Operations rule

Before Ares hands off, saves, or uploads a creative asset to the approved Drive/folder flow, Ares must run the sanitizer and use the cleaned file as the deliverable.

Recommended single-file flow:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.metadata-clean.png
```

## Ares rule

Before Ares uses a creative in a campaign/test, Ares must verify the file. If the file is not clean, Ares must clean it before use or escalate if the campaign asset cannot be safely cleaned.

Recommended gate:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.png \
  || /root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
```

## Batch flow

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh batch /path/to/source-dir --out-dir /path/to/clean-dir --agent ares
```

## Output and privacy discipline

- Do not print full metadata dumps into Discord unless Rodolfo asks and the output has been reviewed.
- Never expose credentials or tokens; this tool does not need any.
- Prefer reporting counts/status: `harmful_tags_before`, `harmful_tags_after`, `clean`, output path, audit log path.
- For untrusted files, keep them in a temp/work directory and upload only the cleaned output.

## Validation baseline

The implementation was validated with a PNG containing a malicious `Comment` payload similar to the ExifCleaner XSS PoC. Before cleaning, `PNG:Comment` was detected. After cleaning, verification returned `clean: true` and ExifTool no longer showed the comment.
