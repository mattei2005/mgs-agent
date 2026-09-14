<?php
/**
 * Plugin Name: MGS Sequencias SMS
 * Description: Encaminha cliques de SMS por página de veículo, gestor e etapa usando a URL, utm_medium, var_phone e step.
 * Version: 1.2.4
 * Author: MGS Digital Corp
 * Requires at least: 6.0
 * Requires PHP: 7.4
 */
if (!defined('ABSPATH')) { exit; }
const MGS_SMSF_OPTION = 'mgs_sms_funnel_router_options';
const MGS_SMSF_SCHEMA_VERSION = 3;
function mgs_smsf_vehicle_keys() { return array('carro', 'moto'); }
function mgs_smsf_group_keys() { return array('g001', 'g002', 'g003', 'g004', 'g005', 'g006'); }
function mgs_smsf_group_defaults($vehicle, $group) {
    return array('enabled'=>0,'label'=>strtoupper($group),'utm_medium'=>$group.'-s','vehicle'=>$vehicle,'step_01_label'=>'Disparos 2','step_01_webhook'=>'','step_02_label'=>'Disparos 3','step_02_webhook'=>'');
}
function mgs_smsf_vehicle_defaults($vehicle) {
    $groups=array(); foreach(mgs_smsf_group_keys() as $group){$groups[$group]=mgs_smsf_group_defaults($vehicle,$group);} return $groups;
}
function mgs_smsf_defaults() {
    return array('schema_version'=>MGS_SMSF_SCHEMA_VERSION,'enabled'=>0,'vehicles'=>array('carro'=>mgs_smsf_vehicle_defaults('carro'),'moto'=>mgs_smsf_vehicle_defaults('moto')));
}
function mgs_smsf_normalize_group_config($stored,$vehicle,$group) {
    $stored=is_array($stored)?$stored:array(); $normalized=wp_parse_args($stored,mgs_smsf_group_defaults($vehicle,$group));
    $normalized['enabled']=empty($normalized['enabled'])?0:1; $normalized['label']=strtoupper($group); $normalized['utm_medium']=$group.'-s'; $normalized['vehicle']=$vehicle; return $normalized;
}
function mgs_smsf_normalize_saved_options($saved) {
    $defaults=mgs_smsf_defaults(); if(!is_array($saved))return $defaults; $normalized=$defaults; $normalized['enabled']=empty($saved['enabled'])?0:1;
    if(isset($saved['vehicles'])&&is_array($saved['vehicles'])){
        foreach(mgs_smsf_vehicle_keys() as $vehicle){$stored_vehicle=isset($saved['vehicles'][$vehicle])&&is_array($saved['vehicles'][$vehicle])?$saved['vehicles'][$vehicle]:array(); foreach(mgs_smsf_group_keys() as $group){$normalized['vehicles'][$vehicle][$group]=mgs_smsf_normalize_group_config($stored_vehicle[$group]??array(),$vehicle,$group);}} return $normalized;
    }
    if(isset($saved['groups'])&&is_array($saved['groups'])){
        foreach(mgs_smsf_group_keys() as $group){$normalized['vehicles']['carro'][$group]=mgs_smsf_normalize_group_config($saved['groups'][$group]??array(),'carro',$group);} return $normalized;
    }
    $normalized['vehicles']['carro']['g002']['enabled']=$normalized['enabled'];
    $normalized['vehicles']['carro']['g002']['step_01_label']=(string)($saved['step_01_label']??'Disparos 2');
    $normalized['vehicles']['carro']['g002']['step_01_webhook']=(string)($saved['step_01_webhook']??'');
    $normalized['vehicles']['carro']['g002']['step_02_label']=(string)($saved['step_02_label']??'Disparos 3');
    $normalized['vehicles']['carro']['g002']['step_02_webhook']=(string)($saved['step_02_webhook']??''); return $normalized;
}
function mgs_smsf_get_options(){return mgs_smsf_normalize_saved_options(get_option(MGS_SMSF_OPTION,array()));}
function mgs_smsf_migrate_options(){ $saved=get_option(MGS_SMSF_OPTION,array()); if(!is_array($saved)||!isset($saved['vehicles'])||!is_array($saved['vehicles']))update_option(MGS_SMSF_OPTION,mgs_smsf_normalize_saved_options($saved),false); }
add_action('plugins_loaded','mgs_smsf_migrate_options',5);
function mgs_smsf_sanitize_options($input){
    $input=is_array($input)?$input:array(); $options=mgs_smsf_get_options(); $scope=sanitize_key($input['_scope']??'');
    if($scope==='master'){ $options['enabled']=empty($input['enabled'])?0:1; return $options; }
    if(!preg_match('/^route_(carro|moto)_(g00[1-6])$/',$scope,$matches))return $options;
    $vehicle=$matches[1];$group=$matches[2];$route_input=isset($input['vehicles'][$vehicle][$group])&&is_array($input['vehicles'][$vehicle][$group])?$input['vehicles'][$vehicle][$group]:array();
    $options['vehicles'][$vehicle][$group]['enabled']=empty($route_input['enabled'])?0:1;
    $options['vehicles'][$vehicle][$group]['step_01_label']=sanitize_text_field($route_input['step_01_label']??'Disparos 2');
    $options['vehicles'][$vehicle][$group]['step_01_webhook']=esc_url_raw(trim($route_input['step_01_webhook']??''),array('https'));
    $options['vehicles'][$vehicle][$group]['step_02_label']=sanitize_text_field($route_input['step_02_label']??'Disparos 3');
    $options['vehicles'][$vehicle][$group]['step_02_webhook']=esc_url_raw(trim($route_input['step_02_webhook']??''),array('https'));
    $options['schema_version']=MGS_SMSF_SCHEMA_VERSION; return $options;
}
function mgs_smsf_register_settings(){register_setting('mgs_sms_funnel_router',MGS_SMSF_OPTION,array('type'=>'array','sanitize_callback'=>'mgs_smsf_sanitize_options','default'=>mgs_smsf_defaults()));}
add_action('admin_init','mgs_smsf_register_settings');
function mgs_smsf_add_settings_pages(){
    add_menu_page('MGS Sequencias SMS','MGS Sequencias SMS','manage_options','mgs-sms-funnel-router','mgs_smsf_render_overview_page','dashicons-email-alt',30.1);
    add_submenu_page('mgs-sms-funnel-router','MGS Sequencias SMS — Visão geral','Visão geral','manage_options','mgs-sms-funnel-router','mgs_smsf_render_overview_page');
    add_submenu_page('mgs-sms-funnel-router','MGS Sequencias SMS — Carro','Carro','manage_options','mgs-sms-funnel-router-carro','mgs_smsf_render_route_page');
    add_submenu_page('mgs-sms-funnel-router','MGS Sequencias SMS — Moto','Moto','manage_options','mgs-sms-funnel-router-moto','mgs_smsf_render_route_page');
}
add_action('admin_menu','mgs_smsf_add_settings_pages');
function mgs_smsf_route_status($config){$count=(!empty($config['step_01_webhook'])?1:0)+(!empty($config['step_02_webhook'])?1:0);if(!empty($config['enabled'])&&$count===2)return 'Ativo · 2/2';if(!empty($config['enabled'])&&$count===1)return 'Ativo · 1/2';if($count===2)return 'Desativado · 2/2';if($count===1)return 'Incompleto · 1/2';return 'Desativado · 0/2';}
function mgs_smsf_render_overview_page(){
    if(!current_user_can('manage_options'))return;$options=mgs_smsf_get_options();?>
    <div class="wrap"><h1>MGS Sequencias SMS</h1><?php settings_errors(); ?><p>O roteamento usa a página acessada mais <code>utm_medium + step</code> para separar Carro/Moto e G001–G006, sem parâmetro extra de veículo.</p>
    <form method="post" action="options.php"><?php settings_fields('mgs_sms_funnel_router'); ?><input type="hidden" name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[_scope]" value="master"><table class="form-table"><tr><th>Status geral</th><td><label><input type="checkbox" name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[enabled]" value="1" <?php checked(1,(int)$options['enabled']); ?>> Ativar roteador no site</label></td></tr></table><?php submit_button('Salvar status geral'); ?></form>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;max-width:1000px;margin-top:18px;"><?php foreach(mgs_smsf_vehicle_keys() as $vehicle): ?><section style="background:#fff;border:1px solid #dcdcde;border-radius:12px;padding:18px"><h2><?php echo esc_html(ucfirst($vehicle)); ?></h2><p><a class="button button-primary" href="<?php echo esc_url(admin_url('admin.php?page=mgs-sms-funnel-router-'.$vehicle)); ?>">Abrir <?php echo esc_html(ucfirst($vehicle)); ?></a></p><ul><?php foreach(mgs_smsf_group_keys() as $group): ?><li><strong><?php echo esc_html(strtoupper($group)); ?>:</strong> <?php echo esc_html(mgs_smsf_route_status($options['vehicles'][$vehicle][$group])); ?></li><?php endforeach; ?></ul></section><?php endforeach; ?></div></div><?php
}
function mgs_smsf_current_admin_vehicle(){return sanitize_key($_GET['page']??'')==='mgs-sms-funnel-router-moto'?'moto':'carro';}
function mgs_smsf_current_admin_group(){$group=strtolower(sanitize_key($_GET['gestor']??'g001'));return in_array($group,mgs_smsf_group_keys(),true)?$group:'g001';}
function mgs_smsf_render_group_filter($vehicle,$selected_group,$options){
    echo '<nav class="mgs-smsf-group-filter" aria-label="Filtrar por gestor">';foreach(mgs_smsf_group_keys() as $group){$config=$options['vehicles'][$vehicle][$group];$url=add_query_arg(array('page'=>'mgs-sms-funnel-router-'.$vehicle,'gestor'=>$group),admin_url('admin.php'));$class=$group===$selected_group?'button button-primary':'button';$count=(!empty($config['step_01_webhook'])?1:0)+(!empty($config['step_02_webhook'])?1:0);echo '<a class="'.esc_attr($class).'" href="'.esc_url($url).'">'.esc_html(strtoupper($group)).' <span>'.(int)$count.'/2</span></a>';}echo '</nav>';
}
function mgs_smsf_render_route_page(){
    if(!current_user_can('manage_options'))return;$vehicle=mgs_smsf_current_admin_vehicle();$group=mgs_smsf_current_admin_group();$options=mgs_smsf_get_options();$config=$options['vehicles'][$vehicle][$group];$field_base=MGS_SMSF_OPTION.'[vehicles]['.$vehicle.']['.$group.']';?>
    <div class="wrap"><h1>MGS Sequencias SMS — <?php echo esc_html(ucfirst($vehicle)); ?></h1><?php settings_errors(); ?><p>Exibindo somente <strong><?php echo esc_html(ucfirst($vehicle)); ?> · <?php echo esc_html(strtoupper($group)); ?></strong>.</p>
    <style>.mgs-smsf-group-filter{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 20px;padding:12px;background:#fff;border:1px solid #dcdcde;border-radius:12px;max-width:900px}.mgs-smsf-group-filter .button{display:inline-flex;align-items:center;gap:6px}.mgs-smsf-group-filter span{font-size:11px;opacity:.8}@media(max-width:782px){.mgs-smsf-group-filter .button{flex:1 1 calc(33.333% - 8px);justify-content:center}}</style>
    <?php mgs_smsf_render_group_filter($vehicle,$group,$options); ?>
    <form method="post" action="options.php"><?php settings_fields('mgs_sms_funnel_router'); ?><input type="hidden" name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[_scope]" value="route_<?php echo esc_attr($vehicle.'_'.$group); ?>"><table class="form-table"><tr><th>Status</th><td><label><input type="checkbox" name="<?php echo esc_attr($field_base); ?>[enabled]" value="1" <?php checked(1,(int)$config['enabled']); ?>> Ativar <?php echo esc_html(ucfirst($vehicle).' · '.strtoupper($group)); ?></label></td></tr><?php foreach(array('01'=>'Disparos 2','02'=>'Disparos 3') as $step=>$default_label):$key='step_'.$step; ?><tr><th>Step <?php echo esc_html($step); ?></th><td><input type="text" class="regular-text" name="<?php echo esc_attr($field_base); ?>[<?php echo esc_attr($key); ?>_label]" value="<?php echo esc_attr($config[$key.'_label']); ?>"><input type="url" class="large-text code" name="<?php echo esc_attr($field_base); ?>[<?php echo esc_attr($key); ?>_webhook]" value="<?php echo esc_attr($config[$key.'_webhook']); ?>" placeholder="https://..." autocomplete="off"><p class="description">Cole a URL de integração da lista <?php echo esc_html($default_label.' — '.ucfirst($vehicle).' '.strtoupper($group)); ?>.</p></td></tr><?php endforeach; ?></table><?php submit_button('Salvar '.ucfirst($vehicle).' · '.strtoupper($group)); ?></form>
    <hr><h2>Como usar nos links</h2><p><code>utm_medium=<?php echo esc_html($group.'-s'); ?>&amp;step=01</code></p><p><code>utm_medium=<?php echo esc_html($group.'-s'); ?>&amp;step=02</code></p><p><code>step=03</code> permanece sem ação até ser configurada uma futura Lista 4.</p><p>A URL acessada identifica automaticamente <code>carro</code> ou <code>moto</code>; não adicione parâmetro de veículo ao link.</p></div><?php
}
function mgs_smsf_plugin_action_links($links){array_unshift($links,sprintf('<a href="%s">Configurar</a>',esc_url(admin_url('admin.php?page=mgs-sms-funnel-router'))));return $links;}
add_filter('plugin_action_links_'.plugin_basename(__FILE__),'mgs_smsf_plugin_action_links');
function mgs_smsf_normalize_step($raw_step){$raw_step=trim((string)$raw_step);if($raw_step===''||!ctype_digit($raw_step))return '';$number=(int)$raw_step;return($number>=1&&$number<=99)?str_pad((string)$number,2,'0',STR_PAD_LEFT):'';}
function mgs_smsf_normalize_medium($raw_medium){$medium=strtolower(trim((string)$raw_medium));if(!preg_match('/^g00[1-6]-s$/',$medium))return '';return substr($medium,0,4);}
function mgs_smsf_vehicle_from_path($request_uri){$path=strtolower(rtrim((string)wp_parse_url((string)$request_uri,PHP_URL_PATH),'/'));$carro_paths=array('/rec-br-financie-seu-carro-em-60-meses','/rec-br-sem-entrada-mesmo-com-nome-restrito','/rec-br-conquiste-seu-veiculo-mesmo-com-nome-negativado');if(in_array($path,$carro_paths,true))return 'carro';if(preg_match('#(^|[-_/])moto([-_/]|$)#',$path))return 'moto';if(preg_match('#(^|[-_/])car(?:ro)?([-_/]|$)#',$path))return 'carro';return '';}
function mgs_smsf_handle_click(){
    if(is_admin()||wp_doing_ajax()||wp_doing_cron()||!isset($_GET['var_phone'],$_GET['step']))return;
    $phone=preg_replace('/\D+/','',wp_unslash($_GET['var_phone']));$step=mgs_smsf_normalize_step(wp_unslash($_GET['step']));$group=mgs_smsf_normalize_medium(wp_unslash($_GET['utm_medium']??''));$vehicle=mgs_smsf_vehicle_from_path(wp_unslash($_SERVER['REQUEST_URI']??''));
    if($phone===''||strlen($phone)<8||$step===''){header('X-MGS-SMS-Router: invalid-input');return;}if($group===''){header('X-MGS-SMS-Router: invalid-medium');return;}if($vehicle===''){header('X-MGS-SMS-Router: invalid-vehicle');return;}
    $options=mgs_smsf_get_options();if(empty($options['enabled'])){header('X-MGS-SMS-Router: inactive');return;}$route_options=$options['vehicles'][$vehicle][$group]??array();if(empty($route_options['enabled'])){header('X-MGS-SMS-Router: group-inactive');return;}
    $routes=array('01'=>(string)($route_options['step_01_webhook']??''),'02'=>(string)($route_options['step_02_webhook']??''));$webhook=$routes[$step]??'';if($webhook===''){header('X-MGS-SMS-Router: route-not-configured');return;}
    $response=wp_remote_post($webhook,array('timeout'=>5,'redirection'=>0,'headers'=>array('Content-Type'=>'application/json'),'body'=>wp_json_encode(array('name'=>'user','phone'=>$phone)),'data_format'=>'body'));
    if(is_wp_error($response)){header('X-MGS-SMS-Router: delivery-error');return;}$status_code=(int)wp_remote_retrieve_response_code($response);header('X-MGS-SMS-Router: '.(($status_code>=200&&$status_code<300)?'delivered':'delivery-rejected'));
}
add_action('template_redirect','mgs_smsf_handle_click',1);
