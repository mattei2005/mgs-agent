#!/usr/bin/env bash
set -euo pipefail

# Deterministic MGS probe for Brave Search API via 1Password.
# Does not print the API key. Prints only key length and result URLs.

cd /root/mgs-agent
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

VAULT="${OP_DEFAULT_VAULT:-MGS Conteúdo}"
ITEM="${BRAVE_OP_ITEM:-Brave Search API - MGS}"
FIELD="${BRAVE_OP_FIELD:-api key}"
QUERY="${1:-AIB Visa Gold credit card UK official}"
COUNT="${BRAVE_COUNT:-5}"
COUNTRY="${BRAVE_COUNTRY:-GB}"
LANG="${BRAVE_LANG:-en}"

KEY="$(op item get "$ITEM" --vault "$VAULT" --fields "$FIELD" --reveal)"
if [ -z "$KEY" ]; then
  echo "ERROR: Brave key is empty" >&2
  exit 1
fi

echo "OK 1Password: item=$ITEM vault=$VAULT field=$FIELD len=${#KEY}"

python3 - "$KEY" "$QUERY" "$COUNT" "$COUNTRY" "$LANG" <<'PY'
import json
import sys
import urllib.parse
import urllib.request
import urllib.error

key, query, count, country, lang = sys.argv[1:6]
params = urllib.parse.urlencode({
    "q": query,
    "count": int(count),
    "country": country,
    "search_lang": lang,
})
url = "https://api.search.brave.com/res/v1/web/search?" + params
req = urllib.request.Request(
    url,
    headers={
        "Accept": "application/json",
        "X-Subscription-Token": key,
        "User-Agent": "Hermes-Agent MGS Brave probe",
    },
)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", "ignore")[:500]
    print(f"ERROR Brave: HTTP {exc.code} {body}")
    raise SystemExit(1)

results = data.get("web", {}).get("results", [])
print(f"OK Brave web: query={query!r} results={len(results)}")
for i, item in enumerate(results[: int(count)], 1):
    title = (item.get("title") or "")[:90]
    print(f"{i}. {title} | {item.get('url', '')}")
PY
