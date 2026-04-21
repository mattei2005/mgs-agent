#!/bin/bash
set -e

SITE_KEY="${1:?usage: update-yoast.sh <site_key> <post_id> <yoast_json_path> [verify]}"
POST_ID="${2:?missing post_id}"
YOAST_JSON="${3:?missing yoast_json_path}"
VERIFY="${4:-}"   # "verify" or "--verify" = GET after PUTs to confirm Yoast fields were saved
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

[ -f "$YOAST_JSON" ] || { echo "ERROR: yoast JSON not found: $YOAST_JSON" >&2; exit 1; }
case "$VERIFY" in verify|--verify) VERIFY="1" ;; "") VERIFY="" ;; *) echo "ERROR: 4th arg must be 'verify' or omitted" >&2; exit 1 ;; esac

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

# PUT 1: only meta
meta_only=$(jq '{meta: .meta}' "$YOAST_JSON")
r1=$(curl -sS -u "$user:$pass" -H "Content-Type: application/json" \
  -X PUT -d "$meta_only" "$wp/wp-json/wp/v2/posts/$POST_ID")
if ! jq -e '.id' <<<"$r1" >/dev/null 2>&1; then
  echo "[$(date -Iseconds)] update-yoast PUT1 FAIL id=$POST_ID resp=$r1" >>"$LOG"
  echo "ERROR: PUT1 failed: $r1" >&2
  exit 1
fi

sleep 2

# PUT 2: title + content + meta to trigger save_post
full=$(jq '{title: .title, content: .content, meta: .meta}' "$YOAST_JSON")
r2=$(curl -sS -u "$user:$pass" -H "Content-Type: application/json" \
  -X PUT -d "$full" "$wp/wp-json/wp/v2/posts/$POST_ID")
if ! jq -e '.id' <<<"$r2" >/dev/null 2>&1; then
  echo "[$(date -Iseconds)] update-yoast PUT2 FAIL id=$POST_ID resp=$r2" >>"$LOG"
  echo "ERROR: PUT2 failed: $r2" >&2
  exit 1
fi

if [ -n "$VERIFY" ]; then
  sleep 1
  got=$(curl -sS -u "$user:$pass" "$wp/wp-json/wp/v2/posts/$POST_ID?context=edit")
  want_t=$(jq -r '.meta._yoast_wpseo_title // ""' "$YOAST_JSON")
  want_d=$(jq -r '.meta._yoast_wpseo_metadesc // ""' "$YOAST_JSON")
  want_f=$(jq -r '.meta._yoast_wpseo_focuskw // ""' "$YOAST_JSON")
  got_t=$(jq -r '.meta._yoast_wpseo_title // ""' <<<"$got")
  got_d=$(jq -r '.meta._yoast_wpseo_metadesc // ""' <<<"$got")
  got_f=$(jq -r '.meta._yoast_wpseo_focuskw // ""' <<<"$got")
  miss=()
  [ "$got_t" = "$want_t" ] || miss+=("_yoast_wpseo_title (got='$got_t' want='$want_t')")
  [ "$got_d" = "$want_d" ] || miss+=("_yoast_wpseo_metadesc (got='$got_d' want='$want_d')")
  [ "$got_f" = "$want_f" ] || miss+=("_yoast_wpseo_focuskw (got='$got_f' want='$want_f')")
  if [ ${#miss[@]} -gt 0 ]; then
    echo "[$(date -Iseconds)] update-yoast VERIFY FAIL id=$POST_ID missing=${miss[*]}" >>"$LOG"
    echo "ERROR: Yoast verify mismatch on post $POST_ID:" >&2
    for m in "${miss[@]}"; do echo "  - $m" >&2; done
    exit 3
  fi
  echo "[$(date -Iseconds)] update-yoast VERIFY OK id=$POST_ID" >>"$LOG"
fi

echo "[$(date -Iseconds)] update-yoast OK id=$POST_ID" >>"$LOG"
jq -n --argjson id "$POST_ID" --arg v "$VERIFY" '{ok:true, post_id:$id, verified: ($v != "")}'
