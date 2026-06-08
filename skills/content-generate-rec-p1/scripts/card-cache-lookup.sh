#!/bin/bash
# card-cache-lookup.sh — consulta cache de dados de cartão
#
# Uso: card-cache-lookup.sh <card_slug>
# Output JSON:
#   HIT  -> {"hit": true, "card_slug": "...", "card_name": "...", ...todos os campos}
#   MISS -> {"hit": false, "card_slug": "..."}
#
# Exit codes:
#   0 = cache HIT (ainda válido, expires_at > now)
#   1 = cache MISS (não existe ou expirou)

set -euo pipefail

CACHE_DB="/root/mgs-agent/data/card-cache.db"
LOG_FILE="/root/mgs-agent/logs/card-cache.log"
SITE="${SITE:-unknown}"

if [ $# -lt 1 ]; then
    echo '{"error": "usage: card-cache-lookup.sh <card_slug>"}' >&2
    exit 2
fi

CARD_SLUG="$1"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Query cache (só HIT se ainda não expirou)
RESULT=$(sqlite3 "$CACHE_DB" -json "
SELECT 
    card_slug, card_name, card_official_url, country, vertical, language,
    annual_fee, apr, benefits_json, tag10, tag2, descriptor,
    competitors_json, raw_extracted_json,
    card_image_local_path, card_image_url_orig,
    card_image_uploaded_id, card_image_uploaded_url,
    researched_at, last_used_at, usage_count, expires_at
FROM card_cache
WHERE card_slug = '$CARD_SLUG'
  AND (expires_at IS NULL OR expires_at > '$NOW');
" 2>/dev/null || echo "")

if [ -n "$RESULT" ] && [ "$RESULT" != "[]" ]; then
    # HIT: incrementar usage_count + last_used_at + log
    sqlite3 "$CACHE_DB" "
        UPDATE card_cache 
        SET usage_count = usage_count + 1, last_used_at = '$NOW'
        WHERE card_slug = '$CARD_SLUG';
        INSERT INTO cache_access_log (card_slug, accessed_at, hit, site, notes)
        VALUES ('$CARD_SLUG', '$NOW', 1, '$SITE', 'lookup HIT');
    "
    
    echo "[$NOW] HIT card_slug=$CARD_SLUG site=$SITE" >> "$LOG_FILE"
    
    # Retornar JSON com hit=true
    echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data:
    obj = data[0]
    obj['hit'] = True
    print(json.dumps(obj, indent=2))
else:
    print(json.dumps({'hit': False, 'card_slug': '$CARD_SLUG'}))
"
    exit 0
else
    # MISS: log + retorna miss
    sqlite3 "$CACHE_DB" "
        INSERT INTO cache_access_log (card_slug, accessed_at, hit, site, notes)
        VALUES ('$CARD_SLUG', '$NOW', 0, '$SITE', 'lookup MISS');
    " 2>/dev/null || true
    
    echo "[$NOW] MISS card_slug=$CARD_SLUG site=$SITE" >> "$LOG_FILE"
    
    echo "{\"hit\": false, \"card_slug\": \"$CARD_SLUG\"}"
    exit 1
fi
