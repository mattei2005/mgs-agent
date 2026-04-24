#!/usr/bin/env bash
# update-yoast-scores.sh
#
# Computes real Yoast SEO + readability scores via Node/@yoast/yoastseo,
# writes them to wp_postmeta, and rebuilds the Yoast indexable via WP-CLI.
#
# Usage:
#   bash update-yoast-scores.sh <site_key> <post_id>
#
# Example:
#   bash update-yoast-scores.sh eggbev 62004
#
# The script sources .env for 1Password + resolves WP credentials,
# then SSHes into the server (via jump if needed) to run WP-CLI.

set -euo pipefail

SITE_KEY="${1:-}"
POST_ID="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(cd "$SCRIPT_DIR/../../" && pwd)"
NODE_SCRIPT="$SCRIPT_DIR/yoast-scorer/yoast-score-updater.js"
RESOLVE_CREDS="$SKILLS_DIR/skills/content-publish-wordpress/scripts/resolve-credentials.sh"

if [[ -z "$SITE_KEY" || -z "$POST_ID" ]]; then
  echo '{"error":"Usage: update-yoast-scores.sh <site_key> <post_id>"}' >&2
  exit 1
fi

# ── Load env ──────────────────────────────────────────────────────────────────
set -a && . "$SKILLS_DIR/.env" && set +a

# ── Resolve WP credentials ───────────────────────────────────────────────────
CREDS=$(bash "$RESOLVE_CREDS" "$SITE_KEY" 2>/dev/null)
WP_URL=$(echo "$CREDS"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['wp_url'])")
WP_USER=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['username'])")
WP_PASS=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['password'])")

# ── Run Node scorer ───────────────────────────────────────────────────────────
echo "[update-yoast-scores] Running analysis for post $POST_ID on $SITE_KEY..." >&2

NODE_OUTPUT=$(node "$NODE_SCRIPT" "$POST_ID" "$WP_URL" "$WP_USER" "$WP_PASS" 2>&1)
echo "$NODE_OUTPUT" >&2

# Extract the JSON line
SCORES_LINE=$(echo "$NODE_OUTPUT" | grep '^SCORES_JSON:' | tail -1)
if [[ -z "$SCORES_LINE" ]]; then
  echo '{"error":"Node script did not produce SCORES_JSON output"}' >&2
  exit 2
fi

SCORES_JSON="${SCORES_LINE#SCORES_JSON:}"
SEO_SCORE=$(echo "$SCORES_JSON"         | python3 -c "import sys,json; print(json.load(sys.stdin)['seo_score'])")
READABILITY_SCORE=$(echo "$SCORES_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['readability_score'])")
SEO_COLOR=$(echo "$SCORES_JSON"         | python3 -c "import sys,json; print(json.load(sys.stdin)['seo_color'])")
READ_COLOR=$(echo "$SCORES_JSON"        | python3 -c "import sys,json; print(json.load(sys.stdin)['readability_color'])")

echo "[update-yoast-scores] SEO=$SEO_SCORE ($SEO_COLOR) Readability=$READABILITY_SCORE ($READ_COLOR)" >&2

