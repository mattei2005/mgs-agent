<?php
/**
 * Transactional smoke for MGS Chat SMS.
 * Intercepts outbound HTTP, inserts one synthetic lead, validates status,
 * deletes the exact inserted row, and verifies the original count is restored.
 */
if (!defined('ABSPATH')) {
    exit(1);
}

if (!class_exists('MGS_Chat_SMS')) {
    fwrite(STDERR, "MGS_Chat_SMS not loaded\n");
    exit(2);
}

global $wpdb;
$table = $wpdb->prefix . 'mgs_chat_leads';
$before = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");

$mock = static function ($preempt, $args, $url) {
    if (is_string($url) && strpos($url, 'v2.smsfunnel.com.br/integrations/lists/') !== false) {
        return array(
            'headers' => array('content-type' => 'application/json'),
            'body' => wp_json_encode(array('success' => true, 'list_id' => 'zeus-transactional-mock')),
            'response' => array('code' => 200, 'message' => 'OK'),
            'cookies' => array(),
            'filename' => null,
        );
    }
    return $preempt;
};
add_filter('pre_http_request', $mock, 999, 3);

$request = new WP_REST_Request('POST', '/mgs-chat/v1/lead');
$request->set_body_params(array(
    'chat_id' => 'CAR-BR-01-SMS',
    'name' => 'Zeus QA Transacional',
    'phone' => '11999990000',
    'ts' => ((int) round(microtime(true) * 1000)) - 5000,
    'website' => '',
    'utm_source' => 'zeusqa',
    'utm_campaign' => 'chat_sms_transactional_smoke',
    'extra' => array('smoke' => 'transactional'),
));
$response = MGS_Chat_SMS::create_lead($request);
remove_filter('pre_http_request', $mock, 999);

$data = $response instanceof WP_REST_Response ? $response->get_data() : rest_ensure_response($response)->get_data();
$lead_id = isset($data['lead_id']) ? (int) $data['lead_id'] : 0;
$inserted_status = $lead_id ? (string) $wpdb->get_var($wpdb->prepare("SELECT sms_funnel_status FROM {$table} WHERE id=%d", $lead_id)) : '';
$deleted = $lead_id ? $wpdb->delete($table, array('id' => $lead_id), array('%d')) : false;
$after = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$table}");
$ok = !empty($data['ok']) && $inserted_status === 'ok:G006' && $deleted === 1 && $before === $after;

$result = array(
    'ok' => $ok,
    'api_ok' => !empty($data['ok']),
    'status' => $inserted_status,
    'row_restored' => ($before === $after),
    'before' => $before,
    'after' => $after,
    'mocked_outbound' => true,
);
echo wp_json_encode($result, JSON_UNESCAPED_SLASHES) . PHP_EOL;
exit($ok ? 0 : 3);
