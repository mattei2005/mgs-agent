#!/usr/bin/env bash
set -euo pipefail
webroot=/home/runcloud/webapps/dicasfinancas
plugin="$webroot/wp-content/plugins/mgs-offer-quiz"
package=/tmp/mgs-offer-quiz-1.4.0-1551628631002841149.zip
backup=/var/backups/mgs-offer-quiz/20260921T122415-0400-v1.4-pre
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

old_version=$(sudo -u runcloud wp --path="$webroot" plugin get mgs-offer-quiz --field=version --allow-root)
[[ "$old_version" == "1.3.0" ]]
old_g002=$(sudo sha256sum "$webroot/quiz/quiz-v1-g002/index.html" | awk '{print $1}')

sudo mkdir -p "$backup"
sudo chown runcloud:runcloud "$backup"
sudo tar -C "$webroot/wp-content/plugins" -czf "$backup/mgs-offer-quiz-1.3.0-production.tar.gz" mgs-offer-quiz
sudo -u runcloud wp --path="$webroot" option get mgs_offer_quiz_items --format=json --allow-root | sudo tee "$backup/option-before-v1.4.json" >/dev/null
sudo tar -C "$webroot/quiz" -czf "$backup/static-g001-g006-before-v1.4.tar.gz" quiz-v1-g001 quiz-v1-g002 quiz-v1-g003 quiz-v1-g004 quiz-v1-g005 quiz-v1-g006
sudo -u runcloud wp --path="$webroot" db export "$backup/database-before-v1.4.sql" --add-drop-table --allow-root >/dev/null
sudo cp "$package" "$backup/"
sudo chown -R runcloud:runcloud "$backup"

unzip -q "$package" -d "$stage"
test -f "$stage/mgs-offer-quiz/mgs-offer-quiz.php"
sudo -u runcloud wp --path="$webroot" option update mgs_offer_quiz_static_version 1.4.0 --allow-root >/dev/null
sudo rsync -a --delete "$stage/mgs-offer-quiz/" "$plugin/"
sudo chown -R runcloud:runcloud "$plugin"

sudo -u runcloud wp --path="$webroot" eval '
$installed=MGS_Offer_Quiz::install_counter_table();
if(is_wp_error($installed)){fwrite(STDERR,$installed->get_error_message()."\n");exit(40);}
$canary=null;
foreach(MGS_Offer_Quiz::items() as $item){if(($item["manager"]??"")==="G001"){$canary=$item;break;}}
if(!$canary){fwrite(STDERR,"G001 missing\n");exit(41);}
$result=MGS_Offer_Quiz::publish_static_item($canary);
if(is_wp_error($result)){fwrite(STDERR,$result->get_error_message()."\n");exit(42);}
global $wpdb;
$table=$wpdb->prefix."mgs_offer_quiz_daily_views";
$rows=(int)$wpdb->get_var("SELECT COUNT(*) FROM {$table}");
echo wp_json_encode(array("canary"=>$result,"counter_table"=>$table,"rows"=>$rows,"schema"=>get_option("mgs_offer_quiz_counter_schema_version")),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)."\n";
' --allow-root

new_version=$(sudo -u runcloud wp --path="$webroot" plugin get mgs-offer-quiz --field=version --allow-root)
[[ "$new_version" == "1.4.0" ]]
new_g002=$(sudo sha256sum "$webroot/quiz/quiz-v1-g002/index.html" | awk '{print $1}')
[[ "$old_g002" == "$new_g002" ]]
sudo -u runcloud wp --path="$webroot" option get mgs_offer_quiz_items --format=json --allow-root | sudo tee "$backup/option-canary-v1.4.json" >/dev/null
sudo chown runcloud:runcloud "$backup/option-canary-v1.4.json"

echo "backup=$backup"
echo "database_bytes=$(sudo stat -c %s "$backup/database-before-v1.4.sql")"
echo "plugin_version=$new_version"
echo "g002_unchanged=$new_g002"
echo "canary_sha256=$(sudo sha256sum "$webroot/quiz/quiz-v1-g001/index.html" | awk '{print $1}')"
