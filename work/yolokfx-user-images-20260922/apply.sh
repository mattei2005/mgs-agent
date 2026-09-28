#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/home/runcloud/backups/yolokfx-v3-user-images-${STAMP}"
MESSAGE_ID=1552159700240437318
CATEGORIES=(women men home shoes electronics others)
declare -A EXPECTED_SHA=(
  [women]=80f52a0460b945b22e4e7ff51c9b2f0c531f41b1eeb85faf34c24a9e82ec8003
  [men]=452cf1b9e53294266c2afbeee8053d069e761524911d4d6fef051bc897e3da97
  [home]=274eb872121272d44c665883bfd37168a5c92dbba062f5f835d69fb1d3e202cd
  [shoes]=7c071681e88cdf1696943e19bcf1fbe7b7d518880c98e5d223deb307c87410bf
  [electronics]=ccd83735d73cf266449318f4483c5b8885e5185992f9c5e047b53951bf5f02fa
  [others]=028f3296299a0508c991ba699eca2115ee9ec814dc355a1a9084f982087340a8
)
declare -A LABEL=( [women]=Women [men]=Men [home]=Home [shoes]=Shoes [electronics]=Electronics [others]=Others )
declare -A URL=()
declare -A ID=()
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
  printf 'IMPORTED_ATTACHMENTS_PRESERVED=' >&2
  for cat in "${CATEGORIES[@]}"; do [[ -n "${ID[$cat]:-}" ]] && printf '%s:%s ' "$cat" "${ID[$cat]}" >&2; done
  printf '\nROLLBACK_PATH=%s\n' "$BACKUP" >&2
}
on_error() { rc=$?; trap - ERR; rollback; exit "$rc"; }
trap on_error ERR

home=$(sudo -u "$OWNER" wp --path="$WP" option get home --allow-root)
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
[[ "$home" == 'https://yolokfx.com' && "$version" == '1.2.0' && "$status" == 'active' ]]
for cat in "${CATEGORIES[@]}"; do
  staged="/home/zeus/yolokfx-v3-${cat}-${MESSAGE_ID}.png"
  test -s "$staged"
  actual=$(sha256sum "$staged" | python3 -c 'import sys; print(sys.stdin.read().split()[0])')
  [[ "$actual" == "${EXPECTED_SHA[$cat]}" ]]
done

sudo mkdir -p "$BACKUP"
sudo chown "$OWNER:$OWNER" "$BACKUP"
sudo chmod 750 "$BACKUP"
sudo cp -a "$WP/quiz" "$BACKUP/quiz-before"
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-before.json" >/dev/null
sudo chown "$OWNER:$OWNER" "$BACKUP/landings-before.json"
sudo chmod 600 "$BACKUP/landings-before.json"
for cat in "${CATEGORIES[@]}"; do
  staged="/home/zeus/yolokfx-v3-${cat}-${MESSAGE_ID}.png"
  asset="$BACKUP/yolokfx-v3-${cat}-${MESSAGE_ID}.png"
  sudo mv "$staged" "$asset"
  sudo chown "$OWNER:$OWNER" "$asset"
  sudo chmod 644 "$asset"
  actual=$(sudo -u "$OWNER" sha256sum "$asset" | python3 -c 'import sys; print(sys.stdin.read().split()[0])')
  [[ "$actual" == "${EXPECTED_SHA[$cat]}" ]]
done
sudo -u "$OWNER" env MGS_DQ_BACKUP_JSON="$BACKUP/landings-before.json" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);if(!is_array($items)||count($items)!==18){throw new Exception("backup_decode_failed");}echo "BACKUP_DECODE_OK";' --allow-root
sudo python3 - "$BACKUP/landings-before.json" <<'PY'
import json,sys
items=json.load(open(sys.argv[1],encoding='utf-8')); assert len(items)==18
v3=[x for x in items if x.get('country')=='us' and x.get('layout_template')=='lp3']; assert len(v3)==6
old_home='https://yolokfx.com/wp-content/uploads/2026/09/yolokfx-home-category-1552154990036918324.png'
for x in v3:
 assert x.get('title')=='Would you like to receive for free?'
 cats=x.get('categories',[]); assert len(cats)==6
 assert [c.get('text') for c in cats]==['Women','Men','Home','Shoes','Electronics','Accessories']
 assert [c.get('image_url','') for c in cats]==['','',old_home,'','','']
