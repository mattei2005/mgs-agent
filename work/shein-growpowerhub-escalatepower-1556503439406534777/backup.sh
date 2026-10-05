set -euo pipefail
TAG=1556503439406534777
for site in growpowerhub escalatepower; do
ROOT=/home/runcloud/webapps/$site
BACK=/home/runcloud/backups/$site-shein-v2v3-$TAG
sudo test ! -e "$BACK" || { printf 'Backup already exists: abort\n'; exit 20; }
sudo mkdir -p "$BACK"
sudo chown runcloud:runcloud "$BACK"
sudo chmod 700 "$BACK"
sudo -u runcloud wp --path="$ROOT" db export "$BACK/database.sql" --allow-root
sudo -u runcloud wp --path="$ROOT" eval '$out=array("home"=>get_option("home"),"option_exists"=>false!==get_option("mgs_direct_quiz_landings",false),"items"=>get_option("mgs_direct_quiz_landings",array()),"active_plugins"=>get_option("active_plugins"),"logo"=>get_theme_mod("custom_logo"),"post"=>get_post(9001,ARRAY_A),"static_version"=>get_option("mgs_direct_quiz_static_version",false));file_put_contents("/home/runcloud/backups/'"$site"'-shein-v2v3-1556503439406534777/runtime.json",wp_json_encode($out));echo "items=".count($out["items"]).chr(10);' --allow-root
if sudo test -d "$ROOT/wp-content/plugins/mgs-direct-quiz"; then sudo cp -a "$ROOT/wp-content/plugins/mgs-direct-quiz" "$BACK/plugin-before"; else printf 'absent\n' | sudo -u runcloud tee "$BACK/plugin-before.state" >/dev/null; fi
if sudo test -d "$ROOT/quiz"; then sudo cp -a "$ROOT/quiz" "$BACK/quiz-before"; else printf 'absent\n' | sudo -u runcloud tee "$BACK/quiz-before.state" >/dev/null; fi
sudo chown -R runcloud:runcloud "$BACK"
sudo -u runcloud chmod 600 "$BACK/database.sql" "$BACK/runtime.json"
sudo -u runcloud sha256sum "$BACK/database.sql" "$BACK/runtime.json"
sudo -u runcloud wp --path="$ROOT" eval '$x=json_decode(file_get_contents("/home/runcloud/backups/'"$site"'-shein-v2v3-1556503439406534777/runtime.json"),true);if(!is_array($x)||$x["home"]!==get_option("home")||$x["post"]["post_content"]!==get_post(9001)->post_content){exit(30);}echo "backup_decode_verified";' --allow-root
printf '\nBACKUP=%s\n' "$BACK"
done
