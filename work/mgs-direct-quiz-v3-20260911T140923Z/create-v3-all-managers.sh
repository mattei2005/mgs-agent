#!/usr/bin/env bash
set -Eeuo pipefail
SITE=${1:-}
case "$SITE" in vizioid|yolokfx) ;; *) printf 'invalid site\n' >&2; exit 2;; esac
OWNER=runcloud
WP="/home/runcloud/webapps/$SITE"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/home/runcloud/backups/${SITE}-mgs-direct-quiz-v3-all-managers-${STAMP}"
MUTATED=0

rollback() {
  set +e
  if [[ "$MUTATED" == 1 ]]; then
    sudo mkdir -p "$BACKUP/failed-state"
    if sudo test -d "$WP/quiz"; then sudo mv "$WP/quiz" "$BACKUP/failed-state/quiz-after-failure"; fi
    if sudo test -d "$BACKUP/quiz-before"; then sudo cp -a "$BACKUP/quiz-before" "$WP/quiz"; fi
    sudo chown -R "$OWNER:$OWNER" "$WP/quiz" 2>/dev/null || true
    sudo -u "$OWNER" env MGS_DQ_BACKUP_JSON="$BACKUP/landings-before.json" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);if(!is_array($items)){throw new Exception("invalid_backup_json");}update_option("mgs_direct_quiz_landings",$items,false);update_option("mgs_direct_quiz_static_version","1.2.0",false);' --allow-root >/dev/null 2>&1 || true
  fi
  printf 'ROLLBACK_PATH=%s\n' "$BACKUP" >&2
}
on_error() { rc=$?; trap - ERR; rollback; exit "$rc"; }
trap on_error ERR

home=$(sudo -u "$OWNER" wp --path="$WP" option get home --allow-root)
[[ "$home" == "https://$SITE.com" ]]
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
[[ "$version" == '1.2.0' && "$status" == 'active' ]]

sudo mkdir -p "$BACKUP"
sudo cp -a "$WP/quiz" "$BACKUP/quiz-before"
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-before.json" >/dev/null
sudo chmod 600 "$BACKUP/landings-before.json"
sudo test -s "$BACKUP/landings-before.json"
for manager in g001 g003 g004 g005 g006; do
  sudo test ! -e "$WP/quiz/us/sh3-$manager"
done
MUTATED=1

create_json=$(sudo -u "$OWNER" wp --path="$WP" eval '
$targets=array("G001","G002","G003","G004","G005","G006");
$items=MGS_Direct_Quiz::items();$base=null;$existing_v3=array();
foreach($items as $item){if(($item["country"]??"")==="us"&&($item["layout_template"]??"")==="lp3"){$m=(string)($item["manager_code"]??"");$existing_v3[$m]=$item;if($m==="G002"&&($item["slug"]??"")==="sh3-g002"&&!empty($item["active"])){$base=$item;}}}
if(!$base){throw new Exception("active_g002_v3_base_missing");}
if(array_keys($existing_v3)!==array("G002")){throw new Exception("unexpected_existing_v3_".wp_json_encode(array_keys($existing_v3)));}
$now=current_time("mysql",true);$created=array();
foreach($targets as $manager){
 if($manager==="G002")continue;
 $copy=$base;$copy["id"]=wp_generate_uuid4();$copy["name"]="SHEIN US — ".$manager." — V3";$copy["manager_code"]=$manager;$copy["slug"]="sh3-".strtolower($manager);$copy["active"]=1;$copy["created_at"]=$now;$copy["updated_at"]=$now;
 $items[]=$copy;$created[]=array("id"=>$copy["id"],"manager"=>$manager,"slug"=>$copy["slug"]);
}
if(!MGS_Direct_Quiz::save_items($items)){throw new Exception("option_save_failed");}
$sync=MGS_Direct_Quiz::sync_static_pages();if(is_wp_error($sync)){throw new Exception($sync->get_error_message());}
$readback=MGS_Direct_Quiz::items();$found=array();foreach($readback as $item){if(($item["layout_template"]??"")==="lp3"&&in_array($item["manager_code"]??"",$targets,true)){$found[$item["manager_code"]]=$item;}}
ksort($found);if(array_keys($found)!==$targets){throw new Exception("v3_manager_readback_failed_".wp_json_encode(array_keys($found)));}
foreach($found as $manager=>$item){$slug="sh3-".strtolower($manager);if(($item["slug"]??"")!==$slug||empty($item["active"])||($item["destination_a_url"]??"")!==$base["destination_a_url"]){throw new Exception("v3_item_invalid_".$manager);}}
echo wp_json_encode(array("created"=>$created,"item_count"=>count($readback),"active_sync_count"=>count($sync),"destination"=>$base["destination_a_url"]),JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root)

sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-after.json" >/dev/null
sudo chmod 600 "$BACKUP/landings-after.json"
sudo python3 - "$BACKUP/landings-before.json" "$BACKUP/landings-after.json" <<'PY'
import json,sys
before=json.load(open(sys.argv[1])); after=json.load(open(sys.argv[2]))
b={str(x['id']):x for x in before}; a={str(x['id']):x for x in after}
assert set(b)<=set(a) and all(a[k]==v for k,v in b.items()), 'existing_item_drift'
new=[x for k,x in a.items() if k not in b]
assert len(new)==5, len(new)
assert sorted(x['manager_code'] for x in new)==['G001','G003','G004','G005','G006']
assert all(x['layout_template']=='lp3' and x['active']==1 and x['slug']=='sh3-'+x['manager_code'].lower() for x in new)
print(json.dumps({'old_items_preserved':len(b),'new_items':len(new),'current_items':len(a),'new_ids':{x['manager_code']:x['id'] for x in new}},sort_keys=True,separators=(',',':')))
PY

sudo python3 - "$WP" "$SITE" <<'PY'
import hashlib,json,os,sys
wp,site=sys.argv[1:]
results=[]
for manager in range(1,7):
    slug=f'sh3-g{manager:03d}'
    path=os.path.join(wp,'quiz','us',slug,'index.html')
    assert os.path.isfile(path), path
    html=open(path,encoding='utf-8').read()
    assert 'MGS Direct Quiz static; plugin=1.2.0' in html
    assert html.count('data-mgs-dq-cta')==7
    assert html.count('class="mgs-dq-category"')==6
    assert '<form' not in html.lower() and '<input' not in html.lower()
    assert f'https://{site}.com/rec-us-app-shein-circle-of-style/' in html
    assert 'src="http://' not in html and 'href="http://' not in html
    results.append({'slug':slug,'sha256':hashlib.sha256(html.encode()).hexdigest()})
print(json.dumps(results,separators=(',',':')))
PY

sudo test -d "$BACKUP/quiz-before"
sudo test -s "$BACKUP/landings-before.json"
sudo test -s "$BACKUP/landings-after.json"
MUTATED=0
printf 'SITE=%s\nVERSION=%s\nSTATUS=%s\nBACKUP=%s\nCREATE=%s\n' "$SITE" "$version" "$status" "$BACKUP" "$create_json"
