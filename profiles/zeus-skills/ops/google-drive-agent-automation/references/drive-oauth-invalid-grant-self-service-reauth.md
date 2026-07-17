# Retired personal Google reauthorization procedure

This reference is intentionally non-operational. MGS permanently removed personal Google credential recovery during the `mgs-core-prod` cutover on 2026-07-17.

Do not recreate former watchdogs, authorization URLs, local token files or retired 1Password items. Diagnose the canonical Service Account instead:

```bash
python3 /root/mgs-agent/scripts/monitor-drive-auth-unified.py --dry-run --force-sa
```

Then validate the exact Drive file or Sheet through `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`. Missing file access is corrected by sharing the existing file with `mgsagent@mgs-core-prod.iam.gserviceaccount.com`; new uploads use `MGS-AGENTS`.
