# Hera/Ares Creative Taxonomy Sync — 2026-06-07

## Trigger

Use when Rodolfo asks whether Hera files/SOUL/skills should be updated based on prior Ares discussions about creative taxonomy, Google Drive organization, Canva downloads, or handoff of creative assets into campaign operations.

## Durable lesson

Ares may help define creative taxonomy because it is the downstream campaign consumer, but Hera is the operational owner of creative assets. Once Rodolfo approves a taxonomy or Drive structure in an Ares thread, Hera must be synchronized before real creative ingestion begins.

Do not let Hera keep a generic naming/Drive proposal when Ares already has an approved operation-specific standard.

## Current CC_US_ES decisions captured from Ares thread `1508906079642456084`

```text
Operation pilot              CC_US_ES
Drive root                   MGS-CRIATIVOS
Raw Canva upload area         MGS-CRIATIVOS > UPLOAD CANVAS
Primary organized structure   MGS-CRIATIVOS/CC_US_ES/IMG and /VID
Lifecycle folders             01_READY, 02_TESTING, 03_TESTED,
                              04_WINNERS, 05_REJECTED, 99_LEGACY
Official naming               CC_US_ES_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
FORMAT                        IMG or VID
ANGLE                         Controlled dictionary per operation; UNKNOWN allowed
P_ORIENT                      PV, NV, PS, NS only for CC_US_ES
Official sizes                FEED 1080x1080; STORY 1080x1920
Dimension in filename         No; keep width/height/aspect_ratio in inventory
Mass rename/move              Only after inventory + rename plan + Rodolfo approval
```

## P_ORIENT final for CC_US_ES

```text
Code | Meaning
-----|--------------------------------
PV   | pessoa vertical / stories
NV   | sem pessoa vertical / stories
PS   | pessoa square / feed
NS   | sem pessoa square / feed
```

Removed/not used for this operation: `PH`, `NH`, `PU`, `NU`, `UU`.

If person/orientation is uncertain, the asset goes to review before final renaming. `UNKNOWN` remains valid for `ANGLE`, not for `P_ORIENT`.

## Files that should be synchronized before Hera processes uploaded creatives

```text
/root/mgs-agent/context/hera-creative-agent.md
/root/mgs-agent/profiles/hera-soul.md
/root/mgs-agent/profiles/hera-skills/creative/creative-brief-handoff/SKILL.md
```

Update targets:

```text
Topic                       Required alignment
--------------------------- ------------------------------------------------
Naming                      Replace generic [site]_[vertical]... proposal with
                            MGS operation-specific taxonomy, at least for CC_US_ES.
Drive/Canva                 Add MGS-CRIATIVOS, UPLOAD CANVAS as raw/original,
                            and CC_US_ES/IMG|VID/01_READY as initial organized destinations.
P_ORIENT                    Encode PV/NV/PS/NS only for CC_US_ES.
Sizes                       Encode FEED 1080x1080 and STORY 1080x1920.
Inventory                   Include origin manager/folder, Canva/design ID if present,
                            original filename, format, dimensions, aspect ratio,
                            language/operation guess, angle, p_orient, status,
                            destination path, and review notes.
Safety                      Hera reads/classifies first, generates plan second,
                            and only renames/moves/copies after explicit approval.
Hera/Ares boundary          Hera prepares organized, approved, traceable creative
                            assets; Ares consumes them for campaign work.
```

## Recommended sequence

1. Import/read the relevant Ares thread in read-only mode if not already available.
2. Extract the finalized taxonomy/Drive decisions, distinguishing stable decisions from exploratory discussion.
3. Patch Hera architecture/context first (`context/hera-creative-agent.md`).
4. Patch Hera SOUL to point at the same operational standard without turning SOUL into a long implementation manual.
5. Patch Hera creative skill with the procedural details for classification, inventory, rename-plan, and approval gate.
6. Run a cross-file consistency audit: Ares = campaign execution; Hera = creative assets/Drive/Canva; Zeus = governance.
7. Only after Hera is aligned should Rodolfo upload the downloaded Canva creatives and ask Hera to start reading/restructuring.

## Pitfall

Do not answer “the three files are Hera files” and stop. The operational issue is synchronization: if Ares has already defined folders/naming/taxonomy, Hera must carry those same rules before ingestion, or the agents will diverge and invent conflicting standards.