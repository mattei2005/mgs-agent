#!/usr/bin/env bash
set -euo pipefail

TARGETS_CSV=${1:-}
TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_ROOT="/var/backups/mgs-chat-funnels-offer-copy/$TS"
mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"

sites=(
  '/home/runcloud/webapps/eggbev|eggbev.com|runcloud'
  '/home/runcloud/webapps/newsoun|newsoun.com|runcloud'
  '/home/runcloud/webapps/topfeedfinance|finance.topfeed.fun|runcloud'
  '/home/runcloud2/webapps/wantabrand|wantabrand.com|runcloud2'
  '/home/runcloud/webapps/zuout|zuout.com|runcloud'
  '/home/runcloud/webapps/zytiva|zytiva.com|runcloud'
)

selected() {
  local domain=$1
  [[ -z "$TARGETS_CSV" || ",$TARGETS_CSV," == *",$domain,"* ]]
}

for entry in "${sites[@]}"; do
  IFS='|' read -r path domain user <<< "$entry"
  selected "$domain" || continue
  plugin="$path/wp-content/plugins/mgs-chat-funnels"
  legacy="$plugin/configs/car-br-01.json"
  sms="$plugin/configs/car-br-01-sms.json"
  site_backup="$BACKUP_ROOT/$domain"
  mkdir -p "$site_backup"
  chmod 700 "$site_backup"

  echo "BEGIN|$domain"
  sudo -u "$user" wp --path="$path" plugin is-active mgs-chat-funnels --allow-root
  test -f "$legacy" -a -f "$sms"
  cp "$legacy" "$site_backup/car-br-01.json"
  cp "$sms" "$site_backup/car-br-01-sms.json"
  chmod 600 "$site_backup"/*.json

  if ! sudo python3 - "$legacy" "$sms" "$domain" <<'PY'
import copy,json,os,sys,tempfile
from urllib.parse import urlparse
legacy_path,sms_path,domain=sys.argv[1:4]
paths=[legacy_path,sms_path]
expected_ids=['CAR-BR-01','CAR-BR-01-SMS']
expected_routes=['/chat/car/br1','/chat-sms/car/br1']
desired_names=['🚗 Financiar sem entrada','💰 Ver ofertas disponíveis','🚘 Financiamento com parcela baixa']

def validate(c,idx):
    if c.get('id')!=expected_ids[idx] or c.get('route')!=expected_routes[idx] or c.get('mode')!='cards':
        raise SystemExit(f'{domain}: unexpected identity/route/mode for {expected_ids[idx]}')
    offers=c.get('offers')
    if not isinstance(offers,list) or len(offers)!=3:
        raise SystemExit(f'{domain}: {expected_ids[idx]} does not have exactly three offers')
    for offer in offers:
        target=offer.get('target') or offer.get('url') or ''
        if (urlparse(target).hostname or '').lower()!=domain.lower():
            raise SystemExit(f'{domain}: cross-domain or missing target blocked')

before=[]; after=[]
for idx,path in enumerate(paths):
    with open(path,encoding='utf-8') as f: c=json.load(f)
    validate(c,idx)
    before.append(copy.deepcopy(c))
    for offer,name in zip(c['offers'],desired_names): offer['name']=name
    c['offers'][2]['subtitle']='Consulte se essa condição está disponível para você,'
    validate(c,idx)
    after.append(c)

allowed={(f'offers.{i}.name') for i in range(3)}|{'offers.2.subtitle'}
def diff(a,b,p=''):
    out=[]
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)): out.extend(diff(a.get(k),b.get(k),f'{p}.{k}'.strip('.')))
    elif isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b): out.append(p+'.length')
        for i,(x,y) in enumerate(zip(a,b)): out.extend(diff(x,y,f'{p}.{i}'.strip('.')))
    elif a!=b: out.append(p)
    return out
for a,b in zip(before,after):
    changed=set(diff(a,b))
    if not changed.issubset(allowed): raise SystemExit(f'{domain}: unexpected changed paths {sorted(changed)}')

for path,obj in zip(paths,after):
    directory=os.path.dirname(path)
    fd,tmp=tempfile.mkstemp(prefix='.zeus-offer-copy-',suffix='.json',dir=directory,text=True)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    json.load(open(tmp,encoding='utf-8'))
    os.replace(tmp,path)
print(f'UPDATED|{domain}|configs=2|fields=4_each')
PY
  then
    cp "$site_backup/car-br-01.json" "$legacy"
    cp "$site_backup/car-br-01-sms.json" "$sms"
    chown "$user:$user" "$legacy" "$sms"
    echo "ROLLBACK|$domain|reason=mutation_failed"
    exit 1
  fi

  chown "$user:$user" "$legacy" "$sms"
  sudo -u "$user" php -r 'foreach(array_slice($argv,1) as $p){json_decode(file_get_contents($p),true,512,JSON_THROW_ON_ERROR);} echo "json_ok\n";' "$legacy" "$sms"
  sudo -u "$user" wp --path="$path" cache flush --allow-root >/dev/null 2>&1 || true
  sudo python3 - "$legacy" "$sms" "$domain" <<'PY'
import json,sys
from urllib.parse import urlparse
expected=['🚗 Financiar sem entrada','💰 Ver ofertas disponíveis','🚘 Financiamento com parcela baixa']
for path,kind in zip(sys.argv[1:3],('legacy','sms')):
 c=json.load(open(path)); names=[x.get('name') for x in c['offers']]
 if names!=expected or c['offers'][2].get('subtitle')!='Consulte se essa condição está disponível para você,': raise SystemExit(kind+' copy readback failed')
 if any((urlparse(x.get('target') or x.get('url') or '').hostname or '').lower()!=sys.argv[3] for x in c['offers']): raise SystemExit(kind+' target drift')
print('READBACK|legacy=ok|sms=ok|targets=preserved')
PY
  echo "COMPLETE|$domain|backup=$site_backup"
done

echo "BACKUP_ROOT|$BACKUP_ROOT"
