#!/usr/bin/env bash
set -euo pipefail
SITE_PATH=/home/runcloud/webapps/boostingecon
BACKUP_DIR=/home/runcloud/backups/boostingecon-shein-v2-all-20260923T162942Z
sudo -u runcloud wp --path="$SITE_PATH" option update mgs_direct_quiz_landings "$(<"$BACKUP_DIR/option-before.json")" --format=json --allow-root
sudo -u runcloud wp --path="$SITE_PATH" eval '$r=MGS_Direct_Quiz::sync_static_pages(); if(is_wp_error($r)){fwrite(STDERR,$r->get_error_message()); exit(1);} echo wp_json_encode($r);' --allow-root
sudo -u runcloud wp --path="$SITE_PATH" cache flush --allow-root
