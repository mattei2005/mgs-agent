#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
sudo -u "$OWNER" wp --path="$WP" eval '
$items=MGS_Direct_Quiz::items();$out=[];
foreach($items as $x){if(($x["country"]??"")==="us"&&($x["layout_template"]??"")==="lp3"){$cats=[];foreach((array)($x["categories"]??[]) as $c){$cats[]=["text"=>(string)($c["text"]??""),"image_url"=>(string)($c["image_url"]??"")];}$out[]=["manager_code"=>$x["manager_code"],"slug"=>$x["slug"],"categories"=>$cats];}}
usort($out,fn($a,$b)=>$a["manager_code"]<=>$b["manager_code"]);echo wp_json_encode(["v3"=>$out],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root
