#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
BACK=/home/runcloud/backups/yolokfx-v3-title-electronics-20260923T025845Z
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
nginx_state=$(sudo systemctl is-active nginx-rc)
apache_state=$(sudo systemctl is-active apache2-rc)
sudo test -d "$BACK/quiz-before"
sudo test -s "$BACK/landings-before.json"
sudo test -s "$BACK/landings-after.json"
sudo test -s "$BACK/verification.json"
sudo test -s "$BACK/SHA256-MANIFEST.json"
sudo -u "$OWNER" wp --path="$WP" eval '
$items=MGS_Direct_Quiz::items();$v3=[];
foreach($items as $x){if(($x["country"]??"")==="us"&&($x["layout_template"]??"")==="lp3"){$v3[]=$x;}}
if(count($items)!==18||count($v3)!==6){throw new Exception("count_mismatch");}
foreach($v3 as $x){if(($x["title"]??"")!=="Would you like to receive for free?"){throw new Exception("title_".($x["slug"]??"unknown"));}$texts=array_map(fn($c)=>(string)($c["text"]??""),(array)($x["categories"]??[]));if($texts!==["Women","Men","Kids","Shoes","Electronics","Accessories"]){throw new Exception("categories_".($x["slug"]??"unknown"));}}
echo wp_json_encode(["items"=>count($items),"v3"=>count($v3),"title_and_categories_readback"=>"PASS"],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root
sudo python3 - "$WP/wp-content/cache/all/quiz/us" <<'PY'
import json,os,sys
root=sys.argv[1]; rows=[]
for i in range(1,7):
 slug=f'sh3-g{i:03d}'; p=os.path.join(root,slug,'index.html')
 if os.path.isfile(p):
  h=open(p,encoding='utf-8').read(); assert 'Would you like to receive for free?' in h and 'Get Free Products Delivered to Your Home' not in h and 'Electronics' in h
  rows.append({'slug':slug,'cache_present':True,'cache_copy':'new'})
 else: rows.append({'slug':slug,'cache_present':False,'cache_copy':None})
print(json.dumps({'v3_cache_readback':rows},separators=(',',':')))
PY
printf 'VERSION=%s\nPLUGIN_STATUS=%s\nNGINX=%s\nAPACHE=%s\nBACKUP=%s\n' "$version" "$status" "$nginx_state" "$apache_state" "$BACK"