print(json.dumps({'preflight':'PASS','items':18,'v3':6,'current_labels':['Women','Men','Home','Shoes','Electronics','Accessories']},separators=(',',':')))
PY

sudo -u "$OWNER" bash -c ': > "$1"' _ "$BACKUP/attachments.jsonl"
for cat in "${CATEGORIES[@]}"; do
  slug="yolokfx-v3-${cat}-${MESSAGE_ID}"
  asset="$BACKUP/${slug}.png"
  id=$(sudo -u "$OWNER" env ATTACHMENT_SLUG="$slug" wp --path="$WP" eval '$p=get_page_by_path(getenv("ATTACHMENT_SLUG"),OBJECT,"attachment");echo $p?(int)$p->ID:0;' --allow-root)
  if [[ "$id" == 0 ]]; then
    import_out=$(sudo -u "$OWNER" wp --path="$WP" media import "$asset" --title="YOLOKFX V3 ${LABEL[$cat]}" --alt="${LABEL[$cat]}" --porcelain --allow-root)
    id=$(python3 -c 'import re,sys; nums=re.findall(r"(?m)^\s*(\d+)\s*$",sys.stdin.read()); print(nums[-1] if nums else "")' <<< "$import_out")
  fi
  [[ "$id" =~ ^[1-9][0-9]*$ ]]
  ID[$cat]="$id"
  attachment_json=$(sudo -u "$OWNER" env ATTACHMENT_ID="$id" EXPECTED_ALT="${LABEL[$cat]}" wp --path="$WP" eval '
$id=(int)getenv("ATTACHMENT_ID");$url=wp_get_attachment_url($id);$file=get_attached_file($id);$meta=wp_get_attachment_metadata($id);$alt=get_post_meta($id,"_wp_attachment_image_alt",true);if(get_post_status($id)!=="publish"||get_post_mime_type($id)!=="image/png"||!$url||strpos($url,"https://yolokfx.com/wp-content/uploads/")!==0||!is_file($file)){throw new Exception("attachment_invalid");}if((int)($meta["width"]??0)!==600||(int)($meta["height"]??0)!==600||$alt!==getenv("EXPECTED_ALT")){throw new Exception("attachment_metadata_invalid");}echo wp_json_encode(["id"=>$id,"url"=>$url,"file"=>$file,"width"=>(int)$meta["width"],"height"=>(int)$meta["height"],"alt"=>$alt,"sha256"=>hash_file("sha256",$file),"bytes"=>filesize($file)],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root)
  URL[$cat]=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])' <<< "$attachment_json")
  sudo -u "$OWNER" bash -c 'printf "%s\n" "$1" >> "$2"' _ "$attachment_json" "$BACKUP/attachments.jsonl"
done

