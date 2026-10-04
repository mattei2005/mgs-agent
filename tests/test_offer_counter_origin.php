<?php
define('ABSPATH',__DIR__);
function home_url(){return 'http://dicasfinancas.info';}
function wp_parse_url($url){return parse_url($url);}
class WP_Error {public $code;function __construct($c,$m,$d=array()){$this->code=$c;}}
class WP_REST_Request {private $origin;function __construct($o){$this->origin=$o;}function get_header($k){return $k==='origin'?$this->origin:'';}}
require $argv[1];
$checks=array(
 array('https://dicasfinancas.info',true),array('http://dicasfinancas.info',true),
 array('https://dicasfinancas.info:443',true),array('https://other.invalid',false),
 array('https://dicasfinancas.info.other.invalid',false),array('null',false),
 array('',false),array('https://attacker@dicasfinancas.info',false),
 array('https://dicasfinancas.info/path',false),array('https://dicasfinancas.info:9999',false)
);
foreach($checks as $case){$r=MGS_Offer_Quiz::counter_origin(new WP_REST_Request($case[0]));if(($r===true)!==$case[1])throw new Exception('Origin guard mismatch');}
echo json_encode(array('tests'=>count($checks),'pass'=>true,'counter_writes'=>0,'origin_header_is_not_identity_proof'=>true));
