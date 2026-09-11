#!/usr/bin/env bash
set -Eeuo pipefail
SITE=${1:-}
case "$SITE" in vizioid|yolokfx) ;; *) printf 'invalid site\n' >&2; exit 2;; esac
OWNER=runcloud
WP="/home/runcloud/webapps/$SITE"
ACTIVE="$WP/wp-content/plugins/mgs-direct-quiz"
ARCHIVE=/tmp/mgs-direct-quiz-1.2.0.tar.gz
EXPECTED=8f62156f0efab144ca0d7e2b3e7f88343a3d6cb29beeede3e020feb5b0c4421c
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/home/runcloud/backups/${SITE}-mgs-direct-quiz-1.2.0-v3-${STAMP}"
STAGE="$BACKUP/stage"
OLD="$BACKUP/plugin-live-before"
MUTATED=0

rollback() {
  set +e
  if [[ "$MUTATED" == 1 ]]; then
    sudo mkdir -p "$BACKUP/failed-state"
    if sudo test -d "$WP/quiz"; then sudo mv "$WP/quiz" "$BACKUP/failed-state/quiz-after-failure"; fi
    if sudo test -d "$BACKUP/quiz-before"; then sudo cp -a "$BACKUP/quiz-before" "$WP/quiz"; fi
    if sudo test -d "$ACTIVE"; then sudo mv "$ACTIVE" "$BACKUP/failed-state/plugin-after-failure"; fi
    if sudo test -d "$OLD"; then sudo mv "$OLD" "$ACTIVE"; fi
    sudo chown -R "$OWNER:$OWNER" "$WP/quiz" "$ACTIVE" 2>/dev/null || true
    sudo -u "$OWNER" env MGS_DQ_BACKUP_JSON="$BACKUP/landings-before.json" MGS_DQ_STATIC_VERSION_FILE="$BACKUP/static-version-before.txt" wp --path="$WP" eval '$items=json_decode(file_get_contents(getenv("MGS_DQ_BACKUP_JSON")),true);if(!is_array($items)){throw new Exception("invalid_backup_json");}update_option("mgs_direct_quiz_landings",$items,false);$v=trim((string)file_get_contents(getenv("MGS_DQ_STATIC_VERSION_FILE")));update_option("mgs_direct_quiz_static_version",$v,false);' --allow-root >/dev/null 2>&1 || true
  fi
  printf 'ROLLBACK_PATH=%s\n' "$BACKUP" >&2
}
on_error() { rc=$?; trap - ERR; rollback; exit "$rc"; }
trap on_error ERR

actual=$(sha256sum "$ARCHIVE" | python3 -c 'import sys; print(sys.stdin.read().split()[0])')
[[ "$actual" == "$EXPECTED" ]]
home=$(sudo -u "$OWNER" wp --path="$WP" option get home --allow-root)
[[ "$home" == "https://$SITE.com" ]]
old_version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
old_status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
[[ "$old_version" == '1.1.1' && "$old_status" == 'active' ]]
sudo test ! -e "$WP/quiz/us/sh3-g002"

sudo mkdir -p "$STAGE"
sudo cp -a "$ACTIVE" "$OLD"
sudo cp -a "$WP/quiz" "$BACKUP/quiz-before"
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root | sudo tee "$BACKUP/landings-before.json" >/dev/null
sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_static_version --allow-root | sudo tee "$BACKUP/static-version-before.txt" >/dev/null
sudo chmod 600 "$BACKUP/landings-before.json" "$BACKUP/static-version-before.txt"
sudo test -s "$BACKUP/landings-before.json"
sudo tar -xzf "$ARCHIVE" -C "$STAGE"
sudo chown -R "$OWNER:$OWNER" "$STAGE/mgs-direct-quiz"
sudo python3 - "$STAGE/mgs-direct-quiz" <<'PY'
import os,sys
root=sys.argv[1]
for current,dirs,files in os.walk(root):
    os.chmod(current,0o755)
    for name in files:
        os.chmod(os.path.join(current,name),0o644)
PY
sudo mv "$ACTIVE" "$BACKUP/plugin-copy-before"
sudo mv "$STAGE/mgs-direct-quiz" "$ACTIVE"
MUTATED=1

