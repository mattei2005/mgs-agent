#!/bin/bash
# card-cache-stats.sh — mostra estatísticas do cache

set -euo pipefail

CACHE_DB="/root/mgs-agent/data/card-cache.db"

echo "═══ Card Cache Stats ═══"
echo ""

echo "Total cards cacheados:"
sqlite3 "$CACHE_DB" "SELECT COUNT(*) FROM card_cache;"

echo ""
echo "Cards por country:"
sqlite3 "$CACHE_DB" -header -column "SELECT country, COUNT(*) AS n FROM card_cache GROUP BY country;"

echo ""
echo "Top 10 cards mais usados:"
sqlite3 "$CACHE_DB" -header -column "
SELECT card_slug, usage_count, last_used_at 
FROM card_cache 
ORDER BY usage_count DESC 
LIMIT 10;
"

echo ""
echo "Hit rate últimos 7 dias:"
sqlite3 "$CACHE_DB" "
SELECT 
    printf('%.1f%%', 100.0 * SUM(hit) / COUNT(*)) AS hit_rate,
    SUM(hit) || ' hits / ' || COUNT(*) || ' requests' AS detail
FROM cache_access_log
WHERE accessed_at > datetime('now', '-7 days');
"

echo ""
echo "Cards expirados (>30 dias):"
sqlite3 "$CACHE_DB" "SELECT COUNT(*) FROM card_cache WHERE expires_at < datetime('now', 'utc');"
