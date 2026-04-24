#!/bin/bash
# yoast-score-post.sh
#
# Calcula scores Yoast para um post e grava no banco via WP-CLI + reindex.
#
# Usage:
#   bash yoast-score-post.sh <site_key> <post_id>
#
# Exemplo:
#   bash yoast-score-post.sh eggbev 62004
#
# O script:
#   1. Resolve credenciais do site (via resolve-credentials.sh)
#   2. Roda yoast-scorer.js (Node) para calcular seo_score + readability_score
#   3. SSH jump S03→S01: grava scores no postmeta via WP-CLI
#   4. SSH jump S03→S01: reindex o post via wp yoast index
#   5. Retorna JSON com resultado final

set -euo pipefail

SITE_KEY="${1:-}"
POST_ID="${2:-}"
SCORER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/yoast-scorer" && pwd)"
PUBLISH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../content-publish-wordpress/scripts" && pwd)"

if [[ -z "$SITE_KEY" || -z "$POST_ID" ]]; then
  echo '{"status":"error","message":"Usage: yoast-score-post.sh <site_key> <post_id>"}' >&2
  exit 1
fi

# ── Load env ───────────────────────────────────────────────────────────────────
set -a
source /root/mgs-agent/.env
set +a

# ── Resolve WP credentials ────────────────────────────────────────────────────
CREDS=$(bash "$PUBLISH_DIR/resolve-credentials.sh" "$SITE_KEY" 2>/dev/null)
WP_URL=$(echo "$CREDS"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['wp_url'])")
WP_USER=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['username'])")
WP_PASS=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['password'])")

# ── Resolve SSH credentials ────────────────────────────────────────────────────
S03_PASS=$(op item get 'Runcloud Server 03 - 46.4.95.117- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal 2>/dev/null)
S01_PASS=$(op item get 'Runcloud Server 01 - 162.55.28.178- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal 2>/dev/null)

# ── Resolve WP path from sites.json ───────────────────────────────────────────
WP_PATH=$(python3 -c "
import json
with open('/root/mgs-agent/data/sites.json') as f:
    sites = json.load(f)
site = sites.get('$SITE_KEY', {})
print(site.get('wp_path', '/home/runcloud/webapps/$SITE_KEY'))
" 2>/dev/null || echo "/home/runcloud/webapps/$SITE_KEY")

# ── Step 1: Calculate scores via Node ─────────────────────────────────────────
SCORE_JSON=$(node "$SCORER_DIR/yoast-scorer.js" "$WP_URL" "$POST_ID" "$WP_USER" "$WP_PASS" 2>/dev/null)
SCORE_STATUS=$(echo "$SCORE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))")

if [[ "$SCORE_STATUS" != "ok" ]]; then
  echo "$SCORE_JSON"
  exit 1
fi

SEO_SCORE=$(echo "$SCORE_JSON"  | python3 -c "import sys,json; print(json.load(sys.stdin)['seo_score'])")
READ_SCORE=$(echo "$SCORE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['readability_score'])")

# ── Step 2: Write scores to postmeta + reindex via SSH jump ───────────────────
REMOTE_SCRIPT=$(cat <<REMOTE
#!/bin/bash
WP_PATH="$WP_PATH"
POST_ID="$POST_ID"
SEO="$SEO_SCORE"
READ="$READ_SCORE"

# Gravar no postmeta
sudo -u runcloud wp --path="\$WP_PATH" post meta update "\$POST_ID" _yoast_wpseo_linkdex "\$SEO" 2>&1
sudo -u runcloud wp --path="\$WP_PATH" post meta update "\$POST_ID" _yoast_wpseo_content_score "\$READ" 2>&1

# Reindex para atualizar wp_yoast_indexable
sudo -u runcloud wp --path="\$WP_PATH" yoast index --reindex 2>&1 | grep -E "post $POST_ID|Done|Error|reindex" | head -5 || true

# Verify indexable was updated
sudo -u runcloud wp --path="\$WP_PATH" db query \
  "SELECT primary_focus_keyword_score, readability_score FROM wp_yoast_indexable WHERE object_id=$POST_ID AND object_type='post' LIMIT 1" \
  --skip-column-names 2>&1

echo "WPCLI_DONE"
REMOTE
)

# Write remote script to tmp
echo "$REMOTE_SCRIPT" > /tmp/yoast_reindex_$POST_ID.sh
chmod +x /tmp/yoast_reindex_$POST_ID.sh

# SCP remote script to S01
cat > /tmp/_scp_yoast_$POST_ID.exp << EOFEXP
#!/usr/bin/expect -f
set s03 [lindex \$argv 0]
set s01 [lindex \$argv 1]
set timeout 30
spawn scp -o StrictHostKeyChecking=no -J zeus@46.4.95.117 /tmp/yoast_reindex_$POST_ID.sh zeus@162.55.28.178:/tmp/yoast_reindex_$POST_ID.sh
expect "46.4.95.117's password:"
send "\$s03\r"
expect "162.55.28.178's password:"
send "\$s01\r"
expect {
    "100%" { exp_continue }
    eof {}
}
EOFEXP
chmod +x /tmp/_scp_yoast_$POST_ID.exp
/tmp/_scp_yoast_$POST_ID.exp "$S03_PASS" "$S01_PASS" > /dev/null 2>&1

# Execute remote script via SSH
cat > /tmp/_ssh_yoast_$POST_ID.exp << EOFEXP
#!/usr/bin/expect -f
set s03 [lindex \$argv 0]
set s01 [lindex \$argv 1]
set timeout 90
spawn ssh -o StrictHostKeyChecking=no -J zeus@46.4.95.117 zeus@162.55.28.178
expect "46.4.95.117's password:"
send "\$s03\r"
expect "162.55.28.178's password:"
send "\$s01\r"
expect "Made with"
sleep 3
send "bash /tmp/yoast_reindex_$POST_ID.sh\n"
sleep 30
send "exit\r"
expect eof
EOFEXP
chmod +x /tmp/_ssh_yoast_$POST_ID.exp
SSH_OUTPUT=$(/tmp/_ssh_yoast_$POST_ID.exp "$S03_PASS" "$S01_PASS" 2>/dev/null)

# Parse indexable scores from output (last two numbers before WPCLI_DONE)
INDEXABLE_LINE=$(echo "$SSH_OUTPUT" | grep -E "^[0-9]+[[:space:]]+[0-9]+" | tail -1 || echo "")
IDX_SEO=$(echo  "$INDEXABLE_LINE" | awk '{print $1}' || echo "?")
IDX_READ=$(echo "$INDEXABLE_LINE" | awk '{print $2}' || echo "?")

# Cleanup tmp files
rm -f /tmp/yoast_reindex_$POST_ID.sh /tmp/_scp_yoast_$POST_ID.exp /tmp/_ssh_yoast_$POST_ID.exp

# ── Output ────────────────────────────────────────────────────────────────────
python3 - <<PYEOF
import json
print(json.dumps({
    "status":            "ok",
    "post_id":           int("$POST_ID"),
    "seo_score":         int("$SEO_SCORE"),
    "readability_score": int("$READ_SCORE"),
    "indexable_seo":     "$IDX_SEO",
    "indexable_read":    "$IDX_READ",
}))
PYEOF
