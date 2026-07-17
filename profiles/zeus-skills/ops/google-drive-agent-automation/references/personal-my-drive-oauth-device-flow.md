# Retired personal My Drive authentication procedure

MGS no longer supports personal Google credential bootstrap, device flow, desktop consent or local token storage. This reference is a tombstone so historical links fail closed instead of reviving a removed architecture.

Current rules:

- existing operational Sheets may remain in My Drive when shared with `mgsagent@mgs-core-prod.iam.gserviceaccount.com`;
- new automated uploads go to the Shared Drive `MGS-AGENTS`;
- consumers use `/root/mgs-agent/scripts/mgs_google_workspace_auth.py` and accept only `service_account`;
- user-scoped Google services remain blocked until Rodolfo approves a separate corporate architecture.