MUTATED=1
change_json=$(sudo -u "$OWNER" env IMG_WOMEN="${URL[women]}" IMG_MEN="${URL[men]}" IMG_HOME="${URL[home]}" IMG_SHOES="${URL[shoes]}" IMG_ELECTRONICS="${URL[electronics]}" IMG_OTHERS="${URL[others]}" wp --path="$WP" eval '
$urls=[getenv("IMG_WOMEN"),getenv("IMG_MEN"),getenv("IMG_HOME"),getenv("IMG_SHOES"),getenv("IMG_ELECTRONICS"),getenv("IMG_OTHERS")];if(count(array_unique($urls))!==6){throw new Exception("image_urls_not_unique");}$items=MGS_Direct_Quiz::items();$changed=0;$fields=0;$oldHome="https://yolokfx.com/wp-content/uploads/2026/09/yolokfx-home-category-1552154990036918324.png";
foreach($items as &$item){if(($item["country"]??"")!=="us"||($item["layout_template"]??"")!=="lp3"){continue;}$cats=(array)($item["categories"]??[]);if(count($cats)!==6||array_map(fn($c)=>(string)($c["text"]??""),$cats)!==["Women","Men","Home","Shoes","Electronics","Accessories"]||array_map(fn($c)=>(string)($c["image_url"]??""),$cats)!==["","",$oldHome,"","",""]){throw new Exception("precondition_".($item["slug"]??"unknown"));}for($i=0;$i<6;$i++){$cats[$i]["image_url"]=$urls[$i];$fields++;}$cats[5]["text"]="Others";$fields++;$item["categories"]=$cats;$changed++;}
unset($item);if($changed!==6||$fields!==42){throw new Exception("target_count_mismatch_".$changed."_".$fields);}if(!MGS_Direct_Quiz::save_items($items)){throw new Exception("option_save_failed");}$sync=MGS_Direct_Quiz::sync_static_pages();if(is_wp_error($sync)){throw new Exception($sync->get_error_message());}if(count($sync)!==17){throw new Exception("sync_count_".count($sync));}echo wp_json_encode(["changed_items"=>$changed,"changed_fields"=>$fields,"active_sync_count"=>count($sync),"image_urls"=>$urls],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root)

sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-after.json" >/dev/null
sudo chown "$OWNER:$OWNER" "$BACKUP/landings-after.json"
sudo chmod 600 "$BACKUP/landings-after.json"
sudo python3 - "$BACKUP/landings-before.json" "$BACKUP/landings-after.json" "$WP" "$BACKUP/verification.json" "${URL[women]}" "${URL[men]}" "${URL[home]}" "${URL[shoes]}" "${URL[electronics]}" "${URL[others]}" <<'PY'
import copy,hashlib,json,os,sys
from html.parser import HTMLParser
class TextParser(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]
 def handle_data(self,data): self.parts.append(data)
def visible_text(source): p=TextParser(); p.feed(source); return ' '.join(' '.join(p.parts).split())
before=json.load(open(sys.argv[1],encoding='utf-8')); after=json.load(open(sys.argv[2],encoding='utf-8')); wp,out=sys.argv[3:5]; urls=sys.argv[5:]
assert len(before)==len(after)==18 and len(urls)==6 and len(set(urls))==6
b={str(x['id']):x for x in before}; a={str(x['id']):x for x in after}; assert set(b)==set(a); changed=[]
for ident,old in b.items():
 cur=a[ident]
 if old.get('layout_template')!='lp3': assert cur==old; continue
 oc=copy.deepcopy(old); cc=copy.deepcopy(cur); old_cats=oc.pop('categories'); new_cats=cc.pop('categories'); assert oc==cc
 assert [x.get('text') for x in new_cats]==['Women','Men','Home','Shoes','Electronics','Others']
 assert [x.get('image_url') for x in new_cats]==urls
 for idx,(o,n) in enumerate(zip(old_cats,new_cats)):
  oo=copy.deepcopy(o); nn=copy.deepcopy(n); ot=oo.pop('text'); nt=nn.pop('text'); oo.pop('image_url'); nn.pop('image_url'); assert oo==nn
  if idx==5: assert (ot,nt)==('Accessories','Others')
  else: assert ot==nt
 changed.append(cur['slug'])
assert sorted(changed)==[f'sh3-g{i:03d}' for i in range(1,7)]
active=[x for x in after if x.get('active')]; assert len(active)==17; rows=[]
for x in active:
 path=os.path.join(wp,'quiz','us',x['slug'],'index.html'); html=open(path,encoding='utf-8').read(); text=visible_text(html)
 assert 'MGS Direct Quiz static; plugin=1.2.0' in html
 if x['layout_template']=='lp3':
  for label in ['Women','Men','Home','Shoes','Electronics','Others']: assert label in text
  assert 'Kids' not in text and 'Phones' not in text and 'Accessories' not in text
  for url in urls: assert url in html
  assert html.count('data-mgs-dq-cta')==7 and html.count('class="mgs-dq-category"')==6
 else: assert 'Get Free Products Delivered to Your Home' in text and 'Would you like to get free products?' in text and html.count('data-mgs-dq-cta')==2
 rows.append({'slug':x['slug'],'layout':x['layout_template'],'sha256':hashlib.sha256(html.encode()).hexdigest()})
summary={'readback':'PASS','items':18,'changed_items':6,'changed_fields':42,'labels':['Women','Men','Home','Shoes','Electronics','Others'],'image_urls':urls,'active_static_routes':17,'non_target_fields_preserved':True,'routes':rows}
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
sudo test -s "$BACKUP/attachments.jsonl"
sudo test -s "$BACKUP/landings-after.json"
sudo test -s "$BACKUP/verification.json"
sudo test -s "$BACKUP/SHA256-MANIFEST.json"
MUTATED=0
printf 'SITE=yolokfx.com\nVERSION=%s\nSTATUS=%s\nBACKUP=%s\nATTACHMENTS=%s\nCHANGE=%s\n' "$version" "$status" "$BACKUP" "$(sudo -u "$OWNER" tr '\n' ' ' < "$BACKUP/attachments.jsonl")" "$change_json"
