# UPLOAD_CANVAS video classification at scale

Use this reference when scaling creative naming from a pilot sample to the full `UPLOAD_CANVAS` video backlog.

## Trigger

Rodolfo approves the multi-frame method and asks to proceed with the full video backlog.

## Durable lessons from the pilot

- Do **not** classify videos from the first Drive thumbnail or first frame only. Canva videos can show the real content, CTA, amount/limit, or product text only after a few seconds.
- Call the visual artifact `timeline de frames` or `imagem de revisão`; avoid saying only `sheet`, because Rodolfo may interpret it as Google Sheet/planilha.
- Do not create Google Sheets/planilhas unless Rodolfo explicitly asks. Use local CSV/JSON manifests for audit and attach only when useful.
- Once the method is validated, do not keep doing arbitrary micro-samples like another 24 before scaling. Run the full backlog, using technical batches only for stability/resume/audit.

## Safe full-video sequence

1. Run a fresh read-only Drive inventory after any rename/move.
2. Generate multi-frame timelines for all videos with:
   ```bash
   /root/mgs-agent/scripts/ares-drive-video-frame-sampler.py \
     /path/to/upload-canvas-inventory.csv \
     --seconds 0.5,2.0,3.2,4.5,6.0 \
     --out-dir /root/mgs-agent/data/ares/creative-inventory/video-frame-samples-full \
     --discard-videos
   ```
3. Verify completion objectively:
   - selected_count equals video inventory count;
   - sheets count equals video count;
   - frames count equals `video_count * 5`;
   - `videos_remaining=0` when using `--discard-videos`;
   - disk usage is acceptable.
4. Build overview pages and an index CSV for human audit, but treat these as local review images/CSVs, not Google Sheets.
5. Run OCR-assisted naming proposal:
   ```bash
   /root/mgs-agent/scripts/ares-classify-video-timelines-ocr.py \
     /path/to/video-frame-sample-manifest.json \
     --out-dir /root/mgs-agent/data/ares/creative-inventory/video-classification-full
   ```
6. Produce CSV fields at minimum:
   ```text
   current_filename, relative_path, visible_lang_ocr, language_guess,
   country_proposed, angle_proposed, person, orientation_mgs, p_orient,
   proposed_filename, confidence, needs_visual_audit, notes, sheet
   ```
7. Never rename the full Drive backlog directly from OCR alone. First present counts by confidence, language, angle and review bucket.

## Classification guardrails

- OCR can identify language/angle from visible text, but it is weak for detecting `PERSON` vs `NO_PERSON`. Mark visual audit when person presence is not proven.
- Use only `PV`, `PH`, `NV`, `NH` for final `P_ORIENT`.
- For `UNKNOWN` placement/orientation, do not force a final filename; route to review.
- If OCR corrects the filename/folder language guess, note that explicitly in `notes`.
- If multiple videos map to the same proposed name, assign deterministic variants (`001`, `002`, ...), keep the original path and timeline reference for audit, and never emit 2-digit variants in final filenames.

## Reporting

Creating scripts or durable outputs under `/root/mgs-agent/scripts/` or `/root/mgs-agent/data/ares/creative-inventory/` requires `[REPORT-INFRA]` with sanitized evidence: row counts, output paths, hashes, commit if any. Never include Drive tokens, OAuth secrets, or raw credentials.
