<?php
$site=parse_url(get_option('home'),PHP_URL_HOST);
$site=explode('.',$site)[0];
if(!in_array($site,array('growpowerhub','escalatepower'),true)){exit(10);}
$back='/home/runcloud/backups/'.$site.'-shein-v2v3-1556503439406534777';
$items=json_decode(file_get_contents($back.'/'.$site.'-landings-inactive.json'),true);
$phase=getenv('MGS_PHASE');
$before=MGS_Direct_Quiz::items();
if(count($items)!==12 || MGS_DQ_VERSION!=='1.2.1'){exit(11);}
$routes=array();
foreach($items as &$i){
 if($i['layout_template']!=='lp2' && $i['layout_template']!=='lp3'){exit(12);}
 if($i['language']!=='en' || $i['destination_a_url']!==home_url('/rec-us-app-shein-circle-of-style/') || $i['destination_a_url']!==$i['destination_b_url']){exit(13);}
 $routes[]=$i['slug'];
 if($phase==='canary'){$i['active']=in_array($i['slug'],array('sh2-g001','sh3-g001'),true)?1:0;}
 elseif($phase==='all'){$i['active']=1;}
 elseif($phase!=='inactive'){exit(14);}
}
unset($i);
if(count(array_unique($routes))!==12){exit(15);}
if($phase==='inactive' && count($before)!==0){exit(16);}
if($phase!=='inactive'){
 $baseline=json_decode(file_get_contents($back.'/'.$site.'-landings-inactive.json'),true);
 if(count($before)!==12){exit(17);}
 foreach($before as $k=>$v){$v['active']=0;if($v!==$baseline[$k]){exit(18);}}
}
if(!MGS_Direct_Quiz::save_items($items)){exit(19);}
$sync=MGS_Direct_Quiz::sync_static_pages();
if(is_wp_error($sync)){MGS_Direct_Quiz::save_items($before);fwrite(STDERR,$sync->get_error_message());exit(20);}
$readback=MGS_Direct_Quiz::items();
if($readback!==$items || count($sync)!==count(array_filter($items,function($i){return !empty($i['active']);}))){exit(21);}
file_put_contents($back.'/landings-'.$phase.'-readback.json',wp_json_encode($readback));
echo wp_json_encode(array('site'=>$site,'phase'=>$phase,'count'=>count($readback),'active'=>count($sync),'routes'=>$routes,'static_version'=>get_option(MGS_Direct_Quiz::STATIC_VERSION_OPTION)));
