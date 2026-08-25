<?php
$wpdb = $GLOBALS['wpdb'];
$rows = $wpdb->get_results(
    "SELECT slug, sms_funnel_urls FROM {$wpdb->prefix}mgs_quiz_config WHERE slug REGEXP '^quiz-moto-parcelas-g00[1-6]$' ORDER BY slug"
);
foreach ($rows as $row) {
    $items = json_decode((string) $row->sms_funnel_urls, true);
    if (!is_array($items)) {
        echo $row->slug . " json=invalid\n";
        continue;
    }
    $selected = null;
    foreach ($items as $item) {
        if (!is_array($item)) continue;
        if (!empty($item['default']) && !empty($item['active'])) {
            $selected = $item;
            break;
        }
    }
    if (!$selected) {
        foreach ($items as $item) {
            if (is_array($item) && !empty($item['active'])) {
                $selected = $item;
                break;
            }
        }
    }
    $code = is_array($selected) ? (string) ($selected['gestor_code'] ?? $selected['code'] ?? '') : '';
    $url = is_array($selected) ? (string) ($selected['url'] ?? $selected['sms_funnel_url'] ?? '') : '';
    $host = $url ? (string) parse_url($url, PHP_URL_HOST) : '';
    $path = $url ? (string) parse_url($url, PHP_URL_PATH) : '';
    $valid_endpoint = ($host === 'v2.smsfunnel.com.br' && preg_match('#^/integrations/lists/[^/]+/add-lead$#', $path));
    echo $row->slug
        . " gestor=" . ($code !== '' ? $code : 'blank')
        . " active_rows=" . count(array_filter($items, function($x){ return is_array($x) && !empty($x['active']); }))
        . " endpoint_valid=" . ($valid_endpoint ? '1' : '0')
        . "\n";
}
