<?php
/** Live report smoke for actual SMS Funnel cost. */
$_GET = array(
    'page' => 'mgs-quiz-report',
    'from' => '2026-09-20',
    'to' => '2026-09-20',
    'leads_per_page' => '5',
    'days_per_page' => '5',
);
global $wpdb;
$cost_t = $wpdb->prefix . 'mgs_quiz_sms_cost';
$revenue_t = $wpdb->prefix . 'mgs_quiz_sms_revenue';
$cost = $wpdb->get_row(
    "SELECT SUM(sms_sent) sms_sent, SUM(cost_cents) cost_cents,
            SUM(CASE WHEN stage=1 THEN sms_sent ELSE 0 END) stage_1_sent,
            SUM(CASE WHEN stage=2 THEN sms_sent ELSE 0 END) stage_2_sent,
            SUM(CASE WHEN stage=3 THEN sms_sent ELSE 0 END) stage_3_sent,
            COUNT(*) records_count
       FROM {$cost_t}
      WHERE cost_date='2026-09-20' AND provider='smsfunnel' AND domain='creditoparaveiculo'",
    ARRAY_A
);
$revenue_cents = (int) $wpdb->get_var(
    "SELECT SUM(net_revenue_cents) FROM {$revenue_t}
      WHERE revenue_date='2026-09-20' AND publisher='digital-trust_creditoparaveiculo' AND domain='creditoparaveiculo'"
);
if ( 36 !== (int) $cost['records_count'] ) {
    throw new RuntimeException( 'Expected 36 SMS cost rows' );
}
ob_start();
MGS_Quiz_Admin::render_report();
$html = ob_get_clean();
$cost_cents = (int) $cost['cost_cents'];
$profit_cents = $revenue_cents - $cost_cents;
$roi = $cost_cents > 0 ? round( ( $profit_cents / $cost_cents ) * 100, 2 ) : null;
$checks = array(
    'sms_label' => false !== strpos( $html, 'SMS enviados' ),
    'cost_label' => false !== strpos( $html, 'Custo real de SMS' ),
    'daily_table' => false !== strpos( $html, 'Custo real de SMS por dia e disparo' ),
    'sent_value' => false !== strpos( $html, esc_html( number_format_i18n( (int) $cost['sms_sent'] ) ) ),
    'cost_value' => false !== strpos( $html, esc_html( 'R$ ' . number_format( $cost_cents / 100, 2, ',', '.' ) ) ),
    'revenue_value' => false !== strpos( $html, esc_html( 'R$ ' . number_format( $revenue_cents / 100, 2, ',', '.' ) ) ),
    'roi_value' => false !== strpos( $html, esc_html( number_format( $roi, 2, ',', '.' ) . '%' ) ),
    'old_cost_per_registration_absent' => false === strpos( $html, 'Custo por registro' ),
    'old_estimated_cost_absent' => false === strpos( $html, 'Custo estimado de SMS' ),
    'source_note' => false !== strpos( $html, 'O custo entra no dia em que cada disparo ocorreu' ),
);
foreach ( $checks as $name => $ok ) {
    if ( ! $ok ) {
        throw new RuntimeException( 'Report smoke failed: ' . $name );
    }
}
echo wp_json_encode( array(
    'status' => 'REPORT_SMS_COST_SMOKE_OK',
    'date' => '2026-09-20',
    'sms_sent' => (int) $cost['sms_sent'],
    'stage_1_sent' => (int) $cost['stage_1_sent'],
    'stage_2_sent' => (int) $cost['stage_2_sent'],
    'stage_3_sent' => (int) $cost['stage_3_sent'],
    'cost_cents' => $cost_cents,
    'revenue_cents' => $revenue_cents,
    'profit_cents' => $profit_cents,
    'roi_percent' => $roi,
    'checks' => $checks,
), JSON_UNESCAPED_SLASHES ) . PHP_EOL;
