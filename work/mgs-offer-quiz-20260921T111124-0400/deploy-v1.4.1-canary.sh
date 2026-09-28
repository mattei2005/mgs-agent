#!/usr/bin/env bash
set -euo pipefail
webroot=/home/runcloud/webapps/dicasfinancas
plugin="$webroot/wp-content/plugins/mgs-offer-quiz"
package=/tmp/mgs-offer-quiz-1.4.1-1551662963591749692.zip
backup=/var/backups/mgs-offer-quiz/20260921T143832-0400-v1.4.1-pre
stage=$(mktemp -d /tmp/mgs-offer-quiz-v1.4.1-stage.XXXXXX)
cleanup(){ rm -rf "$stage"; }
trap cleanup EXIT

test "$(sudo -u runcloud wp --path="$webroot" plugin get mgs-offer-quiz --field=version --allow-root)" = "1.4.0"
sudo install -d -o runcloud -g runcloud -m 0750 "$backup"
sudo tar -C "$webroot/wp-content/plugins" -czf "$backup/mgs-offer-quiz-1.4.0-production.tar.gz" mgs-offer-quiz
sudo tar -C "$webroot" -czf "$backup/static-g001-g006-before-v1.4.1.tar.gz" quiz/quiz-v1-g001 quiz/quiz-v1-g002 quiz/quiz-v1-g003 quiz/quiz-v1-g004 quiz/quiz-v1-g005 quiz/quiz-v1-g006
sudo -u runcloud wp --path="$webroot" option get mgs_offer_quiz_items --format=json --allow-root | sudo tee "$backup/option-before-v1.4.1.json" >/dev/null
sudo -u runcloud wp --path="$webroot" option get mgs_offer_quiz_static_version --allow-root | sudo tee "$backup/static-version-before-v1.4.1.txt" >/dev/null
sudo -u runcloud wp --path="$webroot" db export "$backup/database-before-v1.4.1.sql" --add-drop-table --allow-root >/dev/null
sudo cp "$package" "$backup/"
sudo chown -R runcloud:runcloud "$backup"

sudo -u runcloud wp --path="$webroot" option update mgs_offer_quiz_static_version 1.4.1 --allow-root >/dev/null
unzip -q "$package" -d "$stage"
sudo rsync -a --delete "$stage/mgs-offer-quiz/" "$plugin/"
sudo chown -R runcloud:runcloud "$plugin"
sudo chmod -R u=rwX,go=rX "$plugin"

test "$(sudo -u runcloud wp --path="$webroot" plugin get mgs-offer-quiz --field=version --allow-root)" = "1.4.1"
sudo -u runcloud wp --path="$webroot" eval '$items=MGS_Offer_Quiz::items();$updated=array();foreach($items as &$item){if(($item["manager"]??"")==="G001"){$item["target_url"]="https://dicasfinancas.info/rec-br-cc-cartao-de-credito-nubank/";$updated=$item;}}unset($item);MGS_Offer_Quiz::save_items($items);$result=MGS_Offer_Quiz::publish_static_item($updated);if(is_wp_error($result)){fwrite(STDERR,$result->get_error_message()."\n");exit(41);}echo wp_json_encode($result,JSON_UNESCAPED_SLASHES)."\n";' --allow-root
sudo -u runcloud wp --path="$webroot" option get mgs_offer_quiz_items --format=json --allow-root | sudo tee "$backup/option-canary-v1.4.1.json" >/dev/null

sudo -u runcloud python3 -c 'from pathlib import Path; import json,re
rows=[]
for n in (1,2):
 p=Path(f"/home/runcloud/webapps/dicasfinancas/quiz/quiz-v1-g{n:03d}/index.html")
 t=p.read_text(encoding="utf-8")
 m=re.search(r"var target\s*=\s*(\".*?\");",t)
 rows.append({"g":n,"target":json.loads(m.group(1)) if m else None,"v141":"plugin=1.4.1" in t,"v140":"plugin=1.4.0" in t})
print(json.dumps(rows,separators=(",",":")))'

sudo -u runcloud wp --path="$webroot" plugin get mgs-offer-quiz --fields=status,version --format=json --allow-root
sudo du -b "$backup/database-before-v1.4.1.sql"
