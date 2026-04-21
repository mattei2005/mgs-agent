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

resp=$(curl -sS -u "$user:$pass" \
  -H "Content-Disposition: attachment; filename=\"$FILENAME\"" \
  -H "Content-Type: $mime" \
  --data-binary "@$IMAGE_PATH" \
  "$wp/wp-json/wp/v2/media")

id=$(jq -r '.id // empty' <<<"$resp")
url=$(jq -r '.source_url // empty' <<<"$resp")

if [ -z "$id" ]; then
  echo "[$(date -Iseconds)] upload-image FAIL site=$SITE_KEY file=$FILENAME resp=$resp" >>"$LOG"
  echo "ERROR: upload failed: $resp" >&2
  exit 1
fi

echo "[$(date -Iseconds)] upload-image OK site=$SITE_KEY file=$FILENAME id=$id" >>"$LOG"
jq -n --argjson id "$id" --arg url "$url" '{id:$id, source_url:$url}'
