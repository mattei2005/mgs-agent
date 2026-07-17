# Retired Google authentication in one-off work scripts

Dated Python utilities in this tree that depended on the removed personal Google credential are preserved for audit but now terminate immediately through `MGS_GOOGLE_AUTH_RETIRED_GUARD`.

To reuse their business logic, rebuild the utility on `/root/mgs-agent/scripts/mgs_google_workspace_auth.py` and validate with the canonical `mgs-core-prod` Service Account. Do not remove the guard or recreate the former credential path.
