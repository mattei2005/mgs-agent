# Hera Creative Ops + Ares Taxonomy Alignment — 2026-06-07

## Trigger

Use when Rodolfo is finalizing Hera or any Creative Ops agent/files after prior Ares discussions about Drive, Canva, taxonomy, or campaign asset handoff.

## Durable lesson

Hera is **Creative Operations**, not an assistant/sub-agent of Ares.

Hera must support two parallel asset flows:

```text
Flow A — Hera-created creative
Request → Hera creates static/video creative → names/organizes → places in vertical folder → Ares or human uses.

Flow B — Human-created creative
Kelly/Geizian/gestor creates asset → uploads to Drive → Hera classifies/names/inventories/organizes → Ares or human uses.
```

Ares is an important consumer of approved creative assets, but not the only consumer. Kelly, Geizian, and gestores may also create and run campaigns manually without Ares. Hera still owns organization, taxonomy, status, and inventory for those assets.

## CC_US_ES taxonomy captured from Ares thread

For the `CC_US_ES` pilot, align Hera docs/SOUL/skills with the Ares-approved taxonomy:

```text
CC_US_ES_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

`P_ORIENT` official values for this operation:

```text
PV = pessoa vertical / stories
NV = sem pessoa vertical / stories
PS = pessoa square / feed
NS = sem pessoa square / feed
```

Do not use `PH`, `NH`, `PU`, `NU`, or `UU` for `CC_US_ES`. If person/orientation is uncertain, put the asset in review before final rename. `UNKNOWN` is acceptable for `ANGLE` only, with a note.

Official dimensions:

```text
Placement  Dimensão   Aspect ratio
FEED       1080x1080  1:1
STORY      1080x1920  9:16
```

Do not put size/dimension in filename; keep width/height/aspect_ratio/placement in the inventory.

## Drive structure

Rodolfo definiu o Shared Drive `MGS-AGENTS/CRIATIVOS` como raiz operacional:

```text
https://drive.google.com/drive/folders/0AEwt4Ye690ocUk9PVA
Workspace admin: support@matteiservicesinc.com
```

Recommended conceptual structure:

```text
MGS-AGENTS/CRIATIVOS/
├── UPLOAD CANVAS              # bruto/original
└── CC_US_ES/
    ├── IMG/
    │   ├── 01_READY
    │   ├── 02_TESTING
    │   ├── 03_TESTED
    │   ├── 04_WINNERS
    │   ├── 05_REJECTED
    │   └── 99_LEGACY
    └── VID/
        ├── 01_READY
        ├── 02_TESTING
        ├── 03_TESTED
        ├── 04_WINNERS
        ├── 05_REJECTED
        └── 99_LEGACY
```

`UPLOAD CANVAS` is raw/original. Hera should not delete, overwrite, move, or rename in bulk without first producing a plan and getting explicit Rodolfo approval.

## Inventory fields required for human + Ares flows

When updating Hera files or skills, include fields that distinguish origin from usage:

```text
original_filename
suggested_filename
source_folder
destination_folder
format
angle
p_orient
variant
width
height
aspect_ratio
placement_fit
language
created_by        # HERA / KELLY / GEIZIAN / GESTOR / UNKNOWN
requested_by
used_by           # ARES / HUMAN / UNKNOWN
campaign_owner    # Ares, Kelly, Geizian, gestor, UNKNOWN
source            # HERA_GENERATED / CANVA / HUMAN_UPLOAD
canva_design_id
asset_drive_id
status
notes
```

## File update pattern

When Rodolfo says to synchronize Hera with an Ares taxonomy/Drive thread, update at least:

```text
/root/mgs-agent/context/hera-creative-agent.md
/root/mgs-agent/profiles/hera-soul.md
/root/.hermes/profiles/hera/SOUL.md
/root/mgs-agent/profiles/hera-skills/creative/creative-brief-handoff/SKILL.md
/root/.hermes/profiles/hera/skills/creative/creative-brief-handoff/SKILL.md
```

If templates exist under the Hera skill, update them too:

```text
templates/creative-brief.md
templates/ares-handoff.md
```

Keep live and versioned Hera files identical. Back up before patching. Validate with `cmp`, `git diff --check`, secret scan on added lines, audit log, auto-push, and `HEAD == origin/main`.

## Communication pattern to Rodolfo

When returning files for review, attach them as native files (`MEDIA:/tmp/...`) and summarize the operational decisions, not only the raw file changes.

Decision framing:

```text
Hera = creates + organizes creative assets.
Ares = optional campaign consumer.
Humans = may create/use assets directly.
Zeus = governance/audit.
```
