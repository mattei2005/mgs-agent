#!/bin/bash
# monitor-rec-readability.sh
# Verifica readability dos RECs gb-cc-en publicados no eggbev APÓS o adendo (2026-04-25).
# Mantém contador de consecutivos verdes rumo ao threshold de 5.
# Output: JSON para o cron report processar.

set -euo pipefail

SITE="eggbev"
STATE_FILE="/root/mgs-agent/data/rec-readability-monitor.json"
SCORER="/root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh"
RESOLVE="/root/mgs-agent/skills/content-publish-wordpress/scripts/resolve-credentials.sh"
ADENDO_DATE="2026-04-25"

set -a && . /root/mgs-agent/.env && set +a

CREDS=$(bash "$RESOLVE" "$SITE" 2>/dev/null)
WP_URL=$(echo  "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['wp_url'])")
WP_USER=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['username'])")
WP_PASS=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['password'])")

# Carregar estado
STATE=$(cat "$STATE_FILE")
# Variáveis mantidas para compatibilidade do heredoc Python legado abaixo.
# shellcheck disable=SC2034
CONSECUTIVE=$(echo "$STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('consecutive_green',0))")
# shellcheck disable=SC2034
THRESHOLD=$(echo  "$STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('threshold',5))")

# Buscar RECs gb-cc-en publicados (tags: rec=219, gb=451, cc=214, lang_en=215)
# Filtrar apenas posts >= ADENDO_DATE
POSTS=$(curl -s \
  -u "$WP_USER:$WP_PASS" \
  "$WP_URL/wp-json/wp/v2/posts?tags=219,451,214,215&per_page=20&_fields=id,slug,date&status=publish&after=${ADENDO_DATE}T00:00:00" \
  2>/dev/null)

# Processar posts via Python (mais robusto que bash puro)
python3 - <<PYEOF
import json, subprocess, sys

STATE_FILE = "$STATE_FILE"
SCORER     = "$SCORER"
SITE       = "$SITE"

with open(STATE_FILE) as f:
    state = json.load(f)

consecutive  = state.get("consecutive_green", 0)
checked_ids  = set(state.get("checked_ids", []))
history      = state.get("history", [])
threshold    = state.get("threshold", 5)

posts = json.loads('''$POSTS''')

alerts    = []
new_posts = []

for post in posts:
    pid   = post["id"]
    slug  = post["slug"]
    date  = post["date"][:10]

    if pid in checked_ids:
        continue

    # Scorer
    try:
        result = subprocess.run(
            ["bash", SCORER, SITE, str(pid)],
            capture_output=True, text=True, timeout=60
        )
        score_data = json.loads(result.stdout.strip())
        read_score = score_data.get("readability_score")
        seo_score  = score_data.get("seo_score")
    except Exception as e:
        print(f"SCORER ERROR {slug}: {e}", file=sys.stderr)
        continue

    if read_score is None:
        continue

    # Classificar
    if   read_score >= 71: color, emoji = "green",  "🟢"
    elif read_score >= 41: color, emoji = "orange", "🟡"
    else:                  color, emoji = "red",    "🔴"

    if color == "green":
        consecutive += 1
    else:
        consecutive = 0
        alerts.append({
            "slug": slug, "id": pid, "date": date,
            "readability": read_score, "seo": seo_score,
            "emoji": emoji, "color": color
        })

    entry = {
        "id": pid, "slug": slug, "date": date,
        "readability": read_score, "seo": seo_score,
        "color": color,
        "note": f"REC #{len(history)+1} pós-adendo (canário)"
    }
    history.append(entry)
    checked_ids.add(pid)
    new_posts.append(entry)
    print(f"Checked: {slug} | Read={read_score} {emoji} | SEO={seo_score} | Consec={consecutive}")

# Salvar estado
state["consecutive_green"] = consecutive
state["checked_ids"]       = list(checked_ids)
state["history"]           = history

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)

# Output para o cron
print(f"\n--- SUMMARY ---")
print(f"CONSECUTIVE_GREEN={consecutive}/{threshold}")
print(f"NEW_POSTS={len(new_posts)}")

if consecutive >= threshold:
    print("STATUS=THRESHOLD_REACHED")
    print(f"ACTION_REQUIRED: 5 RECs consecutivos verdes atingidos. Autorizado replicar adendo para próximo template de idioma.")
elif alerts:
    print("STATUS=ALERT")
    for a in alerts:
        print(f"ALERT: {a['slug']} | Read={a['readability']} {a['emoji']} | SEO={a['seo']}")
else:
    print("STATUS=OK")
    if new_posts:
        print(f"All {len(new_posts)} new RECs passed readability check.")
    else:
        print("No new RECs to check today.")
PYEOF
