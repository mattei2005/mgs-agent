#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
BACK=/home/runcloud/backups/yolokfx-direct-quiz-copy-recovery-20260923T023052Z
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
nginx_state=$(sudo systemctl is-active nginx-rc)
apache_state=$(sudo systemctl is-active apache2-rc)
sudo test -s "$BACK/verification.json"
sudo test -s "$BACK/SHA256-MANIFEST.json"
sudo test -s "$BACK/wp-fastest-cache-before/sh1-g002/index.html"
sudo test -s "$BACK/wp-fastest-cache-before/sh2-g002/index.html"
sudo -u "$OWNER" wp --path="$WP" eval '
$items=MGS_Direct_Quiz::items();$counts=["lp1"=>0,"lp2"=>0,"lp3"=>0];$active=0;
foreach($items as $x){$l=(string)($x["layout_template"]??"");if(($x["country"]??"")!=="us"||!isset($counts[$l])){continue;}$counts[$l]++;if(!empty($x["active"]))$active++;if(($x["title"]??"")!=="Get Free Products Delivered to Your Home"){throw new Exception("title_".($x["slug"]??"unknown"));}if(($l==="lp1"||$l==="lp2")&&($x["question"]??"")!=="Would you like to get free products?"){throw new Exception("question_".($x["slug"]??"unknown"));}}
if(count($items)!==18||$counts!==["lp1"=>6,"lp2"=>6,"lp3"=>6]||$active!==17){throw new Exception("count_mismatch");}
echo wp_json_encode(["items"=>count($items),"counts"=>$counts,"active"=>$active,"copy_readback"=>"PASS"],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root
sudo python3 - "$WP/wp-content/cache/all/quiz/us" <<'PY'
import json,os,sys
root=sys.argv[1]; rows=[]
for slug in ('sh1-g002','sh2-g002'):
 p=os.path.join(root,slug,'index.html')
 if os.path.isfile(p):
  h=open(p,encoding='utf-8').read()
  assert 'Get Free Products Delivered to Your Home' in h
  assert 'Get Free SHEIN Products Delivered to Your Home' not in h
  rows.append({'slug':slug,'cache_present':True,'cache_new_copy':True})
 else:
  rows.append({'slug':slug,'cache_present':False,'cache_new_copy':None})
print(json.dumps({'wp_fastest_cache':rows},separators=(',',':')))
PY
printf 'VERSION=%s\nPLUGIN_STATUS=%s\nNGINX=%s\nAPACHE=%s\nBACKUP=%s\n' "$version" "$status" "$nginx_state" "$apache_state" "$BACK"