# ── Resolve SSH config for this site ─────────────────────────────────────────
SITES_JSON="$SKILLS_DIR/data/sites.json"
WP_PATH=$(python3 -c "
import sys, json
sites = json.load(open('$SITES_JSON'))
site = sites.get('$SITE_KEY', {})
print(site.get('wp_path', '/home/runcloud/webapps/$SITE_KEY'))
")
SSH_SERVER=$(python3 -c "
import sys, json
sites = json.load(open('$SITES_JSON'))
site = sites.get('$SITE_KEY', {})
print(site.get('ssh_server', 'S01'))
")

echo "[update-yoast-scores] WP path: $WP_PATH, SSH server: $SSH_SERVER" >&2

# ── Load SSH credentials ─────────────────────────────────────────────────────
S03_PASS=$(op item get 'Runcloud Server 03 - 46.4.95.117- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal 2>/dev/null)
S01_PASS=$(op item get 'Runcloud Server 01 - 162.55.28.178- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal 2>/dev/null)

# ── Write remote script ───────────────────────────────────────────────────────
REMOTE_SCRIPT=$(cat <<REMOTE
#!/bin/bash
WP_PATH="$WP_PATH"
POST_ID="$POST_ID"
SEO_SCORE="$SEO_SCORE"
READABILITY_SCORE="$READABILITY_SCORE"

echo "[remote] Updating postmeta for post \$POST_ID..."

# Write scores to postmeta
sudo -u runcloud wp --path="\$WP_PATH" post meta update "\$POST_ID" _yoast_wpseo_linkdex "\$SEO_SCORE" 2>&1
sudo -u runcloud wp --path="\$WP_PATH" post meta update "\$POST_ID" _yoast_wpseo_content_score "\$READABILITY_SCORE" 2>&1

echo "[remote] Rebuilding Yoast indexable..."

# Rebuild indexable from postmeta
sudo -u runcloud wp --path="\$WP_PATH" yoast index --reindex --objects=post --object-id="\$POST_ID" 2>&1 || \
sudo -u runcloud wp --path="\$WP_PATH" yoast index --reindex 2>&1 | head -5

echo "[remote] Verifying indexable..."
sudo -u runcloud wp --path="\$WP_PATH" db query \
  "SELECT primary_focus_keyword_score, readability_score FROM wp_yoast_indexable WHERE object_id=\$POST_ID AND object_type='post' LIMIT 1;" 2>&1

echo "REMOTE_DONE"
REMOTE
)

echo "$REMOTE_SCRIPT" > /tmp/yoast_remote_$POST_ID.sh
chmod +x /tmp/yoast_remote_$POST_ID.sh

# ── SCP remote script ─────────────────────────────────────────────────────────
cat > /tmp/scp_yoast_scores.exp << 'EOFEXP'
#!/usr/bin/expect -f
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set postid [lindex $argv 2]
set timeout 30
spawn scp -o StrictHostKeyChecking=no -J zeus@46.4.95.117 /tmp/yoast_remote_$postid.sh zeus@162.55.28.178:/tmp/yoast_remote_$postid.sh
expect "46.4.95.117's password:"
send "$s03\r"
expect "162.55.28.178's password:"
send "$s01\r"
expect { "100%" { exp_continue } eof {} }
EOFEXP
chmod +x /tmp/scp_yoast_scores.exp
/tmp/scp_yoast_scores.exp "$S03_PASS" "$S01_PASS" "$POST_ID"

# ── Execute remote script ─────────────────────────────────────────────────────
cat > /tmp/run_yoast_scores.exp << EOFEXP
#!/usr/bin/expect -f
set s03 [lindex \$argv 0]
set s01 [lindex \$argv 1]
set postid [lindex \$argv 2]
set timeout 90

spawn ssh -o StrictHostKeyChecking=no -J zeus@46.4.95.117 zeus@162.55.28.178
expect "46.4.95.117's password:"
send "\$s03\r"
expect "162.55.28.178's password:"
send "\$s01\r"
expect "Made with"
sleep 3
send "bash /tmp/yoast_remote_\$postid.sh\n"
sleep 20
send "exit\r"
expect eof
EOFEXP
chmod +x /tmp/run_yoast_scores.exp

SSH_OUTPUT=$(/tmp/run_yoast_scores.exp "$S03_PASS" "$S01_PASS" "$POST_ID" 2>&1)
echo "$SSH_OUTPUT" >&2

# ── Final result ──────────────────────────────────────────────────────────────
if echo "$SSH_OUTPUT" | grep -q "REMOTE_DONE"; then
  echo "{\"ok\":true,\"post_id\":$POST_ID,\"seo_score\":$SEO_SCORE,\"readability_score\":$READABILITY_SCORE,\"seo_color\":\"$SEO_COLOR\",\"readability_color\":\"$READ_COLOR\"}"
else
  echo "{\"ok\":false,\"post_id\":$POST_ID,\"error\":\"Remote script did not complete\"}" >&2
  exit 1
fi
