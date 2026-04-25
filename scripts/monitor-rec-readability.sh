#!/bin/bash
# monitor-rec-readability.sh
# Verifica readability dos RECs gb-cc-en publicados no eggbev.
# Mantém contador de consecutivos verdes rumo ao threshold de 5.
# Reporta via Discord se algum REC sair vermelho ou amarelo.
#
# Uso: bash monitor-rec-readability.sh
# Cron: diário

set -euo pipefail

SITE="eggbev"
STATE_FILE="/root/mgs-agent/data/rec-readability-monitor.json"
SCORER="/root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh"
RESOLVE="/root/mgs-agent/skills/content-publish-wordpress/scripts/resolve-credentials.sh"

set -a && . /root/mgs-agent/.env && set +a

# Resolver credenciais
CREDS=$(bash "$RESOLVE" "$SITE" 2>/dev/null)
WP_URL=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['wp_url'])")
WP_USER=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['username'])")
WP_PASS=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['password'])")

# Carregar estado atual
if [ ! -f "$STATE_FILE" ]; then
    echo '{"consecutive_green": 0, "checked_ids": [], "history": []}' > "$STATE_FILE"
fi

STATE=$(cat "$STATE_FILE")
CONSECUTIVE=$(echo "$STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('consecutive_green',0))")
CHECKED_IDS=$(echo "$STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('checked_ids',[])))")

# Buscar RECs gb-cc-en publicados (tags: rec=219, gb=451, cc=214, lang_en=215)
POSTS=$(curl -s \
  -u "$WP_USER:$WP_PASS" \
  "$WP_URL/wp-json/wp/v2/posts?tags=219,451,214,215&per_page=10&_fields=id,slug,date&status=publish" \
  2>/dev/null)

NEW_CHECKED="$CHECKED_IDS"
NEW_CONSECUTIVE="$CONSECUTIVE"
ALERTS=""
HISTORY_APPEND=""

while IFS= read -r line; do
    POST_ID=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['id'])")
    POST_SLUG=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['slug'])")
    POST_DATE=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['date'][:10])")

    # Pular se já checado
    ALREADY=$(echo "$NEW_CHECKED" | python3 -c "import sys,json; ids=json.load(sys.stdin); print('yes' if $POST_ID in ids else 'no')")
    if [ "$ALREADY" = "yes" ]; then
        continue
    fi

    # Rodar scorer
    SCORE_JSON=$(bash "$SCORER" "$SITE" "$POST_ID" 2>/dev/null || echo '{}')
    READ_SCORE=$(echo "$SCORE_JSON" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('readability_score','null'))" 2>/dev/null || echo "null")
    SEO_SCORE=$(echo "$SCORE_JSON"  | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('seo_score','null'))" 2>/dev/null || echo "null")

    if [ "$READ_SCORE" = "null" ] || [ -z "$READ_SCORE" ]; then
        continue
    fi

    # Classificar
    if   [ "$READ_SCORE" -ge 71 ] 2>/dev/null; then COLOR="green";  EMOJI="🟢"
    elif [ "$READ_SCORE" -ge 41 ] 2>/dev/null; then COLOR="orange"; EMOJI="🟡"
    else                                              COLOR="red";    EMOJI="🔴"
    fi

    # Atualizar consecutivos
    if [ "$COLOR" = "green" ]; then
        NEW_CONSECUTIVE=$((NEW_CONSECUTIVE + 1))
    else
        NEW_CONSECUTIVE=0
        ALERTS="${ALERTS}⚠️ REC com readability não-verde: **${POST_SLUG}** | Read=${READ_SCORE} ${EMOJI} | SEO=${SEO_SCORE} | Data=${POST_DATE}\n"
    fi

    # Adicionar ao histórico
    HISTORY_APPEND="${HISTORY_APPEND}{\"id\":${POST_ID},\"slug\":\"${POST_SLUG}\",\"date\":\"${POST_DATE}\",\"readability\":${READ_SCORE},\"seo\":${SEO_SCORE},\"color\":\"${COLOR}\"},"

    # Marcar como checado
    NEW_CHECKED=$(echo "$NEW_CHECKED" | python3 -c "import sys,json; ids=json.load(sys.stdin); ids.append($POST_ID); print(json.dumps(ids))")

    echo "Checked: $POST_SLUG | Read=$READ_SCORE $EMOJI | SEO=$SEO_SCORE | Consec=$NEW_CONSECUTIVE"
done < <(echo "$POSTS" | python3 -c "
import sys, json
posts = json.load(sys.stdin)
for p in posts:
    print(json.dumps(p))
")

# Salvar novo estado
python3 -c "
import json, sys

with open('$STATE_FILE') as f:
    state = json.load(f)

state['consecutive_green'] = $NEW_CONSECUTIVE
state['checked_ids'] = json.loads('''$NEW_CHECKED''')

# Append history
new_items = '''$HISTORY_APPEND'''.strip().rstrip(',')
if new_items:
    for item in new_items.split('},{'):
        item = item.strip().strip(',')
        if not item.startswith('{'): item = '{' + item
        if not item.endswith('}'): item = item + '}'
        try:
            state.setdefault('history', []).append(json.loads(item))
        except: pass

with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)

print(f'State saved: consecutive_green={state[\"consecutive_green\"]}')
"

# Output final para o cron report
echo ""
echo "CONSECUTIVE_GREEN=$NEW_CONSECUTIVE"
echo "ALERTS=$ALERTS"
if [ -n "$ALERTS" ]; then
    echo "STATUS=ALERT"
else
    echo "STATUS=OK"
fi
