#!/usr/bin/env bash
set -euo pipefail
webroot=/home/runcloud/webapps/dicasfinancas
package=/tmp/mgs-offer-quiz-1.0.0-1551609844665028611.zip
failed_tar=/tmp/mgs-offer-quiz-1.0.0-1551609844665028611.tar.gz
backup=/var/backups/mgs-offer-quiz/20260921T110529-0400

sudo test ! -d "$webroot/wp-content/plugins/mgs-offer-quiz"
sudo chown runcloud:runcloud "$package"
sudo -u runcloud wp --path="$webroot" plugin install "$package" --activate --allow-root
sudo mv "$package" "$backup/"
sudo chown runcloud:runcloud "$backup/$(basename "$package")"
if test -f "$failed_tar"; then
  sudo mv "$failed_tar" "$backup/"
  sudo chown runcloud:runcloud "$backup/$(basename "$failed_tar")"
fi

sudo -u runcloud wp --path="$webroot" plugin get mgs-offer-quiz --fields=name,status,version --format=json --allow-root
sudo -u runcloud wp --path="$webroot" eval '$items=MGS_Offer_Quiz::items(); echo wp_json_encode(array_map(function($x){return array("manager"=>$x["manager"],"slug"=>$x["slug"],"active"=>(int)$x["active"],"target_url"=>$x["target_url"]);},$items),JSON_UNESCAPED_SLASHES)."\n";' --allow-root

for n in 1 2 3 4 5 6; do
  route="$webroot/quiz/quiz-v1-g00$n/index.html"
  if sudo test -f "$route"; then
    bytes=$(sudo stat -c %s "$route")
    marker=$(sudo grep -c 'MGS Offer Quiz static' "$route" || true)
    printf 'g00%s static=present bytes=%s marker=%s\n' "$n" "$bytes" "$marker"
  else
    printf 'g00%s static=absent\n' "$n"
  fi
done

sudo -u runcloud sha256sum \
  "$webroot/wp-content/plugins/mgs-offer-quiz/mgs-offer-quiz.php" \
  "$webroot/wp-content/plugins/mgs-offer-quiz/includes/class-mgs-offer-quiz.php" \
  "$webroot/wp-content/plugins/mgs-offer-quiz/templates/landing.php" \
  "$webroot/wp-content/plugins/mgs-offer-quiz/README.md" | sha256sum
printf 'package_archived='; sudo test -f "$backup/$(basename "$package")" && echo yes || echo no
