set -euo pipefail
for site in growpowerhub escalatepower; do
ROOT=/home/runcloud/webapps/$site
BACK=/home/runcloud/backups/$site-shein-v2v3-1556503439406534777
PACKAGE="$BACK/mgs-direct-quiz-1.2.1.tar.gz"
printf 'SITE=%s\n' "$site"
sudo test ! -e "$ROOT/wp-content/plugins/mgs-direct-quiz" || { printf 'ABORT plugin appeared\n'; exit 20; }
sudo -u runcloud wp --path="$ROOT" eval 'if(get_option("home")!=="https://'"$site"'.com" || count(get_option("mgs_direct_quiz_landings",array()))!==0){exit(21);}echo "preflight_ok\n";' --allow-root
for model in 2 3; do for n in 001 002 003 004 005 006; do sudo test ! -e "$ROOT/quiz/us/sh$model-g$n" || { printf 'ABORT route exists\n'; exit 22; }; done; done
printf '%s  %s\n' f65cc34407a2684f1eb4e63e5b5259dda4f1d6e6792c3c9c8c680c2cda0fc968 "$PACKAGE" | sudo sha256sum -c -
STAGING="$ROOT/wp-content/plugins/.mgs-direct-quiz-stage-1556503439406534777"
sudo -u runcloud mkdir "$STAGING"
sudo -u runcloud tar -xzf "$PACKAGE" --strip-components=1 -C "$STAGING"
sudo -u runcloud php -l "$STAGING/mgs-direct-quiz.php"
sudo -u runcloud php -l "$STAGING/includes/class-mgs-direct-quiz.php"
sudo -u runcloud php -l "$STAGING/templates/landing.php"
sudo -u runcloud mv "$STAGING" "$ROOT/wp-content/plugins/mgs-direct-quiz"
sudo -u runcloud wp --path="$ROOT" plugin activate mgs-direct-quiz --allow-root
sudo -u runcloud wp --path="$ROOT" plugin get mgs-direct-quiz --format=json --allow-root
sudo -u runcloud wp --path="$ROOT" media import "$BACK/$site-logo-dark-600.png" "$BACK/category-0.webp" "$BACK/category-1.webp" "$BACK/category-2.webp" "$BACK/category-3.webp" "$BACK/category-4.webp" "$BACK/category-5.webp" --porcelain --allow-root | sudo -u runcloud tee "$BACK/media-ids.txt"
sudo -u runcloud wp --path="$ROOT" eval '$ids=array_map("intval",file("/home/runcloud/backups/'"$site"'-shein-v2v3-1556503439406534777/media-ids.txt",FILE_IGNORE_NEW_LINES));$out=array();foreach($ids as $id){$m=wp_get_attachment_metadata($id);$f=get_attached_file($id);$out[]=array("id"=>$id,"url"=>wp_get_attachment_url($id),"meta"=>$m,"bytes"=>filesize($f),"sha256"=>hash_file("sha256",$f));}if(count($out)!==7){exit(23);}file_put_contents("/home/runcloud/backups/'"$site"'-shein-v2v3-1556503439406534777/media.json",wp_json_encode($out));echo "MGSJSON=".wp_json_encode($out);' --allow-root
printf '\n'
done
