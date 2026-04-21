#!/bin/bash
set -e

SITE_KEY="${1:?usage: upload-image.sh <site_key> <image_path> <filename>}"
IMAGE_PATH="${2:?missing image_path}"
FILENAME="${3:?missing filename}"
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

[ -f "$IMAGE_PATH" ] || { echo "ERROR: image not found: $IMAGE_PATH" >&2; exit 1; }

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

mime="image/png"
case "${FILENAME,,}" in
  *.jpg|*.jpeg) mime="image/jpeg" ;;
  *.webp) mime="image/webp" ;;
esac

tmp=$(mktemp)
http=$(curl -sS -o "$tmp" -w '%{http_code}' -u "$user:$pass" \
  -H "Content-Disposition: attachment; filename=\"$FILENAME\"" \
  -H "Content-Type: $mime" \
  --data-binary "@$IMAGE_PATH" \
  "$wp/wp-json/wp/v2/media" || echo "000")
resp=$(cat "$tmp")
rm -f "$tmp"

if [ "${http:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] upload-image FAIL http=$http site=$SITE_KEY file=$FILENAME resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: upload-image HTTP $http: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi

id=$(jq -r '.id // empty' <<<"$resp")
url=$(jq -r '.source_url // empty' <<<"$resp")

if [ -z "$id" ]; then
  echo "[$(date -Iseconds)] upload-image FAIL http=$http no_id site=$SITE_KEY file=$FILENAME resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: upload-image got HTTP $http but no id in response: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi

echo "[$(date -Iseconds)] upload-image OK http=$http site=$SITE_KEY file=$FILENAME id=$id" >>"$LOG"
jq -n --argjson id "$id" --arg url "$url" '{id:$id, source_url:$url}'
