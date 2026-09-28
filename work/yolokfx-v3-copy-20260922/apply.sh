#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/home/runcloud/backups/yolokfx-v3-title-electronics-${STAMP}"
MUTATED=0
rollback() {
  set +e
  if [[ "$MUTATED" == 1 ]]; then
    sudo mkdir -p "$BACKUP/failed-state"
    if sudo test -d "$WP/quiz"; then sudo mv "$WP/quiz" "$BACKUP/failed-state/quiz-after-failure"; fi
    if sudo test -d "$BACKUP/quiz-before"; then sudo cp -a "$BACKUP/quiz-before" "$WP/quiz"; fi
    sudo chown -R "$OWNER:$OWNER" "$WP/quiz" 2>/dev/null || true
    sudo chown "$OWNER:$OWNER" "$BACKUP/landings-before.json" 2>/dev/null || true
    sudo -u "$OWNER" env MGS_DQ_BACKUP_JSON="$BACKUP/landings-before.json" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);if(!is_array($items)){throw new Exception("invalid_backup_json");}update_option("mgs_direct_quiz_landings",$items,false);$rb=get_option("mgs_direct_quiz_landings",[]);if(wp_json_encode($rb)!==wp_json_encode($items)){throw new Exception("rollback_option_readback_failed");}echo "ROLLBACK_OPTION_OK";' --allow-root >&2 || true
  fi
  printf 'ROLLBACK_PATH=%s\n' "$BACKUP" >&2
}
on_error() { rc=$?; trap - ERR; rollback; exit "$rc"; }
trap on_error ERR

home=$(sudo -u "$OWNER" wp --path="$WP" option get home --allow-root)
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
[[ "$home" == 'https://yolokfx.com' ]]
[[ "$version" == '1.2.0' && "$status" == 'active' ]]

sudo mkdir -p "$BACKUP"
sudo cp -a "$WP/quiz" "$BACKUP/quiz-before"
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-before.json" >/dev/null
sudo chown "$OWNER:$OWNER" "$BACKUP/landings-before.json"
sudo chmod 600 "$BACKUP/landings-before.json"
sudo test -s "$BACKUP/landings-before.json"
sudo -u "$OWNER" env MGS_DQ_BACKUP_JSON="$BACKUP/landings-before.json" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);if(!is_array($items)||count($items)!==18){throw new Exception("backup_decode_failed");}echo "BACKUP_DECODE_OK";' --allow-root
sudo python3 - "$BACKUP/landings-before.json" <<'PY'
import json,sys
items=json.load(open(sys.argv[1],encoding='utf-8'))
assert len(items)==18
v3=[x for x in items if x.get('country')=='us' and x.get('layout_template')=='lp3']
assert len(v3)==6 and sorted(x['manager_code'] for x in v3)==[f'G{i:03d}' for i in range(1,7)]
expected=['Women','Men','Kids','Shoes','Phones','Accessories']
for x in v3:
 assert x.get('active')==1
 assert x.get('title')=='Get Free Products Delivered to Your Home'
 assert [c.get('text') for c in x.get('categories',[])]==expected
print(json.dumps({'preflight':'PASS','items':18,'v3':6,'categories':expected},separators=(',',':')))
PY

