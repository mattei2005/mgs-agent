#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
BACK=/home/runcloud/backups/yolokfx-v3-home-20260923T031817Z
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
nginx_state=$(sudo systemctl is-active nginx-rc)
apache_state=$(sudo systemctl is-active apache2-rc)
sudo test -d "$BACK/quiz-before"
sudo test -s "$BACK/landings-before.json"
sudo test -s "$BACK/landings-after.json"
sudo test -s "$BACK/verification.json"
sudo test -s "$BACK/SHA256-MANIFEST.json"
sudo -u "$OWNER" wp --path="$WP" eval '
$url=wp_get_attachment_url(62306);$file=get_attached_file(62306);$meta=wp_get_attachment_metadata(62306);if(!$url||!is_file($file)||hash_file("sha256",$file)!=="fa76c6812a3b3b7f129038b63400285357956d2abf6445d76cc7f4450ad8881f"||(int)($meta["width"]??0)!==600||(int)($meta["height"]??0)!==600){throw new Exception("attachment_readback_failed");}$v3=[];foreach(MGS_Direct_Quiz::items() as $x){if(($x["country"]??"")==="us"&&($x["layout_template"]??"")==="lp3"){$v3[]=$x;}}if(count($v3)!==6){throw new Exception("v3_count");}foreach($v3 as $x){$cats=(array)$x["categories"];if(($cats[2]["text"]??"")!=="Home"||($cats[2]["image_url"]??"")!==$url){throw new Exception("home_".($x["slug"]??"unknown"));}if(($cats[4]["text"]??"")!=="Electronics"||($x["title"]??"")!=="Would you like to receive for free?"){throw new Exception("prior_copy_".($x["slug"]??"unknown"));}}echo wp_json_encode(["items"=>count(MGS_Direct_Quiz::items()),"v3"=>count($v3),"home_readback"=>"PASS","attachment_id"=>62306,"image_url"=>$url,"image_sha256"=>hash_file("sha256",$file)],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root
printf 'VERSION=%s\nPLUGIN_STATUS=%s\nNGINX=%s\nAPACHE=%s\nBACKUP=%s\n' "$version" "$status" "$nginx_state" "$apache_state" "$BACK"
