<?php
function render_sms_revenue_report( $from, $to, $slug = '' ) {
    $_GET = array(
        'page' => 'mgs-quiz-report', 'from' => $from, 'to' => $to, 'slug' => $slug,
        'leads_per_page' => '5', 'days_per_page' => '5',
    );
    ob_start();
    MGS_Quiz_Admin::render_report();
    return ob_get_clean();
}
function render_default_sms_report() {
    $_GET = array( 'page' => 'mgs-quiz-report', 'leads_per_page' => '5', 'days_per_page' => '5' );
    ob_start();
    MGS_Quiz_Admin::render_report();
    return ob_get_clean();
}

global $wpdb;
$table = $wpdb->prefix . 'mgs_quiz_sms_revenue';
$all = $wpdb->get_row( $wpdb->prepare(
    "SELECT COUNT(*) groups_count, COUNT(DISTINCT revenue_date) dates_count, SUM(net_revenue_cents) display_revenue_cents, MIN(revenue_date) first_date, MAX(revenue_date) last_date FROM {$table} WHERE revenue_date BETWEEN %s AND %s AND publisher = %s AND domain = %s",
    '2026-05-22', '2026-07-09', 'digital-trust_creditoparaveiculo', 'creditoparaveiculo'
), ARRAY_A );
$html = render_sms_revenue_report( '2026-05-22', '2026-07-09' );
$expected = 'R$ ' . number_format( (int) $all['display_revenue_cents'] / 100, 2, ',', '.' );
$checks = array(
    'label' => false !== strpos( $html, 'Receita SMS — Smart Bidding' ),
    'amount' => false !== strpos( $html, esc_html( $expected ) ),
    'coverage' => false !== strpos( $html, esc_html( number_format_i18n( (int) $all['dates_count'] ) . ' dia(s)' ) ),
    'scope_note' => false !== strpos( $html, 'Valor líquido exibido na SB. Cobertura:' ),
    'cost_regression' => false !== strpos( $html, 'Custo estimado de SMS' ),
);
foreach ( $checks as $name => $ok ) {
    if ( ! $ok ) { throw new RuntimeException( 'Revenue report smoke failed: ' . $name ); }
}
$day_html = render_sms_revenue_report( '2026-07-08', '2026-07-08', 'quiz-car-parcelas-g002-qm002' );
$day_cents = (int) $wpdb->get_var( "SELECT COALESCE(SUM(net_revenue_cents),0) FROM {$table} WHERE revenue_date='2026-07-08'" );
$day_expected = 'R$ ' . number_format( $day_cents / 100, 2, ',', '.' );
if ( false === strpos( $day_html, esc_html( $day_expected ) ) || 27457 !== $day_cents || false === strpos( $day_html, 'Não comparável' ) ) {
    throw new RuntimeException( 'Single-day revenue filter mismatch' );
}
$roi_html = render_sms_revenue_report( '2026-07-09', '2026-07-09' );
if ( false === strpos( $roi_html, '65,73%' ) || false === strpos( $roi_html, 'Lucro estimado: R$ 114,42' ) ) {
    throw new RuntimeException( 'ROI calculation mismatch for 2026-07-09' );
}
$empty = render_sms_revenue_report( '2020-01-01', '2020-01-02' );
if ( false === strpos( $empty, 'Não disponível' ) || false === strpos( $empty, 'Sem base' ) ) {
    throw new RuntimeException( 'Empty revenue period state failed' );
}
$yesterday = ( new DateTimeImmutable( 'now', wp_timezone() ) )->modify( '-1 day' )->format( 'Y-m-d' );
$default_html = render_default_sms_report();
if ( false === strpos( $default_html, 'name="from" id="mgsqDateFrom" value="' . esc_attr( $yesterday ) . '"' ) || false === strpos( $default_html, 'name="to" id="mgsqDateTo" value="' . esc_attr( $yesterday ) . '"' ) ) {
    throw new RuntimeException( 'Default report dates are not yesterday' );
}
$calendar_checks = array(
    'trigger' => 'id="mgsqDateRangeTrigger"',
    'popover' => 'id="mgsqDatePopover"',
    'two_months' => 'data-calendar-index="1"',
    'preset_yesterday' => 'data-preset="yesterday"',
    'preset_last_7' => 'data-preset="last7"',
    'preset_last_30' => 'data-preset="last30"',
    'preset_this_month' => 'data-preset="thisMonth"',
    'preset_last_month' => 'data-preset="lastMonth"',
    'cancel' => 'id="mgsqDateCancel"',
    'apply' => 'id="mgsqDateApply"',
);
foreach ( $calendar_checks as $name => $marker ) {
    if ( false === strpos( $default_html, $marker ) ) {
        throw new RuntimeException( 'Calendar UI smoke failed: ' . $name );
    }
}
echo wp_json_encode( array(
    'status' => 'REVENUE_REPORT_SMOKE_OK',
    'groups' => (int) $all['groups_count'],
    'dates' => (int) $all['dates_count'],
    'first_date' => $all['first_date'],
    'last_date' => $all['last_date'],
    'revenue' => $expected,
    'single_day_2026_07_08' => $day_expected,
    'roi_2026_07_09' => '65,73%',
    'default_from_to' => $yesterday,
    'html_bytes' => strlen( $html ),
) ) . PHP_EOL;
