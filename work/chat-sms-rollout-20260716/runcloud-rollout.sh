#!/usr/bin/env bash
set -euo pipefail

ARTIFACT=/tmp/mgs-chat-funnels-0.4.1-code-only.tar.gz
SMOKE=/tmp/mgs-chat-sms-smoke.php
TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_ROOT="/var/backups/mgs-chat-funnels/$TS"
MANAGERS="/tmp/mgs-cf-sms-managers-$TS.json"
mkdir -p "$BACKUP_ROOT"
chmod 700 "$BACKUP_ROOT"

test -s "$ARTIFACT"
tar -tzf "$ARTIFACT" >/dev/null
php -l "$SMOKE" >/dev/null
chmod 644 "$SMOKE"

# Private SMS catalog source: the validated Eggbev canary. Never print its values.
sudo -u runcloud wp --path=/home/runcloud/webapps/eggbev option get mgs_cf_sms_managers --format=json --allow-root > "$MANAGERS"
chmod 600 "$MANAGERS"
python3 - "$MANAGERS" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
expected={f'G{i:03d}' for i in range(1,7)}
if set(x) != expected or any(not isinstance(x[k],dict) or not x[k].get('url') for k in expected):
    raise SystemExit('private SMS catalog is incomplete')
print('sms_catalog_ok=6')
PY

sites=(
  '/home/runcloud/webapps/eggbev|eggbev.com|runcloud'
  '/home/runcloud/webapps/newsoun|newsoun.com|runcloud'
  '/home/runcloud/webapps/topfeedfinance|finance.topfeed.fun|runcloud'
  '/home/runcloud2/webapps/wantabrand|wantabrand.com|runcloud2'
  '/home/runcloud/webapps/zuout|zuout.com|runcloud'
  '/home/runcloud/webapps/zytiva|zytiva.com|runcloud'
)

for entry in "${sites[@]}"; do
  IFS='|' read -r path domain user <<< "$entry"
  plugin="$path/wp-content/plugins/mgs-chat-funnels"
  site_backup="$BACKUP_ROOT/$domain"
  mkdir -p "$site_backup/configs"
  chmod 700 "$site_backup" "$site_backup/configs"

  echo "BEGIN|$domain"
  sudo -u "$user" wp --path="$path" plugin is-active mgs-chat-funnels --allow-root
  before_version=$(sudo -u "$user" wp --path="$path" plugin get mgs-chat-funnels --field=version --allow-root)
  echo "BEFORE_VERSION|$domain|$before_version"

  tar -czf "$site_backup/plugin.tar.gz" -C "$path/wp-content/plugins" mgs-chat-funnels
  tar -tzf "$site_backup/plugin.tar.gz" >/dev/null
  sudo -u "$user" wp --path="$path" db export - --allow-root --quiet 2>"$site_backup/db-export.stderr" | gzip -c > "$site_backup/database.sql.gz"
  gzip -t "$site_backup/database.sql.gz"
  test -s "$site_backup/database.sql.gz"
  cp "$plugin/configs/car-br-01.json" "$site_backup/configs/car-br-01.json"
  if test -f "$plugin/configs/car-br-01-sms.json"; then
    cp "$plugin/configs/car-br-01-sms.json" "$site_backup/configs/car-br-01-sms.json"
  fi

  # Code-only overlay: configs are deliberately excluded and preserved.
  tar -xzf "$ARTIFACT" -C "$plugin"
  chown -R "$user:$user" "$plugin"
  sudo -u "$user" php -l "$plugin/mgs-chat-funnels.php" >/dev/null
  sudo -u "$user" php -l "$plugin/includes/class-mgs-chat-sms.php" >/dev/null

  # Update only the CAR-BR three-card copy; preserve every target and site/provider setting.
  # Create the SMS variant only when it does not already exist. Eggbev's validated canary remains untouched.
  python3 - "$plugin/configs/car-br-01.json" "$plugin/configs/car-br-01-sms.json" "$domain" <<'PY'
import copy,json,os,sys,tempfile,urllib.parse
legacy_path,sms_path,domain=sys.argv[1:4]
with open(legacy_path,encoding='utf-8') as f:
    c=json.load(f)
if c.get('id')!='CAR-BR-01' or c.get('route')!='/chat/car/br1' or c.get('mode')!='cards':
    raise SystemExit('unexpected CAR legacy identity/mode')
offers=c.get('offers')
if not isinstance(offers,list) or len(offers)!=3:
    raise SystemExit('legacy CAR config does not have exactly three offers')
targets=[]
for item in offers:
    target=item.get('target') or item.get('url')
    if not target:
        raise SystemExit('offer target missing')
    host=urllib.parse.urlparse(target).hostname or ''
    if host.lower()!=domain.lower():
        raise SystemExit(f'cross-domain target blocked: {host} != {domain}')
    targets.append(target)
