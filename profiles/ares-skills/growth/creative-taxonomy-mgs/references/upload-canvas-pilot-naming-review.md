# UPLOAD_CANVAS pilot naming review

Use this reference when testing or scaling the MGS creative naming taxonomy on a small sample before touching the full `UPLOAD_CANVAS` backlog.

## Trigger

Rodolfo asks to test the nomenclature on a small sample, e.g. “3 criativos de cada: imagem e vídeo”.

## Validated sequence

1. Run a fresh read-only inventory of `MGS-CRIATIVOS/UPLOAD_CANVAS` after any folder/duplicate cleanup.
2. Select a balanced sample: 3 `IMG` + 3 `VID`, preferably covering distinct visible languages and placements.
3. Generate a contact sheet from Drive thumbnails; do not rely only on filename/folder guesses.
4. Visually classify each item for:
   - visible language;
   - country evidence, if any;
   - vertical;
   - `ANGLE`;
   - `PERSON` / `NO_PERSON`;
   - orientation for `P_ORIENT` using only `VERTICAL` or `HORIZONTAL`.
5. Produce a CSV proposal with current path, proposed filename, confidence and notes.
6. Validate that all proposed `p_orient` values are only `PV`, `PH`, `NV`, `NH`.
7. Ask Rodolfo to approve the logic before generating a full-backlog plan or doing any Drive write.

## Key correction from pilot

Do not trust the automatic language/country guess blindly. Visual evidence can override folder/name metadata.

Example observed in pilot:

```text
Automatic guess | Visual evidence                 | Final proposal
----------------|---------------------------------|----------------
DE              | Spanish text + MXN currency     | CC_MX_ES
```

## P_ORIENT mapping used in pilot

Rodolfo’s current rule is only:

```text
PV | PERSON    | VERTICAL
PH | PERSON    | HORIZONTAL
NV | NO_PERSON | VERTICAL
NH | NO_PERSON | HORIZONTAL
```

For naming purposes:

```text
Placement/dimension | Orientation used for P_ORIENT
--------------------|------------------------------
STORY 1080x1920     | VERTICAL
FEED 1080x1080      | HORIZONTAL
LANDSCAPE/16:9      | HORIZONTAL
UNKNOWN             | REVIEW; do not force final name
```

## CSV fields for pilot proposals

Recommended fields:

```text
pilot_index
current_path
current_filename
format
width
height
visible_lang
country_proposed
vertical
angle_proposed
person
orientation_mgs
p_orient
variant
proposed_filename
confidence
notes
```

## Confidence rules

```text
Confidence | Use when
-----------|------------------------------------------------------------
high       | visual text and classification are clear
medium     | name structure is clear but country/angle partly assumed
low        | text is illegible or angle/country is not reliable
```

If `ANGLE` is not reliable, use `UNKNOWN` and keep low confidence. Do not invent angle to make the taxonomy look complete.

## Reporting

Creating durable pilot outputs under `/root/mgs-agent/data/ares/creative-inventory/` requires `[REPORT-INFRA]` with path, row count, `p_orient` values and checksums. Attach the contact sheet and CSV to Rodolfo’s response when useful.
