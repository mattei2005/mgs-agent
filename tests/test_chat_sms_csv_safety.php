<?php
// Native class reflection tests, entirely synthetic and without WordPress/DB.
define('ABSPATH', __DIR__);
require $argv[1];
$method = new ReflectionMethod('MGS_Chat_SMS', 'csv_cell');
$checks = array(
    array('ordinary name','ordinary name'),
    array('=SUM(1,2)',"'=SUM(1,2)"),
    array('+5511999999999',"'+5511999999999"),
    array('-1+1',"'-1+1"),
    array('@SUM(1,2)',"'@SUM(1,2)"),
    array("  =SUM(1,2)","'  =SUM(1,2)"),
    array("\t=1+1","'\t=1+1"),
    array("\r=1+1","'\r=1+1"),
    array(42,42),
    array(null,null),
);
foreach ($checks as $case) {
    if ($method->invoke(null,$case[0]) !== $case[1]) {throw new Exception('CSV cell safety mismatch');}
}
echo json_encode(array('pass'=>true,'tests'=>count($checks),'database_writes'=>0,'sms_sent'=>0));
