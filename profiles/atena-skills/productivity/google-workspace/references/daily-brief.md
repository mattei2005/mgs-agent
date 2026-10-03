# MGS Google scope

Gmail, Calendar, Contacts and user-scoped daily briefs are blocked pending a separately approved corporate architecture. Drive and Sheets use only `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`, project `mgs-core-prod`, Service Account `mgsagent@mgs-core-prod.iam.gserviceaccount.com`. No personal token, client secret, browser consent or alternate-identity fallback is permitted.
