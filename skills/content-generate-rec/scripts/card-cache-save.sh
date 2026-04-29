#!/bin/bash
# card-cache-save.sh — salva ou atualiza dados de cartão no cache
#
# Uso: card-cache-save.sh <json_file>
# 
# JSON file deve conter:
#   {
#     "card_slug": "tesco-bank-clubcard",
#     "card_name": "Tesco Bank Clubcard Credit Card",
#     "card_official_url": "https://...",
#     "country": "gb",
#     "vertical": "cc",
#     "language": "en",
#     "annual_fee": "No annual fee",
#     "apr": "29.9% var.",
#     "benefits": ["Benefit 1", "Benefit 2", ...],
#     "tag10": "Clubcard rewards",
#     "tag2": "No annual fee",
#     "descriptor": "Earn Clubcard points on every purchase. No annual fee.",
#     "competitors": [{"name": "...", "apr": "..."}, {...}],
#     "card_image_local_path": "/root/mgs-agent/data/card-images-cache/tesco-bank-clubcard.jpg",
#     "card_image_url_orig": "https://www.tescobank.com/.../card.png",
#     "card_image_uploaded_id": 62033,
#     "card_image_uploaded_url": "https://eggbev.com/wp-content/uploads/.../card.jpg",
#     "ttl_days": 30,
#     "source": "browser"
#   }
#
# Exit: 0 = saved, 1 = error

set -euo pipefail

CACHE_DB="/root/mgs-agent/data/card-cache.db"
LOG_FILE="/root/mgs-agent/logs/card-cache.log"

if [ $# -lt 1 ]; then
    echo "ERROR: usage: card-cache-save.sh <json_file>" >&2
    exit 1
fi

JSON_FILE="$1"
if [ ! -f "$JSON_FILE" ]; then
    echo "ERROR: file not found: $JSON_FILE" >&2
    exit 1
fi

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

python3 << PYEOF
import json, sqlite3, os, sys
from datetime import datetime, timedelta, timezone

with open("$JSON_FILE") as f:
    data = json.load(f)

required = ['card_slug', 'card_name', 'country', 'vertical']
missing = [k for k in required if not data.get(k)]
if missing:
    print(f"ERROR: missing required fields: {missing}", file=sys.stderr)
    sys.exit(1)

# TTL
ttl_days = int(data.get('ttl_days', 30))
expires_at = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

# JSON serializar arrays
benefits_json = json.dumps(data.get('benefits', []))
competitors_json = json.dumps(data.get('competitors', []))
raw_json = json.dumps(data)

conn = sqlite3.connect("$CACHE_DB")
cur = conn.cursor()

# UPSERT (INSERT or REPLACE)
cur.execute("""
INSERT INTO card_cache (
    card_slug, card_name, card_official_url, country, vertical, language,
    annual_fee, apr, benefits_json, tag10, tag2, descriptor,
    competitors_json, raw_extracted_json,
    card_image_local_path, card_image_url_orig,
    card_image_uploaded_id, card_image_uploaded_url,
    researched_at, ttl_days, expires_at, source
) VALUES (
    ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?,
    ?, ?,
    ?, ?,
    ?, ?,
    ?, ?, ?, ?
)
ON CONFLICT(card_slug) DO UPDATE SET
    card_name = excluded.card_name,
    card_official_url = excluded.card_official_url,
    country = excluded.country,
    vertical = excluded.vertical,
    language = excluded.language,
    annual_fee = excluded.annual_fee,
    apr = excluded.apr,
    benefits_json = excluded.benefits_json,
    tag10 = excluded.tag10,
    tag2 = excluded.tag2,
    descriptor = excluded.descriptor,
    competitors_json = excluded.competitors_json,
    raw_extracted_json = excluded.raw_extracted_json,
    card_image_local_path = excluded.card_image_local_path,
    card_image_url_orig = excluded.card_image_url_orig,
    card_image_uploaded_id = excluded.card_image_uploaded_id,
    card_image_uploaded_url = excluded.card_image_uploaded_url,
    researched_at = excluded.researched_at,
    ttl_days = excluded.ttl_days,
    expires_at = excluded.expires_at,
    source = excluded.source
""", (
    data['card_slug'], data['card_name'], data.get('card_official_url'),
    data['country'], data['vertical'], data.get('language'),
    data.get('annual_fee'), data.get('apr'), benefits_json,
    data.get('tag10'), data.get('tag2'), data.get('descriptor'),
    competitors_json, raw_json,
    data.get('card_image_local_path'), data.get('card_image_url_orig'),
    data.get('card_image_uploaded_id'), data.get('card_image_uploaded_url'),
    "$NOW", ttl_days, expires_at, data.get('source', 'browser')
))

conn.commit()
conn.close()

print(json.dumps({
    "saved": True,
    "card_slug": data['card_slug'],
    "expires_at": expires_at,
    "ttl_days": ttl_days
}, indent=2))
PYEOF

echo "[$NOW] SAVE card_slug=$(jq -r .card_slug $JSON_FILE) source=$(jq -r '.source // "browser"' $JSON_FILE)" >> "$LOG_FILE"