create_json=$(sudo -u "$OWNER" wp --path="$WP" eval '
$items=MGS_Direct_Quiz::items();
foreach($items as $existing){if(($existing["country"]??"")==="us"&&($existing["slug"]??"")==="sh3-g002"){throw new Exception("route_exists");}}
$source=null;
foreach($items as $existing){if(($existing["country"]??"")==="us"&&($existing["manager_code"]??"")==="G002"&&($existing["layout_template"]??"")==="lp2"&&!empty($existing["active"])){$source=$existing;break;}}
if(!$source){throw new Exception("active_g002_lp2_source_missing");}
$now=current_time("mysql",true);
$item=array(
 "id"=>wp_generate_uuid4(),"name"=>"SHEIN US — G002 — V3","country"=>"us","manager_code"=>"G002","slug"=>"sh3-g002","layout_template"=>"lp3",
 "logo_url"=>(string)($source["logo_url"]??""),"title"=>"What would you like to receive?","question"=>"Choose a category to continue.",
 "option_a_text"=>"Continue","option_a_icon"=>"","option_b_text"=>"Continue","option_b_icon"=>"",
 "urgency_text"=>"Today’s offer ends in","eyebrow_text"=>"FREE ITEMS · SEE HOW TO GET","cta_text"=>"SEE TODAY’S BEST DEALS","micro_text"=>"You’ll stay on this site","disclaimer_text"=>"",
 "categories"=>array(
   array("text"=>"Women","image_url"=>""),array("text"=>"Men","image_url"=>""),array("text"=>"Kids","image_url"=>""),
   array("text"=>"Shoes","image_url"=>""),array("text"=>"Phones","image_url"=>""),array("text"=>"Accessories","image_url"=>"")
 ),
 "destination_a_url"=>(string)$source["destination_a_url"],"destination_b_url"=>(string)$source["destination_a_url"],
 "privacy_url"=>(string)($source["privacy_url"]??""),"terms_url"=>(string)($source["terms_url"]??""),"disclaimer_url"=>(string)($source["disclaimer_url"]??""),
 "noindex"=>1,"active"=>1,"created_at"=>$now,"updated_at"=>$now
);
$items[]=$item;
if(!MGS_Direct_Quiz::save_items($items)){throw new Exception("option_save_failed");}
$sync=MGS_Direct_Quiz::sync_static_pages();if(is_wp_error($sync)){throw new Exception($sync->get_error_message());}
$readback=MGS_Direct_Quiz::find_by_id($item["id"]);if(!$readback||($readback["slug"]??"")!=="sh3-g002"||empty($readback["active"])){throw new Exception("item_readback_failed");}
echo wp_json_encode(array("id"=>$item["id"],"count"=>count($items),"destination"=>$item["destination_a_url"],"logo"=>$item["logo_url"],"sync_count"=>count($sync)),JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root)

version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
static_version=$(sudo -u "$OWNER" wp --path="$WP" option get mgs_direct_quiz_static_version --allow-root)
[[ "$version" == '1.2.0' && "$status" == 'active' && "$static_version" == '1.2.0' ]]
sudo python3 - "$WP" "$SITE" <<'PY'
import json, os, re, sys
wp,site=sys.argv[1:]
path=os.path.join(wp,'quiz','us','sh3-g002','index.html')
assert os.path.isfile(path), path
html=open(path,encoding='utf-8').read()
assert 'MGS Direct Quiz static; plugin=1.2.0' in html
assert html.count('data-mgs-dq-cta') == 7
assert html.count('class="mgs-dq-category"') == 6
assert 'data-mgs-dq-countdown' in html and 'data-mgs-dq-disclaimer-toggle' in html
assert '<form' not in html.lower() and '<input' not in html.lower()
assert f'https://{site}.com/rec-us-app-shein-circle-of-style/' in html
assert 'src="http://' not in html and 'href="http://' not in html
assert html.count('/assets/categories/') == 6
print(json.dumps({'index':path,'bytes':len(html),'sha256':__import__('hashlib').sha256(html.encode()).hexdigest()},separators=(',',':')))
PY
backup_items=$(sudo python3 - "$BACKUP/landings-before.json" <<'PY'
import json,sys
items=json.load(open(sys.argv[1]))
print(len(items))
PY
)
current_items=$(sudo -u "$OWNER" wp --path="$WP" eval 'echo count(MGS_Direct_Quiz::items());' --allow-root)
[[ "$current_items" -eq $((backup_items + 1)) ]]
sudo test -d "$BACKUP/plugin-copy-before"
sudo test -d "$BACKUP/quiz-before"
sudo test -s "$BACKUP/landings-before.json"
MUTATED=0
printf 'SITE=%s\nVERSION=%s\nSTATUS=%s\nSTATIC_VERSION=%s\nPACKAGE_SHA256=%s\nBACKUP_ITEMS=%s\nCURRENT_ITEMS=%s\nBACKUP=%s\nCREATE=%s\n' "$SITE" "$version" "$status" "$static_version" "$actual" "$backup_items" "$current_items" "$BACKUP" "$create_json"
