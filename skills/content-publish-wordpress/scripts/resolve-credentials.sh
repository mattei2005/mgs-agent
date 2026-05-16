#!/bin/bash
set -euo pipefail

# Load env vars (for systemd/cron use)
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SITE_KEY="${1:?usage: resolve-credentials.sh <site_key>}"
SITES_JSON="/root/mgs-agent/data/sites.json"

site=$(jq -e ".\"$SITE_KEY\"" "$SITES_JSON") || {
  echo "ERROR: site_key '$SITE_KEY' not found in $SITES_JSON" >&2
  exit 1
}

wp_url=$(jq -r '.wp_url' <<<"$site")
username=$(jq -r '.publishing_user.username' <<<"$site")
author_id=$(jq -r '.publishing_user.id' <<<"$site")
vault=$(jq -r '.credentials_ref.vault' <<<"$site")
item=$(jq -r '.credentials_ref.item' <<<"$site")
field=$(jq -r '.credentials_ref.field' <<<"$site")

password=$(op item get "$item" --vault "$vault" --fields "$field" --reveal 2>/dev/null) || {
  echo "ERROR: could not read '$field' from 1Password item '$item' in vault '$vault'" >&2
  exit 1
}

jq -n \
  --arg wp "$wp_url" \
  --arg u "$username" \
  --arg p "$password" \
  --argjson a "$author_id" \
  '{wp_url:$wp, username:$u, password:$p, author_id:$a}'
