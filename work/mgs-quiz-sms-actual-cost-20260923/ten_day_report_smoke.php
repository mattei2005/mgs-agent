<?php
/** Render smoke for the refreshed 10-day SMS window. */
$_GET = array(
    'page' => 'mgs-quiz-report',
    'from' => '2026-09-13',
    'to' => '2026-09-22',
    'leads_per_page' => '5',
    'days_per_page' => '5',
);
global $wpdb;
$cost_t = $wpdb->prefix . 'mgs_quiz_sms_cost';
$revenue_t = $wpdb->prefix . 'mgs_quiz_sms_revenue';
$cost = $wpdb->get_row(
    "SELECT SUM(sms_sent) sms_sent, SUM(cost_cents) cost_cents, COUNT(DISTINCT cost_date) days_count
       FROM {$cost_t} WHERE provider='smsfunnel' AND domain='creditoparaveiculo' AND cost_date BETWEEN '2026-09-13' AND '2026-09-22'",
    ARRAY_A
);
$revenue = (int) $wpdb->get_var(
    "SELECT SUM(net_revenue_cents) FROM {$revenue_t} WHERE publisher='digital-trust_creditoparaveiculo' AND domain='creditoparaveiculo' AND revenue_date BETWEEN '2026-09-13' AND '2026-09-22'"
);
$profit = $revenue - (int) $cost['cost_cents'];
$roi = round( ( $profit / (int) $cost['cost_cents'] ) * 100, 2 );
ob_start();
MGS_Quiz_Admin::render_report();
$html = ob_get_clean();
$checks = array(
    'sent' => false !== strpos( $html, esc_html( number_format_i18n( (int) $cost['sms_sent'] ) ) ),
    'cost' => false !== strpos( $html, esc_html( 'R$ ' . number_format( (int) $cost['cost_cents'] / 100, 2, ',', '.' ) ) ),
    'revenue' => false !== strpos( $html, esc_html( 'R$ ' . number_format( $revenue / 100, 2, ',', '.' ) ) ),
    'roi' => false !== strpos( $html, esc_html( number_format( $roi, 2, ',', '.' ) . '%' ) ),
    'coverage' => false !== strpos( $html, '10 dia(s), 13/09/2026 a 22/09/2026' ),
    'latest_date' => false !== strpos( $html, '22/09/2026' ),
    'old_estimate_absent' => false === strpos( $html, 'Custo estimado de SMS' ),
);
foreach ( $checks as $name => $ok ) {
    if ( ! $ok ) { throw new RuntimeException( '10-day report smoke failed: ' . $name ); }
}
echo wp_json_encode( array(
    'status' => 'TEN_DAY_REPORT_SMOKE_OK',
    'days' => (int) $cost['days_count'],
    'sms_sent' => (int) $cost['sms_sent'],
    'cost_cents' => (int) $cost['cost_cents'],
    'revenue_cents' => $revenue,
    'profit_cents' => $profit,
    'roi_percent' => $roi,
    'checks' => $checks,
), JSON_UNESCAPED_SLASHES ) . PHP_EOL;
