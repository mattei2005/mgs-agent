#!/usr/bin/env bash
set -euo pipefail
webroot=/home/runcloud/webapps/dicasfinancas
plugin="$webroot/wp-content/plugins/mgs-offer-quiz"
package=/tmp/mgs-offer-quiz-1.1.0-1551615156017037333.zip
backup=/var/backups/mgs-offer-quiz/20260921T113622-0400-v1.1-pre

old_version=$(sudo -u runcloud wp --path="$webroot" plugin get mgs-offer-quiz --field=version --allow-root)
[[ "$old_version" == "1.0.0" ]]
old_g002=$(sudo sha256sum "$webroot/quiz/quiz-v1-g002/index.html" | awk '{print $1}')

sudo mkdir -p "$backup"
sudo tar -C "$webroot/wp-content/plugins" -czf "$backup/mgs-offer-quiz-1.0.0-production.tar.gz" mgs-offer-quiz
sudo -u runcloud wp --path="$webroot" option get mgs_offer_quiz_items --format=json --allow-root | sudo tee "$backup/option-before-v1.1.json" >/dev/null
sudo tar -C "$webroot/quiz" -czf "$backup/static-g001-g006-before-v1.1.tar.gz" quiz-v1-g001 quiz-v1-g002 quiz-v1-g003 quiz-v1-g004 quiz-v1-g005 quiz-v1-g006
sudo cp "$package" "$backup/"
sudo chown -R runcloud:runcloud "$backup"

sudo -u runcloud wp --path="$webroot" option update mgs_offer_quiz_static_version 1.1.0 --allow-root >/dev/null
sudo -u runcloud wp --path="$webroot" plugin install "$package" --force --activate --allow-root >/dev/null

sudo -u runcloud wp --path="$webroot" eval '
$items = MGS_Offer_Quiz::items();
$benefits = array("Controle pelo aplicativo", "Cartão para o dia a dia", "Conteúdo sem cadastro");
$canary = null;
foreach ($items as &$item) {
    $item["benefits"] = $benefits;
    $item["updated_at"] = current_time("mysql", true);
    if (($item["manager"] ?? "") === "G001") { $canary = $item; }
}
unset($item);
if (!$canary) { fwrite(STDERR, "G001 missing\n"); exit(41); }
MGS_Offer_Quiz::save_items($items);
$result = MGS_Offer_Quiz::publish_static_item($canary);
if (is_wp_error($result)) { fwrite(STDERR, $result->get_error_message()."\n"); exit(42); }
echo wp_json_encode(array("items"=>count($items),"canary"=>$result,"benefits"=>$canary["benefits"]), JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)."\n";
' --allow-root

new_version=$(sudo -u runcloud wp --path="$webroot" plugin get mgs-offer-quiz --field=version --allow-root)
[[ "$new_version" == "1.1.0" ]]
new_g002=$(sudo sha256sum "$webroot/quiz/quiz-v1-g002/index.html" | awk '{print $1}')
[[ "$old_g002" == "$new_g002" ]]

sudo -u runcloud wp --path="$webroot" option get mgs_offer_quiz_items --format=json --allow-root | sudo tee "$backup/option-canary-v1.1.json" >/dev/null
sudo chown runcloud:runcloud "$backup/option-canary-v1.1.json"

echo "backup=$backup"
echo "plugin_version=$new_version"
echo "g002_unchanged=$new_g002"
echo "canary_sha256=$(sudo sha256sum "$webroot/quiz/quiz-v1-g001/index.html" | awk '{print $1}')"
