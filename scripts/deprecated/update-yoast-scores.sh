#!/usr/bin/env bash
# =============================================================================
# update-yoast-scores.sh
#
# Computes real Yoast SEO + readability scores via Node/@yoast/yoastseo,
# writes them to wp_postmeta, and rebuilds the Yoast indexable via WP-CLI
# over SSH jump (S03 → S01) using expect for password auth.
#
# Usage:
#   bash update-yoast-scores.sh <post_id> [site_key]
#
# Example:
#   bash update-yoast-scores.sh 62010 eggbev
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="/root/mgs-agent/.env"
SCORER_DIR="${SCRIPT_DIR}/yoast-scorer"
RESOLVE_CREDS="${SCRIPT_DIR}/../skills/content-publish-wordpress/scripts/resolve-credentials.sh"

S03_HOST="46.4.95.117"
S01_HOST="162.55.28.178"
S01_WP_PATH="/home/runcloud/webapps/eggbev"

# ─── args ────────────────────────────────────────────────────────────────────
POST_ID="${1:-}"
SITE_KEY="${2:-eggbev}"

if [[ -z "$POST_ID" ]]; then
  echo "Usage: $0 <post_id> [site_key]" >&2
  exit 1
fi

echo "[yoast-scores] Post ID: ${POST_ID} | Site: ${SITE_KEY}"

# ─── load env + credentials ──────────────────────────────────────────────────
set -a && . "${ENV_FILE}" && set +a

CREDS=$(bash "${RESOLVE_CREDS}" "${SITE_KEY}" 2>/dev/null)
WP_URL=$(echo  "$CREDS" | grep '^WP_URL='  | cut -d= -f2-)
WP_USER=$(echo "$CREDS" | grep '^WP_USER=' | cut -d= -f2-)
WP_PASS=$(echo "$CREDS" | grep '^WP_PASS=' | cut -d= -f2-)

if [[ -z "$WP_URL" || -z "$WP_USER" || -z "$WP_PASS" ]]; then
  echo "[yoast-scores] ERROR: Could not resolve WP credentials for ${SITE_KEY}" >&2
  exit 1
fi

S03_PASS=$(op item get 'Runcloud Server 03 - 46.4.95.117- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal 2>/dev/null)
S01_PASS=$(op item get 'Runcloud Server 01 - 162.55.28.178- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal 2>/dev/null)

if [[ -z "$S03_PASS" || -z "$S01_PASS" ]]; then
  echo "[yoast-scores] ERROR: Could not resolve SSH credentials from 1Password" >&2
  exit 1
fi

# ─── run Node scorer ─────────────────────────────────────────────────────────
echo "[yoast-scores] Running Yoast analysis..."

RESULT=$(node "${SCORER_DIR}/yoast-score-updater.js" "$POST_ID" "$WP_URL" "$WP_USER" "$WP_PASS" 2>/dev/null)

if [[ -z "$RESULT" ]]; then
  echo "[yoast-scores] ERROR: scorer returned empty output" >&2
  exit 1
fi

SEO_SCORE=$(echo  "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['seo'])")
READ_SCORE=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['readability'])")
SEO_COLOR=$(echo  "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['seo_color'])")
READ_COLOR=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['read_color'])")

echo "[yoast-scores] SEO: ${SEO_SCORE} (${SEO_COLOR}) | Readability: ${READ_SCORE} (${READ_COLOR})"

# ─── write remote script ─────────────────────────────────────────────────────
cat > /tmp/yoast_meta_update.sh << EOFSH
#!/bin/bash
set -e
WP="${S01_WP_PATH}"
POST="${POST_ID}"
SEO="${SEO_SCORE}"
READ="${READ_SCORE}"

echo "Writing postmeta..."
sudo -u runcloud wp --path=\$WP post meta update \$POST _yoast_wpseo_linkdex \$SEO
sudo -u runcloud wp --path=\$WP post meta update \$POST _yoast_wpseo_content_score \$READ

echo "Rebuilding Yoast indexable..."
sudo -u runcloud wp --path=\$WP yoast index --object-id=\$POST --object-type=post 2>&1 || \
  echo "WARN: yoast index returned non-zero (may be OK)"

# Verify
echo "--- Verification ---"
sudo -u runcloud wp --path=\$WP post meta get \$POST _yoast_wpseo_linkdex
sudo -u runcloud wp --path=\$WP post meta get \$POST _yoast_wpseo_content_score
echo "--- Done ---"
EOFSH
chmod +x /tmp/yoast_meta_update.sh

# ─── SCP script to S01 via jump ───────────────────────────────────────────────
echo "[yoast-scores] Uploading remote script to S01..."

cat > /tmp/_yoast_scp.exp << 'EOFEXP'
#!/usr/bin/expect -f
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set timeout 30
spawn scp -o StrictHostKeyChecking=no \
  -J zeus@46.4.95.117 \
  /tmp/yoast_meta_update.sh \
  zeus@162.55.28.178:/tmp/yoast_meta_update.sh
expect "46.4.95.117's password:"
send "$s03\r"
expect "162.55.28.178's password:"
send "$s01\r"
expect {
    "100%" { exp_continue }
    eof    {}
}
EOFEXP
chmod +x /tmp/_yoast_scp.exp
/tmp/_yoast_scp.exp "$S03_PASS" "$S01_PASS"

# ─── Execute script on S01 ────────────────────────────────────────────────────
echo "[yoast-scores] Executing WP-CLI on S01..."

cat > /tmp/_yoast_ssh.exp << 'EOFEXP'
#!/usr/bin/expect -f
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set timeout 60
spawn ssh -o StrictHostKeyChecking=no -J zeus@46.4.95.117 zeus@162.55.28.178
expect "46.4.95.117's password:"
send "$s03\r"
expect "162.55.28.178's password:"
send "$s01\r"
expect "Made with"
sleep 3
send "bash /tmp/yoast_meta_update.sh\n"
sleep 20
send "exit\r"
expect eof
EOFEXP
chmod +x /tmp/_yoast_ssh.exp
/tmp/_yoast_ssh.exp "$S03_PASS" "$S01_PASS"

echo "[yoast-scores] ✅ Complete. Post ${POST_ID}: SEO=${SEO_SCORE} (${SEO_COLOR}), Readability=${READ_SCORE} (${READ_COLOR})"
