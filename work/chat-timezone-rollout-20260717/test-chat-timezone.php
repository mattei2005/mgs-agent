<?php
if (!defined('ABSPATH')) define('ABSPATH', __DIR__ . '/');
function wp_date($format, $timestamp = null, $timezone = null) {
    if ($timestamp === null) $timestamp = time();
    $dt = (new DateTimeImmutable('@' . $timestamp))->setTimezone($timezone ?: new DateTimeZone('UTC'));
    return $dt->format($format);
}
require '/root/mgs-agent/plugins/mgs-chat-funnels/includes/class-mgs-chat-sms.php';
$checks = array(
    'timezone' => MGS_Chat_SMS::BUSINESS_TIMEZONE,
    'start' => MGS_Chat_SMS::local_date_bound_to_utc('2026-07-15'),
    'end_exclusive' => MGS_Chat_SMS::local_date_bound_to_utc('2026-07-15', true),
    'display' => MGS_Chat_SMS::format_created_at('2026-07-15 03:00:00'),
    'invalid' => MGS_Chat_SMS::local_date_bound_to_utc('2026-02-31'),
);
$expected = array('timezone'=>'America/Sao_Paulo','start'=>'2026-07-15 03:00:00','end_exclusive'=>'2026-07-16 03:00:00','display'=>'15/07/2026, 00:00','invalid'=>'');
if ($checks !== $expected) { fwrite(STDERR, json_encode($checks) . PHP_EOL); exit(1); }
$ref = new ReflectionMethod('MGS_Chat_SMS', 'report_where'); $ref->setAccessible(true);
$params = array();
$filters = array('chat_id'=>'','from'=>'2026-07-15','to'=>'2026-07-15','manager'=>'','q'=>'');
$args = array($filters, &$params); $where = $ref->invokeArgs(null, $args);
if ($params !== array('2026-07-15 03:00:00','2026-07-16 03:00:00') || strpos($where, 'created_at < %s') === false) { fwrite(STDERR, json_encode(array($where,$params)) . PHP_EOL); exit(2); }
echo json_encode(array('ok'=>true,'checks'=>$checks,'where'=>$where,'params'=>$params), JSON_UNESCAPED_SLASHES) . PHP_EOL;
