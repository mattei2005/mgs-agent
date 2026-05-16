#!/usr/bin/env bash
# runcloud-inventory.sh — inventário read-only de webapps RunCloud via API v3
#
# Uso:
#   scripts/runcloud-inventory.sh             # atualiza /root/mgs-agent/inventario-webapps.json
#   scripts/runcloud-inventory.sh --dry-run   # consulta API e não grava arquivo
#   scripts/runcloud-inventory.sh --json      # imprime JSON no stdout e não grava arquivo
#
# Segurança:
# - Token RunCloud vem do 1Password em runtime.
# - Token nunca é impresso; logs mostram apenas status/contagens.
# - Escrita é atômica via mktemp + mv.

set -euo pipefail

BASE_DIR="/root/mgs-agent"
OUT_FILE="${BASE_DIR}/inventario-webapps.json"
MODE="write"

case "${1:-}" in
  "") ;;
  --dry-run) MODE="dry-run" ;;
  --json) MODE="json" ;;
  -h|--help)
    sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "ERROR: argumento desconhecido: $1" >&2
    echo "Usage: $0 [--dry-run|--json]" >&2
    exit 2
    ;;
esac

# Carregar variáveis de ambiente (incluindo OP_SERVICE_ACCOUNT_TOKEN)
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

TOKEN="$(op item get "RunCloud API - MGS" \
  --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" \
  --fields label=runcloud_api_key_token \
  --reveal 2>/dev/null || true)"

if [[ ${#TOKEN} -lt 50 ]]; then
  echo "ERROR: falha ao obter token RunCloud no 1Password" >&2
  exit 1
fi

TMP_OUT="$(mktemp "/tmp/runcloud-inventory.XXXXXX")"
cleanup() { rm -f "$TMP_OUT"; }
trap cleanup EXIT

RUNCLOUD_TOKEN="$TOKEN" python3 - "$MODE" "$TMP_OUT" <<'PYEOF'
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

MODE = sys.argv[1]
TMP_OUT = sys.argv[2]
TOKEN = os.environ.get("RUNCLOUD_TOKEN", "")
BASE_URL = "https://manage.runcloud.io/api/v3"

SERVERS = [
    ("290075", "MatteiInc01"),
    ("288158", "MatteiInc02"),
    ("310255", "MatteiInc03JBF"),
    ("266820", "SpazioVPS"),
    ("315018", "vpsdimelabella"),
]


def api_get(endpoint, params=None):
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = f"{BASE_URL}{endpoint}{query}"
    last_error = None
    for attempt in range(1, 5):
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Accept": "application/json",
                "User-Agent": "mgs-agent-runcloud-inventory/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            last_error = f"RunCloud API HTTP {exc.code} on {endpoint}: {body}"
            if exc.code in (403, 429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(2 * attempt)
                continue
            raise RuntimeError(last_error) from exc
        except Exception as exc:
            last_error = f"RunCloud API request failed on {endpoint}: {exc}"
            if attempt < 4:
                time.sleep(2 * attempt)
                continue
            raise RuntimeError(last_error) from exc
    raise RuntimeError(last_error or f"RunCloud API request failed on {endpoint}")


inventory = []
summary = []

for server_id, server_name in SERVERS:
    all_webapps = []
    page = 1
    while True:
        data = api_get(f"/servers/{server_id}/webapps", {"perPage": 40, "page": page})
        webapps = data.get("data", [])
        if not isinstance(webapps, list):
            raise RuntimeError(f"Unexpected webapps payload for server {server_name}: data is not list")
        all_webapps.extend(webapps)
        meta = data.get("meta", {})
        pagination = meta.get("pagination", {}) if isinstance(meta, dict) else {}
        total_pages = int(
            pagination.get("total_pages")
            or meta.get("lastPage", 1)
            or 1
        )
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.15)

    wp_apps = [w for w in all_webapps if w.get("type") == "wordpress"]
    summary.append((server_name, len(all_webapps), len(wp_apps)))

    for app in wp_apps:
        app_id = app.get("id")
        domains_data = api_get(f"/servers/{server_id}/webapps/{app_id}/domains")
        domains = domains_data.get("data", [])
        if not isinstance(domains, list):
            domains = []
        primary = next((d.get("name") for d in domains if d.get("type") == "primary"), None)
        all_domains = [d.get("name") for d in domains if d.get("name")]

        inventory.append({
            "server_id": server_id,
            "server_name": server_name,
            "webapp_id": app_id,
            "webapp_name": app.get("name"),
            "root_path": app.get("rootPath"),
            "php_version": app.get("phpVersion"),
            "primary_domain": primary,
            "all_domains": all_domains,
        })
        time.sleep(0.05)

inventory.sort(key=lambda x: (x.get("server_name") or "", x.get("webapp_name") or ""))

with open(TMP_OUT, "w", encoding="utf-8") as f:
    json.dump(inventory, f, indent=2, ensure_ascii=False)
    f.write("\n")

if MODE == "json":
    print(json.dumps(inventory, indent=2, ensure_ascii=False))
else:
    for server_name, total, wp_total in summary:
        print(f"{server_name}: total={total} wordpress={wp_total}")
    print(f"Total WordPress webapps: {len(inventory)}")
    if MODE == "dry-run":
        print("DRY-RUN: arquivo não alterado")
PYEOF

if [[ "$MODE" == "write" ]]; then
  mv "$TMP_OUT" "$OUT_FILE"
  trap - EXIT
  echo "Arquivo atualizado: $OUT_FILE"
else
  rm -f "$TMP_OUT"
  trap - EXIT
fi
