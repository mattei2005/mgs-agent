#!/bin/bash
set -euo pipefail
cat >&2 <<'MSG'
ERROR: generate-card-only-image.sh is deprecated for REC LazyBlock card images.

Reason: the MBNA manual-image incident showed that AI-generated/enhanced
card-only assets can change text, edges, shadows, colours, or brand design.
LazyBlock card images must preserve the real supplied/selected card artwork.

Approved paths:
- If the user supplies a card image: crop/remove external canvas while preserving
  the original RGB card design; reject damaged/low-quality crops instead of
  inventing a new card.
- If no card image is supplied: use automatic card-image search/ranking and
  validate the selected real card artwork.
- Use Gemini/featured generation only for contextual/lifestyle featured images,
  not to recreate isolated card assets for LazyBlock.
MSG
exit 2
