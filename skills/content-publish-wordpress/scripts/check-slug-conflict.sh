#!/bin/bash
set -euo pipefail

# Load env vars (OP_DEFAULT_VAULT, etc.) — runs under systemd/cron too
# shellcheck source=/dev/null
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

# Helper para curl autenticado seguro (não expõe senha em ps aux)
# shellcheck source=/dev/null
source "$(dirname "$0")/wp-curl-auth.sh"

SITE_KEY="${1:?usage: check-slug-conflict.sh <site_key> <slug> [post_types_csv]}"
SLUG="${2:?missing slug}"
POST_TYPES="${3:-posts,media}"
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="/root/mgs-agent/logs/publish-wordpress.log"

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

slug_enc=$(jq -nr --arg s "$SLUG" '$s | @uri')

conflicting="[]"
IFS=',' read -ra TYPES <<<"$POST_TYPES"
for pt in "${TYPES[@]}"; do
  # Attempt 1: with status=any,trash,auto-draft
  tmp=$(mktemp)
  http=$(wp_curl_auth_http "$tmp" "$user" "$pass" \
    "$wp/wp-json/wp/v2/$pt?slug=$slug_enc&status=any,trash,auto-draft&per_page=20" 2>/dev/null)
  body=$(cat "$tmp")
  rm -f "$tmp"

  # Retry without status filter if the first call rejected it (e.g. media doesn't accept auto-draft)
  if [ "${http:0:1}" != "2" ]; then
    tmp=$(mktemp)
    http=$(wp_curl_auth_http "$tmp" "$user" "$pass" \
      "$wp/wp-json/wp/v2/$pt?slug=$slug_enc&per_page=20" 2>/dev/null)
    body=$(cat "$tmp")
    rm -f "$tmp"
  fi

  # Fail-closed: any remaining non-2xx is a hard error
  if [ "${http:0:1}" != "2" ]; then
    echo "ERROR: check-slug-conflict '$pt' endpoint returned HTTP $http on $wp/wp-json/wp/v2/$pt?slug=$slug_enc" >&2
    echo "Response head: $(echo "$body" | head -c 400)" >&2
    exit 1
  fi

  # Response shape must be an array
  if [ "$(jq -r 'type' <<<"$body" 2>/dev/null)" != "array" ]; then
    echo "ERROR: check-slug-conflict '$pt' response is not an array — malformed API response" >&2
    echo "Response head: $(echo "$body" | head -c 400)" >&2
    exit 1
  fi

  hits=$(jq --arg pt "$pt" '[.[] | {id, post_type:$pt, status, slug}]' <<<"$body")
  conflicting=$(jq -s '.[0] + .[1]' <(echo "$conflicting") <(echo "$hits"))
  if [ "$pt" = "posts" ]; then
    posts_hits=$(jq 'length' <<<"$hits")
  fi
done

# WARN if /posts query returned 0 results — possible plugin interference in
# rest_post_query filter. See CLAUDE.md "Known Issue: WP REST /posts?slug=".
if [[ ",$POST_TYPES," == *,posts,* ]] && [ "${posts_hits:-0}" -eq 0 ]; then
  echo "[$(date -Iseconds)] check-slug-conflict WARN posts_query_zero_results slug=$SLUG site=$SITE_KEY (possible plugin interference in rest_post_query — see CLAUDE.md known issue)" >>"$LOG"
fi

available=$(jq 'length == 0' <<<"$conflicting")
jq -n --argjson a "$available" --argjson c "$conflicting" --arg s "$SLUG" \
  '{slug:$s, available:$a, conflicting:$c}'
