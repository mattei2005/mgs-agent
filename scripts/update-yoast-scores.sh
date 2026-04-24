#!/usr/bin/env bash
# =============================================================================
# update-yoast-scores.sh
#
# Computes real Yoast SEO + readability scores via Node/@yoast/yoastseo,
# writes them to wp_postmeta, and rebuilds the Yoast indexable via WP-CLI
# over SSH jump (S03 → S01).
#
# Usage:
#   bash update-yoast-scores.sh <post_id> <site_key>
#
# Example:
#   bash update-yoast-scores.sh 62010 eggbev
#
# Dependencies:
#   - /root/mgs-agent/.env           (WP_URL, SSH vars)
#   - resolve-credentials.sh         (fetches WP user/pass from 1Password)
#   - yoast-scorer/yoast-score-updater.js
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="/root/mgs-agent/.env"
SCORER_DIR="${SCRIPT_DIR}/yoast-scorer"
RESOLVE_CREDS="${SCRIPT_DIR}/../skills/content-publish-wordpress/scripts/resolve-credentials.sh"

# ─── args ────────────────────────────────────────────────────────────────────
POST_ID="${1:-}"
SITE_KEY="${2:-eggbev}"

if [[ -z "$POST_ID" ]]; then
  echo "Usage: $0 <post_id> [site_key]" >&2
  exit 1
fi

echo "[yoast-scores] Post ID: ${POST_ID} | Site: ${SITE_KEY}"

# ─── load env ────────────────────────────────────────────────────────────────
set -a && . "${ENV_FILE}" && set +a

# ─── resolve credentials ─────────────────────────────────────────────────────
CREDS=$(bash "${RESOLVE_CREDS}" "${SITE_KEY}" 2>/dev/null)
WP_URL=$(echo "$CREDS"  | grep '^WP_URL='  | cut -d= -f2-)
WP_USER=$(echo "$CREDS" | grep '^WP_USER=' | cut -d= -f2-)
WP_PASS=$(echo "$CREDS" | grep '^WP_PASS=' | cut -d= -f2-)

if [[ -z "$WP_URL" || -z "$WP_USER" || -z "$WP_PASS" ]]; then
  echo "[yoast-scores] ERROR: Could not resolve credentials for ${SITE_KEY}" >&2
  exit 1
fi

# ─── run Node scorer ─────────────────────────────────────────────────────────
echo "[yoast-scores] Running Yoast analysis..."

RESULT=$(node "${SCORER_DIR}/yoast-score-updater.js" "$POST_ID" "$WP_URL" "$WP_USER" "$WP_PASS" 2>/dev/null)

if [[ -z "$RESULT" ]]; then
  echo "[yoast-scores] ERROR: scorer returned empty output" >&2
  exit 1
fi

SEO_SCORE=$(echo "$RESULT"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['seo'])")
READ_SCORE=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['readability'])")
SEO_COLOR=$(echo "$RESULT"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['seo_color'])")
READ_COLOR=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['read_color'])")

echo "[yoast-scores] SEO: ${SEO_SCORE} (${SEO_COLOR}) | Readability: ${READ_SCORE} (${READ_COLOR})"

# ─── SSH config from env ──────────────────────────────────────────────────────
SSH_JUMP="${SSH_S03_USER}@${SSH_S03_HOST}"
SSH_TARGET="${SSH_S01_USER}@${SSH_S01_HOST}"
SSH_KEY="${SSH_KEY_PATH}"
WP_PATH="${WP_EGGBEV_PATH:-/home/eggbev/webapps/eggbev}"

SSH_CMD="ssh -i ${SSH_KEY} -J ${SSH_JUMP} ${SSH_TARGET} -o StrictHostKeyChecking=no"

# ─── write postmeta via WP-CLI ────────────────────────────────────────────────
echo "[yoast-scores] Writing postmeta via WP-CLI..."

$SSH_CMD "wp --path=${WP_PATH} post meta update ${POST_ID} _yoast_wpseo_linkdex ${SEO_SCORE} 2>&1"
$SSH_CMD "wp --path=${WP_PATH} post meta update ${POST_ID} _yoast_wpseo_content_score ${READ_SCORE} 2>&1"

echo "[yoast-scores] postmeta written."

# ─── rebuild Yoast indexable ─────────────────────────────────────────────────
echo "[yoast-scores] Rebuilding Yoast indexable..."

$SSH_CMD "wp --path=${WP_PATH} yoast index --object-id=${POST_ID} --object-type=post 2>&1" || \
  echo "[yoast-scores] WARN: yoast index command returned non-zero (may be OK if post updated)"

echo "[yoast-scores] Done. Post ${POST_ID}: SEO=${SEO_SCORE} (${SEO_COLOR}), Readability=${READ_SCORE} (${READ_COLOR})"