MUTATED=1
change_json=$(sudo -u "$OWNER" wp --path="$WP" eval '
$items=MGS_Direct_Quiz::items();$oldTitle="Get Free Products Delivered to Your Home";$newTitle="Would you like to receive for free?";$changed=0;$fields=0;
foreach($items as &$item){if(($item["country"]??"")!=="us"||($item["layout_template"]??"")!=="lp3"){continue;}if(($item["title"]??"")!==$oldTitle){throw new Exception("title_precondition_".($item["slug"]??"unknown"));}$cats=(array)($item["categories"]??[]);$hits=0;foreach($cats as &$cat){if(($cat["text"]??"")==="Phones"){$cat["text"]="Electronics";$hits++;}}unset($cat);if($hits!==1){throw new Exception("phones_precondition_".($item["slug"]??"unknown")."_".$hits);}$item["title"]=$newTitle;$item["categories"]=$cats;$changed++;$fields+=2;}
unset($item);if($changed!==6||$fields!==12){throw new Exception("target_count_mismatch");}if(!MGS_Direct_Quiz::save_items($items)){throw new Exception("option_save_failed");}$sync=MGS_Direct_Quiz::sync_static_pages();if(is_wp_error($sync)){throw new Exception($sync->get_error_message());}if(count($sync)!==17){throw new Exception("sync_count_".count($sync));}echo wp_json_encode(["changed_items"=>$changed,"changed_fields"=>$fields,"active_sync_count"=>count($sync)],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root)

sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-after.json" >/dev/null
sudo chown "$OWNER:$OWNER" "$BACKUP/landings-after.json"
sudo chmod 600 "$BACKUP/landings-after.json"
sudo python3 - "$BACKUP/landings-before.json" "$BACKUP/landings-after.json" "$WP" "$BACKUP/verification.json" <<'PY'
import copy,hashlib,json,os,sys
from html.parser import HTMLParser
class TextParser(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]
 def handle_data(self,data): self.parts.append(data)
def visible_text(html):
 p=TextParser(); p.feed(html); return ' '.join(' '.join(p.parts).split())
before=json.load(open(sys.argv[1],encoding='utf-8')); after=json.load(open(sys.argv[2],encoding='utf-8')); wp,out=sys.argv[3:]
assert len(before)==len(after)==18
b={str(x['id']):x for x in before}; a={str(x['id']):x for x in after}; assert set(b)==set(a)
changed=[]
for ident,old in b.items():
 cur=a[ident]
 if old.get('layout_template')!='lp3':
  assert cur==old, (cur.get('slug'),'non_v3_drift')
  continue
 oc=copy.deepcopy(old); cc=copy.deepcopy(cur)
 assert oc.pop('title')=='Get Free Products Delivered to Your Home'
 assert cc.pop('title')=='Would you like to receive for free?'
 old_cats=oc.pop('categories'); new_cats=cc.pop('categories')
 assert len(old_cats)==len(new_cats)==6
 assert [x.get('text') for x in old_cats]==['Women','Men','Kids','Shoes','Phones','Accessories']
 assert [x.get('text') for x in new_cats]==['Women','Men','Kids','Shoes','Electronics','Accessories']
 for o,n in zip(old_cats,new_cats):
  oo=copy.deepcopy(o); nn=copy.deepcopy(n); ot=oo.pop('text'); nt=nn.pop('text'); assert oo==nn; assert (ot,nt) in {(ot,ot),('Phones','Electronics')}
 assert oc==cc, (cur.get('slug'),'non_target_drift')
 changed.append(cur['slug'])
assert sorted(changed)==[f'sh3-g{i:03d}' for i in range(1,7)]
active=[x for x in after if x.get('active')]; assert len(active)==17
rows=[]
for x in active:
 path=os.path.join(wp,'quiz','us',x['slug'],'index.html'); assert os.path.isfile(path)
 html=open(path,encoding='utf-8').read(); text=visible_text(html)
 assert 'MGS Direct Quiz static; plugin=1.2.0' in html
 assert '<form' not in html.lower() and '<input' not in html.lower()
 if x['layout_template']=='lp3':
  assert 'Would you like to receive for free?' in text
  assert 'Get Free Products Delivered to Your Home' not in text
  assert 'Electronics' in text and 'Phones' not in text
  assert html.count('data-mgs-dq-cta')==7 and html.count('class="mgs-dq-category"')==6
 else:
  assert 'Get Free Products Delivered to Your Home' in text
  assert 'Would you like to get free products?' in text
  assert html.count('data-mgs-dq-cta')==2
 rows.append({'slug':x['slug'],'layout':x['layout_template'],'sha256':hashlib.sha256(html.encode()).hexdigest()})
summary={'readback':'PASS','items':18,'changed_items':6,'changed_fields':12,'active_static_routes':17,'non_target_fields_preserved':True,'routes':rows}
open(out,'w',encoding='utf-8').write(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='routes'},separators=(',',':')))
PY
sudo python3 - "$BACKUP" <<'PY'
import hashlib,json,os,sys
root=sys.argv[1]; files=[]
for cur,dirs,names in os.walk(root):
 dirs.sort(); names.sort()
 for name in names:
  p=os.path.join(cur,name)
  if os.path.isfile(p): files.append({'path':os.path.relpath(p,root),'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'bytes':os.path.getsize(p)})
with open(os.path.join(root,'SHA256-MANIFEST.json'),'w',encoding='utf-8') as f: json.dump({'files':files},f,separators=(',',':')); f.write('\n')
print(json.dumps({'backup_files':len(files),'manifest':os.path.join(root,'SHA256-MANIFEST.json')},separators=(',',':')))
PY
sudo test -d "$BACKUP/quiz-before"
sudo test -s "$BACKUP/landings-before.json"
sudo test -s "$BACKUP/landings-after.json"
sudo test -s "$BACKUP/verification.json"
sudo test -s "$BACKUP/SHA256-MANIFEST.json"
MUTATED=0
printf 'SITE=yolokfx.com\nVERSION=%s\nSTATUS=%s\nBACKUP=%s\nCHANGE=%s\n' "$version" "$status" "$BACKUP" "$change_json"
