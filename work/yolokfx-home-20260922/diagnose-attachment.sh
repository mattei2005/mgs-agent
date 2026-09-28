#!/usr/bin/env bash
set -Eeuo pipefail
WP=/home/runcloud/webapps/yolokfx
OWNER=runcloud
sudo -u "$OWNER" env ATTACHMENT_ID=62306 wp --path="$WP" eval '
$id=(int)getenv("ATTACHMENT_ID");$url=wp_get_attachment_url($id);$file=get_attached_file($id);$meta=wp_get_attachment_metadata($id);$alt=get_post_meta($id,"_wp_attachment_image_alt",true);echo wp_json_encode(["id"=>$id,"status"=>get_post_status($id),"mime"=>get_post_mime_type($id),"title"=>get_the_title($id),"url"=>$url,"file"=>$file,"exists"=>is_file($file),"width"=>(int)($meta["width"]??0),"height"=>(int)($meta["height"]??0),"alt"=>$alt,"sha256"=>is_file($file)?hash_file("sha256",$file):null,"bytes"=>is_file($file)?filesize($file):null],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);
' --allow-root
sudo -u "$OWNER" wp --path="$WP" eval '$out=[];foreach(MGS_Direct_Quiz::items() as $x){if(($x["layout_template"]??"")==="lp3"){$out[]=["slug"=>$x["slug"],"text"=>$x["categories"][2]["text"]??null,"image_url"=>$x["categories"][2]["image_url"]??null];}}echo wp_json_encode($out,JSON_UNESCAPED_SLASHES);' --allow-root
