#!/bin/bash
set -euo pipefail

cat >&2 <<'MSG'
ERROR: generate-clean-card-image.sh is deprecated for REC LazyBlock card images.

Reason: the MBNA 62092 incident showed that Gemini-generated card-only assets can
look acceptable in featured compositions but fail as isolated LazyBlock card
images due to edge/text/shadow artifacts.

Use the current runner behavior instead:
- normalize user-supplied manual card images with normalize-card-artwork.py;
- if the useful crop is too small/rough, reject it for LazyBlock;
- fall back to automatic card-only image search;
- report manual_source_url and manual_rejected_reason.
MSG
exit 2
