# REPORT-INFRA — preserving manual inventory sections

Use when processing a REPORT-INFRA that updates `/root/mgs-agent/data/infra-inventory.json` with durable runtime state that is not fully discovered automatically.

## Pattern observed

Two REPORT-INFRA classes required manual inventory sections:
- `system_packages[]` for durable apt/runtime dependencies installed by another agent.
- `profile_skill_references[]` for profile skill/reference sync state, runtime/versioned SHA match, and validation summaries.

During processing, `infra-discovery.sh` initially preserved only some manual sections. If a manual section is present in `infra-inventory.json` but not carried through discovery, a later regeneration can silently erase it. This happened with `runtime_artifacts[]` risk during system-package registration and was corrected by adding preservation logic.

## Required workflow

1. Before editing inventory, inspect whether the target section is auto-discovered or manual-preserved by `/root/mgs-agent/scripts/infra-discovery.sh`.
2. If adding or relying on any manual section, patch `infra-discovery.sh` in the same REPORT-INFRA processing turn to:
   - initialize `<SECTION>_JSON='[]'`;
   - load it from existing inventory with `jq -c '.section // []' "$OUT"`;
   - pass it into `jq -n` via `--argjson`;
   - emit it in the final JSON object.
3. Validate `bash -n scripts/infra-discovery.sh` and `python3 -m json.tool data/infra-inventory.json` before commit.
4. Verify the preservation explicitly with a compact check, e.g. section length/IDs, not a full JSON dump.
5. Commit the inventory plus `infra-discovery.sh` together when discovery was patched.
6. Stage surgically. Leave unrelated sync-souls, Ares/agente legado artifacts, state files, and generated media unstaged.

## Minimal preservation patch shape

```bash
MANUAL_SECTION_JSON='[]'
if [ -f "$OUT" ]; then
    MANUAL_SECTION_JSON=$(jq -c '.manual_section // []' "$OUT")
fi

jq -n \
  --argjson manual_section "$MANUAL_SECTION_JSON" \
  '{"manual_section": $manual_section, ...}'
```

## Pitfall

Do not treat `infra-inventory.json` as purely generated if it contains manual governance sections. Generated/runtime discovery and manually curated state coexist; the script must preserve manual sections or the inventory will drift backward on the next cron regeneration.
