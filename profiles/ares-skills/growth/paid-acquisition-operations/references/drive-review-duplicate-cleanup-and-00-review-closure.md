# Drive review, duplicate cleanup, and 00_REVIEW closure

Use this reference when Rodolfo asks Ares to review/fix all files in `MGS-AGENTS/CRIATIVOS`, clean duplicates, or close remaining `00_REVIEW` assets.

## Operating principle

If Ares has Drive access, do not answer as if files are unavailable. Act through the Drive inventory/review pipeline. If the user says to fix what needs fixing, perform safe Drive actions already inside scope: scan, classify, rename/move organized copies, remove duplicates after explicit approval, and validate with a fresh scan.

Preserve `UPLOAD_CANVAS` RAW unless the user explicitly asks to alter/delete RAW. Apply final review actions to the cleaned/organized copy, not to the RAW `source_drive_id`.

## Safe sequence

1. Generate a fresh Drive inventory of `MGS-AGENTS/CRIATIVOS`.
2. Audit organized outputs separately from RAW:
   - canonical filename format;
   - 3-digit variant;
   - duplicate filename in same folder;
   - duplicate MD5 among organized outputs;
   - remaining `00_REVIEW` items.
3. Fix canonical-name issues and filename collisions first.
4. For MD5 duplicates, keep one file per group and trash the rest only after Rodolfo approves deletion.
5. If the canonical Service Account can edit but cannot trash/delete:
   - check file capabilities (`canTrash`, `canDelete`, `ownedByMe`);
   - verify Shared Drive membership and `organizer` role;
   - fail closed and escalate the capability mismatch; do not revive personal OAuth as fallback.
6. For `00_REVIEW` closure:
   - download the cleaned review copies or sample their thumbnails/frames;
   - build a visual contact sheet/timeline for review;
   - classify vertical/country/lang/format/angle/P_ORIENT conservatively;
   - promote safe assets to `01_READY_CANDIDATE`; move rejects to `05_REJECTED` rather than leaving them in `00_REVIEW`.
7. Validate with a fresh Drive scan and report objective counts.

## Critical pitfall: RAW source vs cleaned review copy

Backlog reports often have both:

```text
source_drive_id = RAW file under UPLOAD_CANVAS
 dest_drive_id  = cleaned copy uploaded into REVIEW/00_REVIEW or final folder
```

When closing `00_REVIEW`, act on the cleaned `dest_drive_id`, not the RAW `source_drive_id`. If a mistaken move touches RAW, restore it to its original `UPLOAD_CANVAS` parent and apply the decision to the cleaned copy.

## Validation targets

A clean final report should include:

```text
Check                             | Expected
----------------------------------|---------
00_REVIEW remaining               | 0, unless intentionally held
Non-canonical READY filenames     | 0
Variant not 3 digits              | 0
Duplicate names in same folder    | 0
Organized MD5 duplicate groups    | 0 after delete approval
RAW files in UPLOAD_CANVAS        | Preserved unless explicitly deleted
```

## Communication lesson

If Rodolfo challenges “why can’t you review them?”, the correct response is to use the Drive pipeline, not to ask him to resend files. Explain only real permission blockers; otherwise proceed and validate.