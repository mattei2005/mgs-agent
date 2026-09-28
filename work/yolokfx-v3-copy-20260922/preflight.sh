#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
printf 'VERSION=%s\nSTATUS=%s\n' "$version" "$status"
sudo -u "$OWNER" wp --path="$WP" eval '
$items=MGS_Direct_Quiz::items();$out=[];
foreach($items as $x){if(($x["country"]??"")==="us"&&($x["layout_template"]??"")==="lp3"){$out[]=["id"=>$x["id"]??null,"manager_code"=>$x["manager_code"]??null,"slug"=>$x["slug"]??null,"title"=>$x["title"]??null,"categories"=>array_map(fn($c)=>(string)($c["text"]??""),(array)($x["categories"]??[])),"active"=>(int)!empty($x["active"])];}}
usort($out,fn($a,$b)=>$a["manager_code"]<=>$b["manager_code"]);
echo wp_json_encode(["total_items"=>count($items),"v3_count"=>count($out),"v3"=>$out],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root
