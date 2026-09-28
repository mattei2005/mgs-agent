#!/usr/bin/env bash
set -euo pipefail
webroot=/home/runcloud/webapps/dicasfinancas
backup=/var/backups/mgs-offer-quiz/20260921T110529-0400

option=$(sudo -u runcloud wp --path="$webroot" option get mgs_offer_quiz_items --format=json --allow-root)
printf '%s\n' "$option" | sudo -u runcloud tee "$backup/option-canary-g001.json" >/dev/null

sudo -u runcloud wp --path="$webroot" eval '
$items = MGS_Offer_Quiz::items();
$allowed = array("G001","G002","G003","G004","G005","G006");
if (count($items) !== 6) { throw new RuntimeException("expected 6 items"); }
foreach ($items as &$item) {
    if (!in_array($item["manager"], $allowed, true)) { throw new RuntimeException("unexpected manager"); }
    $item["active"] = 1;
    $item["updated_at"] = current_time("mysql", true);
}
unset($item);
MGS_Offer_Quiz::save_items($items);
$result = MGS_Offer_Quiz::sync_static_pages();
if (is_wp_error($result)) { throw new RuntimeException($result->get_error_message()); }
echo wp_json_encode(array("published"=>$result,"items"=>array_map(function($x){return array("manager"=>$x["manager"],"slug"=>$x["slug"],"active"=>(int)$x["active"]);},MGS_Offer_Quiz::items())),JSON_UNESCAPED_SLASHES)."\n";
' --allow-root

for n in 1 2 3 4 5 6; do
  route="$webroot/quiz/quiz-v1-g00$n/index.html"
  sudo test -f "$route"
  marker=$(sudo grep -c 'MGS Offer Quiz static' "$route" || true)
  manager=$(sudo grep -c "data-manager=\"G00$n\"" "$route" || true)
  target=$(sudo grep -c 'https://dicasfinancas.info/rec-br-cc-br-cartao-de-credito-superdigital/' "$route" || true)
  forms=$(sudo grep -Eic '<form\b|<input\b' "$route" || true)
  printf 'g00%s marker=%s manager=%s target=%s forms_inputs=%s\n' "$n" "$marker" "$manager" "$target" "$forms"
done
