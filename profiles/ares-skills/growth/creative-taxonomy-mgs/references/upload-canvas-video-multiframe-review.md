# UPLOAD_CANVAS video multi-frame review

Use this reference when classifying or renaming Canva/Drive videos in `MGS-AGENTS/CRIATIVOS/UPLOAD_CANVAS`.

## Durable lesson

Do not classify a video from the Drive thumbnail or first frame only. Some Canva exports show little/no useful content initially and reveal the actual text, CTA, credit limit, card visual, or approval claim after a delay.

Observed example:

```text
Old mistaken name     | CC_DE_DE_VID_UNKNOWN_NV_001.mp4
Reason for mistake    | initial thumbnail/frame looked weak/unclear
Multi-frame finding   | text appeared later: Credit Card / APPROVED FOR YOU / LIMIT FROM $6,550.00
Corrected name        | CC_US_EN_VID_APROBACION_NV_001.mp4
Correct angle         | APROBACION
Correct P_ORIENT      | NV
```

## Standard sampling

For video classification, generate a timeline de frames / imagem de revisão with at least:

```text
0.5s, 2.0s, 3.2s, 4.5s, 6.0s
```

Use the canonical script:

```bash
/root/mgs-agent/scripts/ares-drive-video-frame-sampler.py <inventory.csv> --seconds 0.5,2.0,3.2,4.5,6.0 --discard-videos
```

`--discard-videos` should be used for large batches so downloaded MP4s are deleted after frame extraction; keep the frames/timelines and manifest only.

## Communication preference

With Rodolfo, do **not** call the visual timeline a “sheet” unless clarifying. He interpreted “sheet” as planilha/Google Sheet. Preferred terms:

```text
Preferred term       | Avoid / clarify
---------------------|------------------------------
timeline de frames   | sheet
imagem de revisão    | Google Sheet / planilha
contact visual       | planilha
```

Do not create Google Sheets for this flow unless explicitly requested. CSV/JSON local is acceptable for logs/plans; explain it is not a spreadsheet in Drive.

## Scaling sequence

1. Use a small balanced sample only to validate that the method works.
2. Once validated, scale directly to all remaining videos in technical batches; do not keep proposing more arbitrary small samples.
3. Keep Drive read-only while generating frames and proposed names.
4. Only rename/move after explicit approval.

## Classification notes

- Aggregate text/visual evidence across all sampled frames.
- If later frames reveal a stronger angle than frame 0.5s, use the later-frame evidence.
- Prefer the dominant claim for `ANGLE`; e.g. `APPROVED FOR YOU` usually maps to `APROBACION` even if a credit limit also appears.
- Use only `PV`, `PH`, `NV`, `NH` for `P_ORIENT`.
- If text is still unreadable after multi-frame sampling, keep `UNKNOWN` and mark low confidence/review.
