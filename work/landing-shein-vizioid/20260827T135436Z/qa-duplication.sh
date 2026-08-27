#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/vizioid
BACKUP_ROOT=/home/runcloud/backups/vizioid-mgs-direct-quiz-20260827T135436Z
ORIGINAL=$(sudo -u runcloud wp --path="$WP" option get mgs_direct_quiz_landings --format=json --allow-root)
ORIGINAL_HASH=$(sudo -u runcloud wp --path="$WP" eval 'echo hash("sha256",serialize(MGS_Direct_Quiz::items()));' --allow-root)
MUTATED=0
restore() {
  rc=$?
  trap - ERR
  set +e
  if [[ "$MUTATED" == 1 ]]; then
    sudo -u runcloud wp --path="$WP" option update mgs_direct_quiz_landings "$ORIGINAL" --format=json --quiet --allow-root
  fi
  exit "$rc"
}
trap restore ERR

sudo -u runcloud wp --path="$WP" eval '$u=get_users(array("role"=>"administrator","number"=>1,"fields"=>"ID")); if(!$u){WP_CLI::error("admin_missing");} wp_set_current_user($u[0]); $id="vizioid-us-g002-v2"; $_GET["id"]=$id; $_REQUEST["_wpnonce"]=wp_create_nonce("mgs_dq_duplicate_".$id); MGS_Direct_Quiz::handle_duplicate();' --allow-root
MUTATED=1
COPY_READBACK=$(sudo -u runcloud wp --path="$WP" eval '$items=MGS_Direct_Quiz::items(); if(3!==count($items)){WP_CLI::error("count_".count($items));} $copy=null; foreach($items as $item){if(!in_array($item["id"],array("vizioid-us-g002-v2","vizioid-us-g002-v1"),true)){$copy=$item;}} if(!$copy){WP_CLI::error("copy_missing");} if(0!==(int)$copy["active"]||""!==$copy["manager_code"]||""!==$copy["slug"]){WP_CLI::error("copy_safety_mismatch");} if("SHEIN US — G002 — V2 — cópia"!==$copy["name"]||"lp2"!==$copy["layout_template"]){WP_CLI::error("copy_content_mismatch");} echo wp_json_encode(array("id"=>$copy["id"],"name"=>$copy["name"],"manager_code"=>$copy["manager_code"],"slug"=>$copy["slug"],"active"=>(int)$copy["active"],"model"=>$copy["layout_template"]),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);' --allow-root)
sudo -u runcloud wp --path="$WP" option update mgs_direct_quiz_landings "$ORIGINAL" --format=json --quiet --allow-root
MUTATED=0
RESTORED_HASH=$(sudo -u runcloud wp --path="$WP" eval 'echo hash("sha256",serialize(MGS_Direct_Quiz::items()));' --allow-root)
COUNT=$(sudo -u runcloud wp --path="$WP" eval 'echo count(MGS_Direct_Quiz::items());' --allow-root)
[[ "$ORIGINAL_HASH" == "$RESTORED_HASH" ]]
[[ "$COUNT" == "2" ]]
printf 'duplicate_test=pass\ncopy=%s\noriginal_hash=%s\nrestored_hash=%s\nrestored_count=%s\n' "$COPY_READBACK" "$ORIGINAL_HASH" "$RESTORED_HASH" "$COUNT"
