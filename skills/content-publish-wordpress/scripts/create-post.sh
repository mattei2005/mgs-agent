#!/bin/bash
set -e

SITE_KEY="${1:?usage: create-post.sh <site_key> <post_json_path>}"
POST_JSON="${2:?missing post_json_path}"
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

[ -f "$POST_JSON" ] || { echo "ERROR: post JSON not found: $POST_JSON" >&2; exit 1; }

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

resp=$(curl -sS -u "$user:$pass" -H "Content-Type: application/json" \
  -X POST --data-binary "@$POST_JSON" "$wp/wp-json/wp/v2/posts")
id=$(jq -r '.id // empty' <<<"$resp")
if [ -z "$id" ]; then
  echo "[$(date -Iseconds)] create-post FAIL site=$SITE_KEY resp=$resp" >>"$LOG"
  echo "ERROR: post creation failed: $resp" >&2
  exit 1
fi
echo "[$(date -Iseconds)] create-post OK site=$SITE_KEY id=$id" >>"$LOG"
echo "$resp"
