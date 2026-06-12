# UPLOAD_CANVAS classification continuation after duplicate cleanup

Use this reference when Rodolfo asks to continue classifying `MGS-CRIATIVOS/UPLOAD_CANVAS` after a focused duplicate cleanup in a subfolder such as `cartao de credito/videos`.

## Sequence that worked

1. Reload the main `paid-acquisition-operations` skill and the relevant UPLOAD_CANVAS reference.
2. Re-run the full read-only Drive inventory after any folder move, because counts and duplicate status changed.
3. Generate the organization proposal from the fresh inventory, not from an old CSV.
4. Summarize by folder, format, vertical, language, placement, MD5 duplicates, and anomalous rows.
5. Build a visual/anomaly contact sheet for rows that could change the organization decision:
   - vertical guess does not match the parent folder, e.g. `JOBS` files under `cartao de credito`;
   - `language_guess=UNKNOWN`;
   - `placement_fit=UNKNOWN`;
   - MD5 duplicate groups;
   - files missing width/height in Drive metadata.
6. Use visual confirmation before proposing moves/copies for mixed-folder rows.
7. Keep UPLOAD_CANVAS as RAW unless Rodolfo explicitly requests a move within RAW. Final campaign-ready copies still require cleaned-copy flow and metadata sanitizer gate.

## Duplicate cleanup nuance

If Rodolfo explicitly asks to move visual duplicates to a holding folder such as `videos2` or `imagens2`, the operation is allowed after validation because the user requested that exact Drive state change. Still do:

```text
Step                         | Requirement
-----------------------------|---------------------------------------------
Preflight                    | Count source/destination before move
Duplicate candidate signal   | Same Canva design ID or same MD5 where available
Visual validation            | Contact sheet or direct thumbnails reviewed
Canonical choice             | Prefer clean name without parentheses/copy markers
Move action                  | Drive parents PATCH add destination/remove source
Post-check                   | Count source/destination and duplicate groups after
Report                       | Before/after counts, moved count, errors, auth mode
```

For videos exported from Canva, MD5 may differ even when the video is visually identical. Same design ID in the suffix plus matching duration/dimensions and visual thumbnails is a stronger signal than filename alone.

## Classification pitfalls observed

- A folder named `cartao de credito` can contain real job creatives; do not force them into CC just because of the parent folder.
- A folder named `emprego` can contain files with language unknown from metadata/name; visually confirm before final language routing.
- Drive may lack width/height for some MP4s even when the file is valid; mark as technical review rather than inventing placement.
- After moving video duplicates to `videos2`, include `videos2` in the next inventory so the RAW audit remains complete.

## Reporting infra

Creating durable outputs under `/root/mgs-agent/data/ares/creative-inventory/` still requires `[REPORT-INFRA]`. If direct Discord send lacks channel access, use the configured Alerts Infra webhook from 1Password and report only sanitized evidence: path, counts, exit status, and item name/URL length if needed — never the webhook URL.
