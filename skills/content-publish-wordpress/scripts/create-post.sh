#!/bin/bash
set -e

# Helper para curl autenticado seguro (não expõe senha em ps aux)
source "$(dirname "$0")/wp-curl-auth.sh"

SITE_KEY="${1:?usage: create-post.sh <site_key> <post_json_path>}"
POST_JSON="${2:?missing post_json_path}"
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

[ -f "$POST_JSON" ] || { echo "ERROR: post JSON not found: $POST_JSON" >&2; exit 1; }

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

# Slug pre-check (fail-closed): abort if slug is taken or if check itself fails.
# Bypass with ALLOW_DISAMBIGUATION=1 to let WP auto-disambiguate (append -N).
req_slug=$(jq -r '.slug // empty' "$POST_JSON")
if [ -n "$req_slug" ] && [ "${ALLOW_DISAMBIGUATION:-0}" != "1" ]; then
  check_err=$(mktemp)
  set +e
  check_out=$("$DIR/check-slug-conflict.sh" "$SITE_KEY" "$req_slug" 2>"$check_err")
  check_rc=$?
  set -e
  if [ "$check_rc" -ne 0 ]; then
    echo "[$(date -Iseconds)] create-post ABORT slug_check_failed slug=$req_slug rc=$check_rc" >>"$LOG"
    echo "ERROR: slug pre-check failed for '$req_slug' (exit $check_rc):" >&2
    cat "$check_err" >&2
    rm -f "$check_err"
    echo "To bypass the pre-check and let WP auto-disambiguate, re-run with ALLOW_DISAMBIGUATION=1" >&2
    exit 2
  fi
  rm -f "$check_err"
  avail=$(jq -r '.available' <<<"$check_out")
  if [ "$avail" != "true" ]; then
    echo "[$(date -Iseconds)] create-post ABORT slug_conflict slug=$req_slug conflicts=$(jq -c '.conflicting' <<<"$check_out")" >>"$LOG"
    echo "ERROR: slug '$req_slug' is not available. Conflicting entries:" >&2
    jq '.conflicting' <<<"$check_out" >&2
    echo "To override and let WP auto-disambiguate (-N suffix), re-run with ALLOW_DISAMBIGUATION=1" >&2
    exit 2
  fi
fi

tmp=$(mktemp)
http=$(wp_curl_auth_http "$tmp" "$user" "$pass" -H "Content-Type: application/json" \
  -X POST --data-binary "@$POST_JSON" "$wp/wp-json/wp/v2/posts")
resp=$(cat "$tmp")
rm -f "$tmp"

if [ "${http:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] create-post FAIL http=$http site=$SITE_KEY resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: create-post HTTP $http: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi

id=$(jq -r '.id // empty' <<<"$resp")
if [ -z "$id" ]; then
  echo "[$(date -Iseconds)] create-post FAIL http=$http no_id site=$SITE_KEY resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: create-post got HTTP $http but no id in response: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi
echo "[$(date -Iseconds)] create-post OK http=$http site=$SITE_KEY id=$id" >>"$LOG"
echo "$resp"
