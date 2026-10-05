<?php
$site=explode('.',parse_url(get_option('home'),PHP_URL_HOST))[0];
$back='/home/runcloud/backups/'.$site.'-shein-v2v3-1556503439406534777';
$before=json_decode(file_get_contents($back.'/runtime.json'),true);
$expected=json_decode(file_get_contents($back.'/'.$site.'-landings-inactive.json'),true);
foreach($expected as &$i){$i['active']=1;}unset($i);
$items=MGS_Direct_Quiz::items();
if($items!==$expected || count($items)!==12){exit(10);}
if(get_post(9001,ARRAY_A)!==$before['post'] || get_theme_mod('custom_logo')!==$before['logo']){exit(11);}
$active=get_option('active_plugins');$wanted=$before['active_plugins'];$wanted[]='mgs-direct-quiz/mgs-direct-quiz.php';sort($wanted);sort($active);if($wanted!==$active){exit(12);}
$manifest=array();$root=WP_PLUGIN_DIR.'/mgs-direct-quiz';
$itr=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS));
foreach($itr as $f){if($f->isFile()){$manifest[substr($f->getPathname(),strlen($root)+1)]=hash_file('sha256',$f->getPathname());}}
ksort($manifest);
$physical=array();
foreach($items as $i){$f=ABSPATH.'quiz/us/'.$i['slug'].'/index.html';$html=file_get_contents($f);if(strpos($html,'MGS Direct Quiz static')===false || strpos($html,'http://')!==false || strpos($html,'wp-includes')!==false || strpos($html,'<form')!==false || strpos($html,'<input')!==false){exit(13);}$physical[$i['slug']]=array('sha256'=>hash_file('sha256',$f),'bytes'=>filesize($f));}
foreach(array('sh1-g001','sh1-g002','sh1-g003','sh1-g004','sh1-g005','sh1-g006') as $slug){if(file_exists(ABSPATH.'quiz/us/'.$slug)){exit(14);}}
$admins=get_users(array('role'=>'administrator','number'=>1));if(!$admins){exit(15);}wp_set_current_user($admins[0]->ID);
ob_start();MGS_Direct_Quiz::render_list();$list=ob_get_clean();
ob_start();$_GET['id']=$items[0]['id'];MGS_Direct_Quiz::render_edit();$edit=ob_get_clean();
if(strpos($list,'Nova landing')===false || strpos($list,'Duplicar')===false || strpos($list,'Editar')===false || strpos($edit,'Escolher na Biblioteca de Mídia')===false){exit(16);}
if(substr_count($list,'mgs-dq-landing-cell')!==12){exit(17);}
$roles=array('create'=>strpos($list,'Nova landing')!==false,'edit'=>strpos($list,'Editar')!==false,'duplicate'=>strpos($list,'Duplicar')!==false,'list_rows'=>12,'media_picker'=>strpos($edit,'Escolher na Biblioteca de Mídia')!==false);
echo 'MGSJSON='.wp_json_encode(array('site'=>$site,'items'=>$items,'plugin_version'=>MGS_DQ_VERSION,'manifest'=>$manifest,'static'=>$physical,'rec_unchanged'=>true,'official_logo_unchanged'=>true,'previous_plugins_unchanged'=>true,'v1_absent'=>true,'admin'=>$roles,'backup'=>array('database_bytes'=>filesize($back.'/database.sql'),'runtime_sha256'=>hash_file('sha256',$back.'/runtime.json'),'rollback_exists'=>is_file($back.'/rollback.sh'))));
