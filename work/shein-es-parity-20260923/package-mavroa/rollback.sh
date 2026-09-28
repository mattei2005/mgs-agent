#!/usr/bin/env bash
set -euo pipefail
SITE_PATH=/home/runcloud/webapps/mavroa
BACKUP_DIR=/home/runcloud/backups/mavroa-shein-parity-20260923T154752Z
sudo -u runcloud wp --path="$SITE_PATH" option update mgs_direct_quiz_landings "$(<"$BACKUP_DIR/option-before.json")" --format=json --allow-root
sudo -u runcloud wp --path="$SITE_PATH" eval '$content=file_get_contents("/home/runcloud/backups/mavroa-shein-parity-20260923T154752Z/post-9001-before.html"); $result=wp_update_post(array("ID"=>9001,"post_content"=>$content),true); if(is_wp_error($result)){fwrite(STDERR,$result->get_error_message()); exit(1);} echo $result;' --allow-root
sudo -u runcloud wp --path="$SITE_PATH" eval '$r=MGS_Direct_Quiz::sync_static_pages(); if(is_wp_error($r)){fwrite(STDERR,$r->get_error_message()); exit(1);} echo wp_json_encode($r);' --allow-root
sudo -u runcloud wp --path="$SITE_PATH" cache flush --allow-root
