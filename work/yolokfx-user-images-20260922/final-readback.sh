#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
BACK_HOME=/home/runcloud/backups/yolokfx-v3-home-20260923T031817Z
BACK_PNG=/home/runcloud/backups/yolokfx-v3-user-images-20260923T034439Z
BACK_WEBP=/home/runcloud/backups/yolokfx-v3-optimized-images-20260923T035305Z
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
nginx_state=$(sudo systemctl is-active nginx-rc)
apache_state=$(sudo systemctl is-active apache2-rc)
for back in "$BACK_HOME" "$BACK_PNG" "$BACK_WEBP"; do
  sudo test -d "$back/quiz-before"
  sudo test -s "$back/landings-before.json"
  sudo test -s "$back/landings-after.json"
  sudo test -s "$back/verification.json"
  sudo test -s "$back/SHA256-MANIFEST.json"
done
sudo -u "$OWNER" wp --path="$WP" eval '
$catslug=["women","men","home","shoes","electronics","others"];$labels=["Women","Men","Home","Shoes","Electronics","Others"];$urls=[];$ids=[];$total=0;
foreach($catslug as $i=>$cat){$slug="yolokfx-v3-".$cat."-1552164476814360629";$expected="https://yolokfx.com/wp-content/uploads/2026/09/".$slug.".webp";$id=(int)attachment_url_to_postid($expected);if(!$id){throw new Exception("missing_attachment_".$cat);}$url=wp_get_attachment_url($id);$file=get_attached_file($id);$meta=wp_get_attachment_metadata($id);$alt=get_post_meta($id,"_wp_attachment_image_alt",true);if($url!==$expected||get_post_mime_type($id)!=="image/webp"||!is_file($file)||(int)($meta["width"]??0)!==400||(int)($meta["height"]??0)!==400||$alt!==$labels[$i]||filesize($file)>25000){throw new Exception("attachment_readback_".$cat);}$urls[]=$url;$ids[]=$id;$total+=filesize($file);}
$v3=[];foreach(MGS_Direct_Quiz::items() as $x){if(($x["country"]??"")==="us"&&($x["layout_template"]??"")==="lp3"){$v3[]=$x;}}if(count($v3)!==6){throw new Exception("v3_count");}foreach($v3 as $x){$cats=(array)$x["categories"];if(array_map(fn($c)=>(string)($c["text"]??""),$cats)!==$labels||array_map(fn($c)=>(string)($c["image_url"]??""),$cats)!==$urls||($x["title"]??"")!=="Would you like to receive for free?"){throw new Exception("v3_readback_".($x["slug"]??"unknown"));}}
$custom=get_post(62306);if(!$custom||get_post_status(62306)!=="publish"){throw new Exception("rollback_custom_asset_missing");}
echo wp_json_encode(["items"=>count(MGS_Direct_Quiz::items()),"v3"=>count($v3),"labels"=>$labels,"optimized_attachment_ids"=>$ids,"image_urls"=>$urls,"total_image_bytes"=>$total,"max_image_bytes"=>max(array_map(fn($id)=>filesize(get_attached_file($id)),$ids)),"format"=>"WebP","dimensions"=>"400x400","old_custom_asset_62306_preserved"=>true],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root
printf 'VERSION=%s\nPLUGIN_STATUS=%s\nNGINX=%s\nAPACHE=%s\nBACKUP_HOME=%s\nBACKUP_PNG=%s\nBACKUP_WEBP=%s\n' "$version" "$status" "$nginx_state" "$apache_state" "$BACK_HOME" "$BACK_PNG" "$BACK_WEBP"
