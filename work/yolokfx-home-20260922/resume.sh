#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
BACKUP=/home/runcloud/backups/yolokfx-v3-home-20260923T031817Z
ASSET="$BACKUP/yolokfx-home-category-1552154990036918324.png"
EXPECTED_SHA=2934ec2da3084747ae68ca1823fcfa82ec62bdd9a08f80de7aa211ed6b4cce78
MUTATED=0
ATTACHMENT_ID=0
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
  if [[ "$ATTACHMENT_ID" != 0 ]]; then printf 'UNUSED_ATTACHMENT_PRESERVED=%s\n' "$ATTACHMENT_ID" >&2; fi
  printf 'ROLLBACK_PATH=%s\n' "$BACKUP" >&2
}
on_error() { rc=$?; trap - ERR; rollback; exit "$rc"; }
trap on_error ERR

home=$(sudo -u "$OWNER" wp --path="$WP" option get home --allow-root)
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
[[ "$home" == 'https://yolokfx.com' ]]
[[ "$version" == '1.2.0' && "$status" == 'active' ]]
sudo test -d "$BACKUP/quiz-before"
sudo test -s "$BACKUP/landings-before.json"
sudo test -s "$ASSET"
sudo chown "$OWNER:$OWNER" "$BACKUP" "$BACKUP/landings-before.json" "$ASSET"
sudo chmod 750 "$BACKUP"
sudo chmod 600 "$BACKUP/landings-before.json"
sudo chmod 644 "$ASSET"
actual_sha=$(sudo -u "$OWNER" sha256sum "$ASSET" | python3 -c 'import sys; print(sys.stdin.read().split()[0])')
[[ "$actual_sha" == "$EXPECTED_SHA" ]]
existing=$(sudo -u "$OWNER" wp --path="$WP" eval '$p=get_page_by_path("yolokfx-home-category-1552154990036918324",OBJECT,"attachment");echo $p?(int)$p->ID:0;' --allow-root)
[[ "$existing" == 0 ]]
sudo -u "$OWNER" env MGS_DQ_BACKUP_JSON="$BACKUP/landings-before.json" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);if(!is_array($items)||count($items)!==18){throw new Exception("backup_decode_failed");}echo "BACKUP_DECODE_OK";' --allow-root
sudo python3 - "$BACKUP/landings-before.json" <<'PY'
import json,sys
items=json.load(open(sys.argv[1],encoding='utf-8')); assert len(items)==18
v3=[x for x in items if x.get('country')=='us' and x.get('layout_template')=='lp3']; assert len(v3)==6
for x in v3:
 assert x.get('title')=='Would you like to receive for free?'
 cats=x.get('categories',[]); assert [c.get('text') for c in cats]==['Women','Men','Kids','Shoes','Electronics','Accessories']; assert cats[2].get('image_url','')==''
print(json.dumps({'recovery_preflight':'PASS','v3':6,'asset_sha256':'2934ec2da3084747ae68ca1823fcfa82ec62bdd9a08f80de7aa211ed6b4cce78'},separators=(',',':')))
PY

