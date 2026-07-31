<?php
error_reporting(E_ALL);
define('ABSPATH', __DIR__ . '/');
function plugin_dir_path($file){ return dirname($file) . '/'; }
function plugin_dir_url($file){ return 'https://fixture.local/wp-content/plugins/mgs-chat-funnels/'; }
function add_action(...$args){}
function add_shortcode(...$args){}
function wp_json_encode($value,$flags=0){ return json_encode($value,$flags); }
function esc_attr($v){ return htmlspecialchars((string)$v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function esc_html($v){ return htmlspecialchars((string)$v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function esc_url($v){ return filter_var((string)$v, FILTER_VALIDATE_URL) ? (string)$v : ''; }
function esc_url_raw($v){ return esc_url($v); }
function sanitize_text_field($v){ return trim(strip_tags((string)$v)); }
function sanitize_key($v){ return preg_replace('/[^a-z0-9_\-]/','',strtolower((string)$v)); }
function get_locale(){ return 'pt_BR'; }
function rest_url($path=''){ return 'https://fixture.local/wp-json/' . ltrim($path,'/'); }
function home_url($path=''){ return 'https://fixture.local/' . ltrim($path,'/'); }
function wp_doing_ajax(){ return false; }
function is_admin(){ return false; }
function wp_unslash($v){ return $v; }
function untrailingslashit($v){ return rtrim($v,'/'); }
function status_header($v){}
function nocache_headers(){}
function wp_head(){}
function wp_footer(){}
function wp_body_open(){}
function do_action(...$args){}
function wp_enqueue_script(...$args){}
function wp_register_script(...$args){}
function wp_register_style(...$args){}
function wp_enqueue_style(...$args){}
function wp_script_add_data(...$args){}
require __DIR__ . '/mgs-chat-funnels/mgs-chat-funnels.php';
$config_path = $argv[1] ?? (__DIR__ . '/car-br-01-sms.zuout.json');
$config = json_decode(file_get_contents($config_path), true);
$instance = MGS_Chat_Funnels::instance();
$method = new ReflectionMethod(MGS_Chat_Funnels::class, 'render_full_page');
$method->setAccessible(true);
$method->invoke($instance, $config);
