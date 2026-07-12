<?php
// Local, disposable renderer for the report UI. No WordPress or database access.
define( 'ABSPATH', __DIR__ . '/' );
define( 'ARRAY_A', 'ARRAY_A' );
define( 'DAY_IN_SECONDS', 86400 );
function wp_timezone(){ return new DateTimeZone('America/Sao_Paulo'); }
function sanitize_title($v){ return preg_replace('/[^a-z0-9-]/','',strtolower((string)$v)); }
function sanitize_text_field($v){ return trim((string)$v); }
function esc_html($v){ return htmlspecialchars((string)$v,ENT_QUOTES,'UTF-8'); }
function esc_attr($v){ return htmlspecialchars((string)$v,ENT_QUOTES,'UTF-8'); }
function esc_url($v){ return esc_attr($v); }
function admin_url($v=''){ return 'https://example.test/wp-admin/'.$v; }
function wp_nonce_url($v,$a=''){ return $v.'&_wpnonce=test'; }
function wp_create_nonce($a=''){ return 'test-nonce'; }
function number_format_i18n($n,$d=0){ return number_format((float)$n,$d,',','.'); }
function date_i18n($format,$timestamp){ return date($format,$timestamp); }
function wp_list_pluck($rows,$key){ return array_map(function($r)use($key){return $r[$key]??null;},(array)$rows); }
function selected($a,$b,$echo=true){ $v=((string)$a===(string)$b)?' selected="selected"':''; if($echo)echo $v; return $v; }
function disabled($a,$b=true,$echo=true){ $v=($a===$b)?' disabled="disabled"':''; if($echo)echo $v; return $v; }
class FakeWpdb {
  public $prefix='wp_'; public $options='wp_options'; public $last_error='';
  function prepare($sql,...$args){ return $sql; }
  function esc_like($v){ return $v; }
  function get_var($sql){ return 0; }
  function get_col($sql){ return array(); }
  function get_row($sql,$mode=null){ if(strpos($sql,'mgs_quiz_sms_revenue')!==false)return array('display_revenue_cents'=>0,'revenue_days'=>0,'first_date'=>null,'last_date'=>null,'synced_at'=>null); return null; }
  function get_results($sql,$mode=null){ return array(); }
}
$GLOBALS['wpdb']=new FakeWpdb();
require __DIR__.'/mgs-quiz-carro/includes/class-mgs-quiz-admin.php';
$_GET=array('page'=>'mgs-quiz-report','from'=>'2026-07-01','to'=>'2026-07-10');
?><!doctype html><html><head><meta charset="utf-8"><style>body{font-family:Arial,sans-serif;background:#f0f0f1;padding:20px}.button{display:inline-block;padding:7px 12px}.button-primary{background:#2271b1;color:#fff}.dashicons-calendar-alt:after{content:'📅'}</style></head><body><?php MGS_Quiz_Admin::render_report(); ?></body></html>