new_offer_data=[
 ('🚗 Financie sem entrada','Valores com parcelas','R$157,00 a R$299,00'),
 ('💳 Ver ofertas disponíveis','Bancos com taxas reduzidas','e facilidade para baixo score.'),
 ('🔥 Juros reduzidos 0.98% e sem entrada','Consulte se essa condição está disponível para você.','Oferta por tempo LIMITADO !'),
]
new=[]
for target,(name,subtitle,bank) in zip(targets,new_offer_data):
    new.append({'name':name,'subtitle':subtitle,'bank':bank,'image':'','logo':'','target':target})
c['offers']=new
chat=c.setdefault('chat',{})
chat['pre_offer_messages']=['🔍 Estou pesquisando as melhores condições para você...']
chat['offer_headline']='🚗 Encontrei 3 opções que podem combinar com o seu perfil. | Toque na que mais faz sentido para você:'
def atomic_json(path,obj):
    d=os.path.dirname(path)
    fd,tmp=tempfile.mkstemp(prefix='.zeus-',suffix='.json',dir=d,text=True)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(obj,f,ensure_ascii=False,indent=2)
            f.write('\n')
            f.flush(); os.fsync(f.fileno())
        json.load(open(tmp,encoding='utf-8'))
        os.replace(tmp,path)
    finally:
        # On failure, leave the temporary file for forensic recovery; do not delete it automatically.
        pass
atomic_json(legacy_path,c)
created=False
if not os.path.exists(sms_path):
    sms=copy.deepcopy(c)
    sms['id']='CAR-BR-01-SMS'
    sms['route']='/chat-sms/car/br1'
    sms['title']='chat sms cards financiamento de carros'
    sms['sms_enabled']=True
    sms['sms_manager_code']='G006'
    sms['sms_name_label']='Nome'
    sms['sms_phone_label']='Telefone'
    sms['sms_submit_label']='TRANSFERIR PARA ESPECIALISTA →'
    atomic_json(sms_path,sms)
    created=True
print('CONFIG_MUTATION|legacy_updated|sms_created='+str(created).lower())
PY
  chown "$user:$user" "$plugin/configs/car-br-01.json" "$plugin/configs/car-br-01-sms.json"

  if [ "$domain" != "eggbev.com" ]; then
    sudo -u "$user" wp --path="$path" eval '
      $raw=stream_get_contents(STDIN);
      $data=json_decode($raw,true);
      if(!is_array($data)){throw new Exception("invalid private SMS catalog");}
      foreach(array("G001","G002","G003","G004","G005","G006") as $code){
        if(empty($data[$code]["url"]) || !MGS_Chat_SMS::is_valid_sms_url($data[$code]["url"])){throw new Exception("invalid manager ".$code);}
      }
      update_option(MGS_Chat_SMS::SMS_OPTION,$data,false);
      if(get_option(MGS_Chat_SMS::SMS_OPTION)!==$data){throw new Exception("SMS option readback failed");}
      MGS_Chat_SMS::maybe_upgrade();
      echo "sms_option_readback_ok\n";
    ' --allow-root < "$MANAGERS"
  else
    sudo -u "$user" wp --path="$path" eval 'MGS_Chat_SMS::maybe_upgrade(); echo "sms_schema_checked\n";' --allow-root
  fi

  sudo -u "$user" wp --path="$path" cache flush --allow-root >/dev/null || true
  after_version=$(sudo -u "$user" wp --path="$path" plugin get mgs-chat-funnels --field=version --allow-root)
  test "$after_version" = "0.4.1"
  table=$(sudo -u "$user" wp --path="$path" db prefix --allow-root)mgs_chat_leads
  table_readback=$(sudo -u "$user" wp --path="$path" db query "SHOW TABLES LIKE '$table';" --skip-column-names --allow-root)
  test "$table_readback" = "$table"

  sudo -u "$user" wp --path="$path" eval-file "$SMOKE" --allow-root | sed "s/^/SMOKE|$domain|/"
  python3 - "$plugin/configs/car-br-01.json" "$plugin/configs/car-br-01-sms.json" "$domain" <<'PY'
import json,sys,urllib.parse
legacy=json.load(open(sys.argv[1])); sms=json.load(open(sys.argv[2])); domain=sys.argv[3]
expected=['🚗 Financie sem entrada','💳 Ver ofertas disponíveis','🔥 Juros reduzidos 0.98% e sem entrada']
for c,kind in ((legacy,'legacy'),(sms,'sms')):
    names=[x.get('name') for x in c.get('offers',[])]
    hosts=[urllib.parse.urlparse(x.get('target') or x.get('url') or '').hostname for x in c.get('offers',[])]
    if names!=expected or hosts!=[domain,domain,domain]: raise SystemExit(kind+' readback failed')
if legacy.get('sms_enabled'): raise SystemExit('legacy unexpectedly SMS-enabled')
if not sms.get('sms_enabled') or sms.get('sms_manager_code')!='G006' or sms.get('route')!='/chat-sms/car/br1': raise SystemExit('SMS readback failed')
print('READBACK|legacy=ok|sms=ok|targets=own-domain')
PY
  echo "COMPLETE|$domain|0.4.1|backup=$site_backup"
done

echo "BACKUP_ROOT|$BACKUP_ROOT"
