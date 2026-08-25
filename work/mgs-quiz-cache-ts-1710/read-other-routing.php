<?php
$wpdb = $GLOBALS['wpdb'];
$rows = $wpdb->get_results(
    "SELECT slug, layout_template, redirect_url, sms_funnel_urls, require_sms_success FROM {$wpdb->prefix}mgs_quiz_config WHERE slug NOT REGEXP '^quiz-moto-parcelas-g00[1-6]$' ORDER BY slug"
);
foreach ($rows as $row) {
    $items = json_decode((string) $row->sms_funnel_urls, true);
    $json_ok = is_array($items);
    $selected = null;
    if ($json_ok) {
        foreach ($items as $item) {
            if (is_array($item) && !empty($item['default']) && !empty($item['active'])) { $selected = $item; break; }
        }
        if (!$selected) foreach ($items as $item) {
            if (is_array($item) && !empty($item['active'])) { $selected = $item; break; }
        }
    }
    $code = is_array($selected) ? (string) ($selected['gestor_code'] ?? $selected['code'] ?? '') : '';
    $url = is_array($selected) ? (string) ($selected['url'] ?? $selected['sms_funnel_url'] ?? '') : '';
    $host = $url ? (string) parse_url($url, PHP_URL_HOST) : '';
    $path = $url ? (string) parse_url($url, PHP_URL_PATH) : '';
    $endpoint_ok = ($host === 'v2.smsfunnel.com.br' && preg_match('#^/integrations/lists/[^/]+/add-lead$#', $path));
    $redirect_ok = ((string) $row->redirect_url === 'https://creditoparaveiculo.com/rec-br-financiamento-de-carro-sem-entrada/');
    $active_count = $json_ok ? count(array_filter($items, function($x){ return is_array($x) && !empty($x['active']); })) : 0;
    echo $row->slug
        . " layout=" . ((string)$row->layout_template !== '' ? $row->layout_template : 'default')
        . " gestor=" . ($code !== '' ? $code : 'blank')
        . " active_rows=" . $active_count
        . " endpoint_valid=" . ($endpoint_ok ? '1' : '0')
        . " redirect_valid=" . ($redirect_ok ? '1' : '0')
        . " require_sms=" . intval($row->require_sms_success)
        . "\n";
}
