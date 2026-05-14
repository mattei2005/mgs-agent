#!/bin/bash
set -e

# Carregar variáveis de ambiente (incluindo OP_SERVICE_ACCOUNT_TOKEN)
set -a
source "/root/mgs-agent/.env" 2>/dev/null || true
set +a

export RUNCLOUD_TOKEN=$(op item get "RunCloud API - MGS" --vault "MGS Conteúdo" --fields label=runcloud_api_key_token --reveal)

if [[ ${#RUNCLOUD_TOKEN} -lt 50 ]]; then
    echo "ERRO: Falha ao obter token do 1Password"
    exit 1
fi

echo "Token obtido (length: ${#RUNCLOUD_TOKEN})"
echo ""

python3 << 'PYEOF'
import json, os, subprocess, time

TOKEN = os.environ['RUNCLOUD_TOKEN']
BASE_URL = "https://manage.runcloud.io/api/v3"

def api_get(endpoint, params=""):
    url = f"{BASE_URL}{endpoint}{params}"
    result = subprocess.run([
        "curl", "-s",
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Accept: application/json",
        url
    ], capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return {"error": result.stdout[:200]}

servers = [
    ("290075", "MatteiInc01"),
    ("288158", "MatteiInc02"),
    ("310255", "MatteiInc03JBF"),
    ("266820", "SpazioVPS"),
    ("315018", "vpsdimelabella"),
]

inventario = []

for server_id, server_name in servers:
    print(f"\n=== {server_name} ===")
    
    all_webapps = []
    page = 1
    while True:
        data = api_get(f"/servers/{server_id}/webapps", f"?perPage=40&page={page}")
        webapps = data.get('data', [])
        all_webapps.extend(webapps)
        total_pages = data.get('meta', {}).get('lastPage', 1)  # fix Item 10 — campo correto da API RunCloud
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.2)
    
    wp_apps = [w for w in all_webapps if w.get('type') == 'wordpress']
    print(f"Total: {len(all_webapps)} | WordPress: {len(wp_apps)}")
    
    for app in wp_apps:
        domains_data = api_get(f"/servers/{server_id}/webapps/{app['id']}/domains")
        domains = domains_data.get('data', [])
        primary = next((d['name'] for d in domains if d.get('type') == 'primary'), None)
        all_doms = [d['name'] for d in domains]
        
        entry = {
            'server_id': server_id,
            'server_name': server_name,
            'webapp_id': app['id'],
            'webapp_name': app['name'],
            'root_path': app.get('rootPath'),
            'php_version': app.get('phpVersion'),
            'primary_domain': primary,
            'all_domains': all_doms,
        }
        inventario.append(entry)
        
        disp = primary if primary else "(sem dominio)"
        print(f"  {app['name']:<35} -> {disp}")
        time.sleep(0.15)

with open('/root/mgs-agent/inventario-webapps.json', 'w') as f:
    json.dump(inventario, f, indent=2, ensure_ascii=False)

print(f"\nTotal: {len(inventario)} webapps inventariados")
print(f"Arquivo: /root/mgs-agent/inventario-webapps.json")
PYEOF
