#!/bin/bash
set -euo pipefail
# Validate all caller-controlled identifiers before env or vault access.
[[ "${1:-}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { printf "invalid site key\n" >&2; exit 2; }


# Load env vars (for systemd/cron use)
# shellcheck source=/dev/null
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SITE_KEY="${1:?usage: resolve-credentials.sh <site_key>}"
SITES_JSON="/root/mgs-agent/data/sites.json"

site=$(jq -e --arg key "$SITE_KEY" '.[$key]' "$SITES_JSON") || {
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

printf '%s' "$password" | jq -Rs \
  --arg wp "$wp_url" \
  --arg u "$username" \
  --argjson a "$author_id" \
  '{wp_url:$wp, username:$u, password:., author_id:$a}'
