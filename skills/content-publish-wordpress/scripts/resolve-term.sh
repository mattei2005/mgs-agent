#!/bin/bash
set -e

# Helper para curl autenticado seguro (não expõe senha em ps aux)
source "$(dirname "$0")/wp-curl-auth.sh"

SITE_KEY="${1:?usage: resolve-term.sh <site_key> <taxonomy> <name> [strict]}"
TAX="${2:?missing taxonomy (categories|tags)}"
NAME="${3:?missing name}"
MODE="${4:-create}"   # "strict" = fail with exit 2 if term doesn't exist (no creation)
LOG="/root/mgs-agent/logs/publish-wordpress.log"
DIR="$(cd "$(dirname "$0")" && pwd)"

case "$TAX" in categories|tags) ;; *) echo "ERROR: taxonomy must be categories or tags" >&2; exit 1 ;; esac
case "$MODE" in strict|--strict) MODE="strict" ;; create|"") MODE="create" ;; *) echo "ERROR: 4th arg must be 'strict' or omitted" >&2; exit 1 ;; esac

creds=$("$DIR/resolve-credentials.sh" "$SITE_KEY")
wp=$(jq -r '.wp_url' <<<"$creds")
user=$(jq -r '.username' <<<"$creds")
pass=$(jq -r '.password' <<<"$creds")

search=$(jq -rn --arg n "$NAME" '$n|@uri')
tmp_list=$(mktemp)
h_list=$(wp_curl_auth "$user" "$pass" -sS -o "$tmp_list" -w '%{http_code}' "$wp/wp-json/wp/v2/$TAX?search=$search&per_page=100" || echo "000")
list=$(cat "$tmp_list")
rm -f "$tmp_list"

if [ "${h_list:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] resolve-term SEARCH FAIL http=$h_list site=$SITE_KEY tax=$TAX name=$NAME resp=$(echo "$list" | head -c 500)" >>"$LOG"
  echo "ERROR: resolve-term search HTTP $h_list: $(echo "$list" | head -c 500)" >&2
  exit 1
fi

match=$(jq --arg n "$NAME" '[.[] | select(.name==$n)][0] // empty' <<<"$list" 2>/dev/null)

if [ -n "$match" ]; then
  id=$(jq -r '.id' <<<"$match")
  slug=$(jq -r '.slug' <<<"$match")
  echo "[$(date -Iseconds)] resolve-term HIT site=$SITE_KEY tax=$TAX name=$NAME id=$id" >>"$LOG"
  jq -n --argjson id "$id" --arg n "$NAME" --arg s "$slug" '{id:$id, name:$n, slug:$s}'
  exit 0
fi

if [ "$MODE" = "strict" ]; then
  echo "[$(date -Iseconds)] resolve-term MISS-STRICT site=$SITE_KEY tax=$TAX name=$NAME" >>"$LOG"
  echo "ERROR: strict mode — term '$NAME' not found in $TAX on $SITE_KEY" >&2
  exit 2
fi

body=$(jq -n --arg n "$NAME" '{name:$n}')
tmp_c=$(mktemp)
h_c=$(wp_curl_auth "$user" "$pass" -sS -o "$tmp_c" -w '%{http_code}' -H "Content-Type: application/json" \
  -X POST -d "$body" "$wp/wp-json/wp/v2/$TAX" || echo "000")
resp=$(cat "$tmp_c")
rm -f "$tmp_c"

if [ "${h_c:0:1}" != "2" ]; then
  echo "[$(date -Iseconds)] resolve-term CREATE FAIL http=$h_c site=$SITE_KEY tax=$TAX name=$NAME resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: resolve-term create HTTP $h_c: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi

id=$(jq -r '.id // empty' <<<"$resp")
if [ -z "$id" ]; then
  echo "[$(date -Iseconds)] resolve-term CREATE FAIL http=$h_c no_id site=$SITE_KEY tax=$TAX name=$NAME resp=$(echo "$resp" | head -c 500)" >>"$LOG"
  echo "ERROR: resolve-term create got HTTP $h_c but no id in response: $(echo "$resp" | head -c 500)" >&2
  exit 1
fi
slug=$(jq -r '.slug' <<<"$resp")
echo "[$(date -Iseconds)] resolve-term NEW site=$SITE_KEY tax=$TAX name=$NAME id=$id" >>"$LOG"
jq -n --argjson id "$id" --arg n "$NAME" --arg s "$slug" '{id:$id, name:$n, slug:$s}'
