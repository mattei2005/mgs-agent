#!/bin/bash
# yoast-score-post.sh
#
# Calcula scores Yoast para um post e grava no banco via WP-CLI.
#
# Usage:
#   bash yoast-score-post.sh <site_key> <post_id>
#
# Exemplo:
#   bash yoast-score-post.sh eggbev 62004
#
# Fluxo:
#   1. Resolve credenciais do site
#   2. Node yoast-scorer.js → calcula seo_score + readability_score
#   3. SSH S03→S01: WP-CLI atualiza postmeta (_yoast_wpseo_linkdex, content_score)
#   4. SSH S03→S01: SQL UPDATE direto no wp_yoast_indexable para o post
#   5. Retorna JSON com resultado

set -euo pipefail
# Validate all caller-controlled identifiers before env or vault access.
[[ "${1:-}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { printf "invalid site key\n" >&2; exit 2; }
[[ "${2:-}" =~ ^[1-9][0-9]*$ ]] || { printf "invalid object ID\n" >&2; exit 2; }


SITE_KEY="${1:-}"
POST_ID="${2:-}"
CANARY_NO_INDEX=0
if [ "${3:-}" = "--canary-noindex" ]; then
  [ "$SITE_KEY" = eggbev ] || { printf 'canary is restricted to eggbev\n' >&2; exit 2; }
  CANARY_NO_INDEX=1
elif [ -n "${3:-}" ]; then
  printf 'unsupported scoring option\n' >&2; exit 2
fi

SCORER_DIR="/root/mgs-agent/scripts/yoast-scorer"
PUBLISH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../content-publish-wordpress/scripts" && pwd)"

if [[ -z "$SITE_KEY" || -z "$POST_ID" ]]; then
  echo '{"status":"error","message":"Usage: yoast-score-post.sh <site_key> <post_id>"}' >&2
  exit 1
fi

# ── Load env ───────────────────────────────────────────────────────────────────
set -a
# shellcheck source=/dev/null
source /root/mgs-agent/.env
set +a

# ── Resolve WP credentials ─────────────────────────────────────────────────────
CREDS=$(bash "$PUBLISH_DIR/resolve-credentials.sh" "$SITE_KEY" 2>/dev/null)
WP_URL=$(echo  "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['wp_url'])")
WP_USER=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['username'])")
WP_PASS=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['password'])")

