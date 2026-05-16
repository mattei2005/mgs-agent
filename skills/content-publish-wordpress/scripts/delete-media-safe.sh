#!/bin/bash
set -euo pipefail

# delete-media-safe.sh — safely delete a WordPress media item created by the REC runner.
# Usage: delete-media-safe.sh <site_key> <media_id> [post_id]
# Safety gates:
# - Fetches media and optional post via REST.
# - Refuses deletion if media is the post featured_media.
# - Refuses deletion if media source_url or wp-image-<id> appears in post content.
# - Refuses deletion if media is attached to a different parent post.
# Credentials are read via resolve-credentials.sh and never printed.

# shellcheck source=/dev/null
source "$(dirname "$0")/wp-curl-auth.sh"

SITE_KEY="${1:?usage: delete-media-safe.sh <site_key> <media_id> [post_id]}"
MEDIA_ID="${2:?missing media_id}"
POST_ID="${3:-}"
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

case "$MEDIA_ID" in
  ''|*[!0-9]*) echo "ERROR: media_id must be numeric" >&2; exit 2 ;;
esac
if [ -n "$POST_ID" ]; then
  case "$POST_ID" in
    *[!0-9]*) echo "ERROR: post_id must be numeric" >&2; exit 2 ;;
  esac
fi

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

media_tmp=$(mktemp)
http=$(wp_curl_auth_http "$media_tmp" "$user" "$pass" \
  "$wp/wp-json/wp/v2/media/$MEDIA_ID?context=edit")
media_resp=$(cat "$media_tmp")
rm -f "$media_tmp"

if [ "${http:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] delete-media-safe SKIP media_get http=$http site=$SITE_KEY media_id=$MEDIA_ID" >>"$LOG"
  jq -n --arg status "skipped" --arg reason "media_get_http_$http" --argjson media_id "$MEDIA_ID" '{status:$status, reason:$reason, media_id:$media_id}'
  exit 0
fi

source_url=$(jq -r '.source_url // empty' <<<"$media_resp")
parent_id=$(jq -r '.post // 0' <<<"$media_resp")

if [ -n "$POST_ID" ] && [ "$parent_id" != "0" ] && [ "$parent_id" != "$POST_ID" ]; then
  echo "[$(date -Iseconds)] delete-media-safe SKIP attached_elsewhere site=$SITE_KEY media_id=$MEDIA_ID parent=$parent_id post=$POST_ID" >>"$LOG"
  jq -n --arg status "skipped" --arg reason "attached_to_different_post" --argjson media_id "$MEDIA_ID" --argjson parent_id "$parent_id" '{status:$status, reason:$reason, media_id:$media_id, parent_id:$parent_id}'
  exit 0
fi

if [ -n "$POST_ID" ]; then
  post_tmp=$(mktemp)
  post_http=$(wp_curl_auth_http "$post_tmp" "$user" "$pass" \
    "$wp/wp-json/wp/v2/posts/$POST_ID?context=edit")
  post_resp=$(cat "$post_tmp")
  rm -f "$post_tmp"
  if [ "${post_http:0:1}" = "2" ]; then
    featured=$(jq -r '.featured_media // 0' <<<"$post_resp")
    content=$(jq -r '.content.raw // .content.rendered // ""' <<<"$post_resp")
    if [ "$featured" = "$MEDIA_ID" ]; then
      echo "[$(date -Iseconds)] delete-media-safe SKIP featured site=$SITE_KEY media_id=$MEDIA_ID post=$POST_ID" >>"$LOG"
      jq -n --arg status "skipped" --arg reason "is_featured_media" --argjson media_id "$MEDIA_ID" '{status:$status, reason:$reason, media_id:$media_id}'
      exit 0
    fi
    if grep -Fq "wp-image-$MEDIA_ID" <<<"$content" || { [ -n "$source_url" ] && grep -Fq "$source_url" <<<"$content"; }; then
      echo "[$(date -Iseconds)] delete-media-safe SKIP content_ref site=$SITE_KEY media_id=$MEDIA_ID post=$POST_ID" >>"$LOG"
      jq -n --arg status "skipped" --arg reason "referenced_in_post_content" --argjson media_id "$MEDIA_ID" '{status:$status, reason:$reason, media_id:$media_id}'
      exit 0
    fi
  else
    echo "[$(date -Iseconds)] delete-media-safe WARN post_get http=$post_http site=$SITE_KEY media_id=$MEDIA_ID post=$POST_ID" >>"$LOG"
  fi
fi

del_tmp=$(mktemp)
del_http=$(wp_curl_auth_http "$del_tmp" "$user" "$pass" \
  -X DELETE "$wp/wp-json/wp/v2/media/$MEDIA_ID?force=true")
del_resp=$(cat "$del_tmp")
rm -f "$del_tmp"

if [ "${del_http:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] delete-media-safe FAIL delete_http=$del_http site=$SITE_KEY media_id=$MEDIA_ID resp=$(echo "$del_resp" | head -c 300)" >>"$LOG"
  jq -n --arg status "error" --arg reason "delete_http_$del_http" --argjson media_id "$MEDIA_ID" '{status:$status, reason:$reason, media_id:$media_id}'
  exit 0
fi

echo "[$(date -Iseconds)] delete-media-safe OK site=$SITE_KEY media_id=$MEDIA_ID" >>"$LOG"
jq -n --arg status "deleted" --argjson media_id "$MEDIA_ID" --arg source_url "$source_url" '{status:$status, media_id:$media_id, source_url:$source_url}'
