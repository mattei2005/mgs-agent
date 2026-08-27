#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/vizioid
DEPLOY_ID=20260827T135436Z
INBOX="/home/zeus/mgs-deploy-inbox/$DEPLOY_ID"
BACKUP_ROOT="/home/runcloud/backups/vizioid-mgs-direct-quiz-$DEPLOY_ID"
LOGO_INBOX="$INBOX/vizioid-logo-dark-600.png"
LOGO="$BACKUP_ROOT/vizioid-logo-dark-600.png"
OPTION_BACKUP="$BACKUP_ROOT/vizioid-landings-before-dark-logo.json"
EXPECTED_LOGO_SHA="d97dbeabf745934ddcce95c520ca50869ea5dcee66305145f86bb8eb4cebf25e"
ORIGINAL=$(sudo -u runcloud wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root)
MUTATED=0
rollback() {
  rc=$?
  trap - ERR
  set +e
  if [[ "$MUTATED" == 1 ]]; then
    sudo -u runcloud wp --path="$WP" option update mgs_direct_quiz_landings "$ORIGINAL" --format=json --quiet --allow-root
    sudo -u runcloud wp --path="$WP" cache flush --quiet --allow-root
  fi
  exit "$rc"
}
trap rollback ERR

printf '%s' "$ORIGINAL" | sudo -u runcloud tee "$OPTION_BACKUP" >/dev/null
sudo test -s "$OPTION_BACKUP"
if [[ -f "$LOGO_INBOX" ]]; then sudo mv "$LOGO_INBOX" "$LOGO"; fi
sudo test -f "$LOGO"
sudo chown runcloud:runcloud "$LOGO" "$OPTION_BACKUP"
ACTUAL_LOGO_SHA=$(sudo sha256sum "$LOGO" | awk '{print $1}')
[[ "$ACTUAL_LOGO_SHA" == "$EXPECTED_LOGO_SHA" ]]

ATTACHMENT_ID=$(sudo -u runcloud wp --path="$WP" media import "$LOGO" --title='Vizioid — logo escuro landing SHEIN' --alt='Vizioid' --porcelain --allow-root)
[[ "$ATTACHMENT_ID" =~ ^[0-9]+$ ]]
LOGO_URL=$(sudo -u runcloud env MGS_ATTACHMENT_ID="$ATTACHMENT_ID" wp --path="$WP" eval 'echo wp_get_attachment_url((int)getenv("MGS_ATTACHMENT_ID"));' --allow-root)
[[ "$LOGO_URL" == https://vizioid.com/* ]]

MUTATED=1
UPDATE_READBACK=$(sudo -u runcloud env MGS_LOGO_URL="$LOGO_URL" wp --path="$WP" eval '$url=getenv("MGS_LOGO_URL");$items=MGS_Direct_Quiz::items();if(2!==count($items)){WP_CLI::error("count_".count($items));}foreach($items as &$item){$item["logo_url"]=$url;$item["updated_at"]=current_time("mysql",true);}unset($item);MGS_Direct_Quiz::save_items($items);$rb=MGS_Direct_Quiz::items();foreach($rb as $item){if($item["logo_url"]!==$url){WP_CLI::error("logo_readback_".$item["id"]);}}echo wp_json_encode(array("count"=>count($rb),"logo_url"=>$url),JSON_UNESCAPED_SLASHES);' --allow-root)
sudo -u runcloud wp --path="$WP" cache flush --quiet --allow-root || true
sudo -u runcloud wp --path="$WP" eval 'if(function_exists("wpfc_clear_all_cache")){wpfc_clear_all_cache(true);}' --allow-root
META=$(sudo -u runcloud env MGS_ATTACHMENT_ID="$ATTACHMENT_ID" wp --path="$WP" eval '$id=(int)getenv("MGS_ATTACHMENT_ID");$m=wp_get_attachment_metadata($id);echo wp_json_encode(array("id"=>$id,"url"=>wp_get_attachment_url($id),"width"=>(int)($m["width"]??0),"height"=>(int)($m["height"]??0),"alt"=>get_post_meta($id,"_wp_attachment_image_alt",true)),JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);' --allow-root)
MUTATED=0
trap - ERR
sudo mv "$INBOX/deploy-dark-logo.sh" "$BACKUP_ROOT/deploy-dark-logo.sh"
sudo chown runcloud:runcloud "$BACKUP_ROOT/deploy-dark-logo.sh"
printf 'logo_update=success\nlogo_sha256=%s\nattachment=%s\noption_backup=%s\nreadback=%s\n' "$ACTUAL_LOGO_SHA" "$META" "$OPTION_BACKUP" "$UPDATE_READBACK"