import_out=$(sudo -u "$OWNER" wp --path="$WP" media import "$ASSET" --title='YOLOKFX Home Category' --alt='Home' --porcelain --allow-root)
ATTACHMENT_ID=$(python3 -c 'import re,sys; nums=re.findall(r"(?m)^\s*(\d+)\s*$",sys.stdin.read()); print(nums[-1] if nums else "")' <<< "$import_out")
[[ "$ATTACHMENT_ID" =~ ^[1-9][0-9]*$ ]]
attachment_json=$(sudo -u "$OWNER" env ATTACHMENT_ID="$ATTACHMENT_ID" EXPECTED_SHA="$EXPECTED_SHA" wp --path="$WP" eval '
$id=(int)getenv("ATTACHMENT_ID");$url=wp_get_attachment_url($id);$file=get_attached_file($id);$meta=wp_get_attachment_metadata($id);$alt=get_post_meta($id,"_wp_attachment_image_alt",true);if(!$url||strpos($url,"https://yolokfx.com/wp-content/uploads/")!==0||!is_file($file)){throw new Exception("attachment_path_invalid");}if(hash_file("sha256",$file)!==getenv("EXPECTED_SHA")){throw new Exception("attachment_hash_mismatch");}if((int)($meta["width"]??0)!==600||(int)($meta["height"]??0)!==600||$alt!=="Home"){throw new Exception("attachment_metadata_invalid");}echo wp_json_encode(["id"=>$id,"url"=>$url,"file"=>$file,"width"=>(int)$meta["width"],"height"=>(int)$meta["height"],"alt"=>$alt,"sha256"=>hash_file("sha256",$file)],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root)
HOME_IMAGE_URL=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])' <<< "$attachment_json")
[[ "$HOME_IMAGE_URL" == https://yolokfx.com/wp-content/uploads/* ]]

MUTATED=1
change_json=$(sudo -u "$OWNER" env HOME_IMAGE_URL="$HOME_IMAGE_URL" wp --path="$WP" eval '
$url=(string)getenv("HOME_IMAGE_URL");$items=MGS_Direct_Quiz::items();$changed=0;$fields=0;
foreach($items as &$item){if(($item["country"]??"")!=="us"||($item["layout_template"]??"")!=="lp3"){continue;}$cats=(array)($item["categories"]??[]);if(count($cats)!==6||($cats[2]["text"]??"")!=="Kids"||($cats[2]["image_url"]??"")!==""){throw new Exception("kids_precondition_".($item["slug"]??"unknown"));}$cats[2]["text"]="Home";$cats[2]["image_url"]=$url;$item["categories"]=$cats;$changed++;$fields+=2;}
unset($item);if($changed!==6||$fields!==12){throw new Exception("target_count_mismatch");}if(!MGS_Direct_Quiz::save_items($items)){throw new Exception("option_save_failed");}$sync=MGS_Direct_Quiz::sync_static_pages();if(is_wp_error($sync)){throw new Exception($sync->get_error_message());}if(count($sync)!==17){throw new Exception("sync_count_".count($sync));}echo wp_json_encode(["changed_items"=>$changed,"changed_fields"=>$fields,"active_sync_count"=>count($sync),"image_url"=>$url],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root)

sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-after.json" >/dev/null
sudo chown "$OWNER:$OWNER" "$BACKUP/landings-after.json"
sudo chmod 600 "$BACKUP/landings-after.json"
sudo python3 - "$BACKUP/landings-before.json" "$BACKUP/landings-after.json" "$WP" "$BACKUP/verification.json" "$HOME_IMAGE_URL" <<'PY'
import copy,hashlib,json,os,sys
from html.parser import HTMLParser
class TextParser(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]
 def handle_data(self,data): self.parts.append(data)
def visible_text(source): p=TextParser(); p.feed(source); return ' '.join(' '.join(p.parts).split())
before=json.load(open(sys.argv[1],encoding='utf-8')); after=json.load(open(sys.argv[2],encoding='utf-8')); wp,out,url=sys.argv[3:]
assert len(before)==len(after)==18
b={str(x['id']):x for x in before}; a={str(x['id']):x for x in after}; assert set(b)==set(a); changed=[]
for ident,old in b.items():
 cur=a[ident]
 if old.get('layout_template')!='lp3': assert cur==old; continue
 oc=copy.deepcopy(old); cc=copy.deepcopy(cur); old_cats=oc.pop('categories'); new_cats=cc.pop('categories'); assert oc==cc
 for idx,(o,n) in enumerate(zip(old_cats,new_cats)):
  if idx==2:
   assert o.get('text')=='Kids' and o.get('image_url','')=='' and n.get('text')=='Home' and n.get('image_url')==url
   oo=copy.deepcopy(o); nn=copy.deepcopy(n); oo.pop('text'); oo.pop('image_url'); nn.pop('text'); nn.pop('image_url'); assert oo==nn
  else: assert o==n
 changed.append(cur['slug'])
assert sorted(changed)==[f'sh3-g{i:03d}' for i in range(1,7)]
active=[x for x in after if x.get('active')]; assert len(active)==17; rows=[]
for x in active:
 path=os.path.join(wp,'quiz','us',x['slug'],'index.html'); html=open(path,encoding='utf-8').read(); text=visible_text(html)
 assert 'MGS Direct Quiz static; plugin=1.2.0' in html
 if x['layout_template']=='lp3': assert 'Home' in text and 'Kids' not in text and url in html and 'Would you like to receive for free?' in text and 'Electronics' in text and html.count('data-mgs-dq-cta')==7
 else: assert 'Get Free Products Delivered to Your Home' in text and 'Would you like to get free products?' in text and html.count('data-mgs-dq-cta')==2
 rows.append({'slug':x['slug'],'layout':x['layout_template'],'sha256':hashlib.sha256(html.encode()).hexdigest()})
summary={'recovery':'PASS','readback':'PASS','items':18,'changed_items':6,'changed_fields':12,'attachment_id':None,'image_url':url,'active_static_routes':17,'non_target_fields_preserved':True,'routes':rows}
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
sudo test -s "$BACKUP/landings-after.json"
sudo test -s "$BACKUP/verification.json"
sudo test -s "$BACKUP/SHA256-MANIFEST.json"
MUTATED=0
printf 'SITE=yolokfx.com\nVERSION=%s\nSTATUS=%s\nBACKUP=%s\nATTACHMENT=%s\nCHANGE=%s\n' "$version" "$status" "$BACKUP" "$attachment_json" "$change_json"
