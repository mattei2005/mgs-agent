#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
home=$(sudo -u "$OWNER" wp --path="$WP" option get home --allow-root)
version=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=version --allow-root)
status=$(sudo -u "$OWNER" wp --path="$WP" plugin get mgs-direct-quiz --field=status --allow-root)
printf 'HOME=%s\nVERSION=%s\nSTATUS=%s\n' "$home" "$version" "$status"
sudo -u "$OWNER" wp --path="$WP" eval '
$items=MGS_Direct_Quiz::items();
$out=[];
foreach($items as $x){
 $layout=(string)($x["layout_template"]??"");
 if(($x["country"]??"")==="us" && in_array($layout,["lp1","lp2","lp3"],true)){
  $out[]=["id"=>$x["id"]??null,"name"=>$x["name"]??null,"manager_code"=>$x["manager_code"]??null,"slug"=>$x["slug"]??null,"layout_template"=>$layout,"title"=>$x["title"]??null,"question"=>$x["question"]??null,"active"=>(int)!empty($x["active"]),"destination_a_url"=>$x["destination_a_url"]??null,"updated_at"=>$x["updated_at"]??null];
 }
}
usort($out,function($a,$b){return [$a["layout_template"],$a["manager_code"]]<=>[$b["layout_template"],$b["manager_code"]];});
echo wp_json_encode(["total_items"=>count($items),"target_count"=>count($out),"targets"=>$out],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root
