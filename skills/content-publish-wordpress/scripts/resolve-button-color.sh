#!/bin/bash
set -euo pipefail

# Load env vars (OP_DEFAULT_VAULT, etc.) — runs under systemd/cron too
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SITE_KEY="${1:?usage: resolve-button-color.sh <site_key> [override]}"
OVERRIDE="${2:-}"
SITES_JSON="/root/mgs-agent/data/sites.json"
COLORS_JSON="/root/mgs-agent/data/button-colors.json"

[ -f "$SITES_JSON" ] || { echo "ERROR: sites.json not found: $SITES_JSON" >&2; exit 1; }
[ -f "$COLORS_JSON" ] || { echo "ERROR: button-colors.json not found: $COLORS_JSON" >&2; exit 1; }

HEX_RE='^#[0-9A-Fa-f]{6}$'

validate_hex() {
  local v="$1"
  if [[ ! "$v" =~ $HEX_RE ]]; then
    echo "ERROR: Invalid hex color: '$v' (expected #RRGGBB)" >&2
    exit 1
  fi
}

if [ -n "$OVERRIDE" ]; then
  if [[ "$OVERRIDE" == \#* ]]; then
    hex="$OVERRIDE"
    validate_hex "$hex"
  else
    hex=$(jq -r --arg n "$OVERRIDE" '.[$n] // empty' "$COLORS_JSON")
    if [ -z "$hex" ]; then
      valid_names=$(jq -r 'keys | join(", ")' "$COLORS_JSON")
      echo "ERROR: Unknown button color name: '$OVERRIDE'. Valid names: $valid_names" >&2
      exit 1
    fi
    validate_hex "$hex"
  fi
  source="request_override"
else
  site=$(jq -e --arg k "$SITE_KEY" '.[$k]' "$SITES_JSON") || {
    echo "ERROR: site_key '$SITE_KEY' not found in $SITES_JSON" >&2
    exit 1
  }
  hex=$(jq -r '.default_button_color // empty' <<<"$site")
  if [ -z "$hex" ]; then
    echo "ERROR: site '$SITE_KEY' has no default_button_color and no override provided" >&2
    exit 1
  fi
  validate_hex "$hex"
  source="site_default"
fi

jq -n --arg h "$hex" --arg s "$source" --arg i "$OVERRIDE" \
  '{hex:$h, source:$s, input:(if $i == "" then null else $i end)}'