# ── Resolve SSH credentials ────────────────────────────────────────────────────
S03_PASS=$(op item get 'Runcloud Server 03 - 46.4.95.117- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal 2>/dev/null)
S01_PASS=$(op item get 'Runcloud Server 01 - 162.55.28.178- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal 2>/dev/null)

WP_PATH="/home/runcloud/webapps/$SITE_KEY"
TMP_DIR="$(mktemp -d /tmp/yoast-score-post.XXXXXX)"
REMOTE_SCRIPT="/tmp/yoast_update_${POST_ID}_$$.sh"
KNOWN_HOSTS_FILE="/root/.ssh/known_hosts_mgs"
SSH_OPTS="-o StrictHostKeyChecking=yes -o UserKnownHostsFile=${KNOWN_HOSTS_FILE}"
[ -s "$KNOWN_HOSTS_FILE" ] || { printf "pinned SSH trust is required\n" >&2; exit 2; }
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

# ── Step 1: Calculate scores via Node ─────────────────────────────────────────
SCORE_JSON=$(cd "$SCORER_DIR" && MGS_YOAST_WP_PASSWORD="$WP_PASS" node yoast-scorer.js "$WP_URL" "$POST_ID" "$WP_USER" 2>/dev/null)
SCORE_STATUS=$(echo "$SCORE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))")

if [[ "$SCORE_STATUS" != "ok" ]]; then
  echo "$SCORE_JSON"
  exit 1
fi

SEO_SCORE=$(echo  "$SCORE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['seo_score'])")
READ_SCORE=$(echo "$SCORE_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['readability_score'])")

# ── Step 2: Write postmeta + update indexable via SSH ─────────────────────────
cat > "${TMP_DIR}/yoast_update_${POST_ID}.sh" << REMOTE
#!/bin/bash
WP_PATH="$WP_PATH"
POST_ID="$POST_ID"
SEO="$SEO_SCORE"
READ="$READ_SCORE"

if [ '${CANARY_NO_INDEX}' = 1 ]; then
  [ "\$(sudo -u runcloud wp --path="\$WP_PATH" option get siteurl 2>/dev/null)" = 'https://eggbev.com' ] || exit 42
  [ "\$(sudo -u runcloud wp --path="\$WP_PATH" post get "\$POST_ID" --field=post_name 2>/dev/null)" = 'mgs-infra-canary-1556014718810853448' ] || exit 43
  [ "\$(sudo -u runcloud wp --path="\$WP_PATH" post get "\$POST_ID" --field=post_status 2>/dev/null)" = draft ] || exit 44
  sudo -u runcloud wp --path="\$WP_PATH" post meta update "\$POST_ID" _yoast_wpseo_meta-robots-noindex 1 || exit 45
  [ "\$(sudo -u runcloud wp --path="\$WP_PATH" post meta get "\$POST_ID" _yoast_wpseo_meta-robots-noindex 2>/dev/null)" = 1 ] || exit 46
  printf 'MGS_CANARY_NOINDEX_CONFIRMED\n'
fi


# 2a. Gravar no wp_postmeta
sudo -u runcloud wp --path="\$WP_PATH" post meta update "\$POST_ID" _yoast_wpseo_linkdex "\$SEO" 2>&1
sudo -u runcloud wp --path="\$WP_PATH" post meta update "\$POST_ID" _yoast_wpseo_content_score "\$READ" 2>&1

# 2b. UPDATE direto no wp_yoast_indexable (evita reindex global)
sudo -u runcloud wp --path="\$WP_PATH" db query \
  "UPDATE wp_yoast_indexable SET primary_focus_keyword_score=\$SEO, readability_score=\$READ WHERE object_id=\$POST_ID AND object_type='post'" \
  2>&1

# 2c. Verify
sudo -u runcloud wp --path="\$WP_PATH" db query \
  "SELECT object_id, primary_focus_keyword_score, readability_score FROM wp_yoast_indexable WHERE object_id=\$POST_ID AND object_type='post'" \
  --skip-column-names 2>&1

echo "WPCLI_DONE"
REMOTE
chmod +x "${TMP_DIR}/yoast_update_${POST_ID}.sh"

# SCP
cat > "${TMP_DIR}/scp_y${POST_ID}.exp" << 'EOFEXP'
#!/usr/bin/expect -f
set s03 $env(MGS_YOAST_S03_PASSWORD)
set s01 $env(MGS_YOAST_S01_PASSWORD)
set local_script [lindex $argv 0]
set remote_script [lindex $argv 1]
set ssh_opts [lindex $argv 2]
set timeout 30
spawn sh -c "scp $ssh_opts -J zeus@46.4.95.117 \"$local_script\" zeus@162.55.28.178:\"$remote_script\""
expect "46.4.95.117's password:"; send "$s03\r"
expect "162.55.28.178's password:"; send "$s01\r"
expect { "100%" { exp_continue } eof {} }
EOFEXP
chmod +x "${TMP_DIR}/scp_y${POST_ID}.exp"
MGS_YOAST_S03_PASSWORD="$S03_PASS" MGS_YOAST_S01_PASSWORD="$S01_PASS" "${TMP_DIR}/scp_y${POST_ID}.exp" "${TMP_DIR}/yoast_update_${POST_ID}.sh" "$REMOTE_SCRIPT" "$SSH_OPTS" > /dev/null 2>&1

# SSH execute
cat > "${TMP_DIR}/ssh_y${POST_ID}.exp" << 'EOFEXP'
#!/usr/bin/expect -f
set s03 $env(MGS_YOAST_S03_PASSWORD)
set s01 $env(MGS_YOAST_S01_PASSWORD)
set remote_script [lindex $argv 0]
set ssh_opts [lindex $argv 1]
set timeout 90
spawn sh -c "ssh $ssh_opts -J zeus@46.4.95.117 zeus@162.55.28.178"
expect "46.4.95.117's password:"; send "$s03\r"
expect "162.55.28.178's password:"; send "$s01\r"
expect "Made with"
sleep 3
send "bash $remote_script; rm -f $remote_script\n"
sleep 25
send "exit\r"
expect eof
EOFEXP
chmod +x "${TMP_DIR}/ssh_y${POST_ID}.exp"
SSH_OUT=$(MGS_YOAST_S03_PASSWORD="$S03_PASS" MGS_YOAST_S01_PASSWORD="$S01_PASS" "${TMP_DIR}/ssh_y${POST_ID}.exp" "$REMOTE_SCRIPT" "$SSH_OPTS" 2>/dev/null)

# ── Step 3: Verify — parse SSH_OUT for indexable row ───────────────────────────
# Note: _yoast_wpseo_linkdex / content_score are NOT exposed via REST (not in
# register_post_meta in v4 by design). Verification is done via SSH/DB output.
cat > "${TMP_DIR}/parse_idx.py" << 'PYEOF'
import sys, re, os
pid = os.environ.get("PARSE_ID","")
data = sys.stdin.read()
for line in data.replace('\r','').split('\n'):
    l = line.strip()
    m = re.match(r'\|\s*' + re.escape(pid) + r'\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|', l)
    if m:
        print(m.group(1), m.group(2))
        sys.exit(0)
print("? ?")
PYEOF
_IDX=$(echo "$SSH_OUT" | PARSE_ID="$POST_ID" python3 "${TMP_DIR}/parse_idx.py" 2>/dev/null)
IDX_SEO=$(echo  "$_IDX" | awk '{print $1}')
IDX_READ=$(echo "$_IDX" | awk '{print $2}')
WPCLI_OK=$(echo "$SSH_OUT" | grep -c "WPCLI_DONE" || echo "0")

# Cleanup
# Local temp files are removed by the EXIT trap; remote script is removed after execution.

# ── Output ────────────────────────────────────────────────────────────────────
python3 - << PYEOF
import json
print(json.dumps({
    "status":            "ok",
    "post_id":           int("$POST_ID"),
    "seo_score":         int("$SEO_SCORE"),
    "readability_score": int("$READ_SCORE"),
    "indexable_seo":     "$IDX_SEO",
    "indexable_read":    "$IDX_READ",
    "wpcli_ok":          bool(int("$WPCLI_OK")),
}))
PYEOF
