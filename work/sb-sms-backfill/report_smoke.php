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

global $wpdb;
$table = $wpdb->prefix . 'mgs_quiz_sms_revenue';
$all = $wpdb->get_row( "SELECT COUNT(*) groups_count, COUNT(DISTINCT revenue_date) dates_count, SUM(net_revenue_cents) display_revenue_cents, MIN(revenue_date) first_date, MAX(revenue_date) last_date FROM {$table}", ARRAY_A );
$html = render_sms_revenue_report( '2026-05-22', '2026-07-09' );
$expected = 'R$ ' . number_format( (int) $all['display_revenue_cents'] / 100, 2, ',', '.' );
$checks = array(
    'label' => false !== strpos( $html, 'Receita SMS — Smart Bidding' ),
    'amount' => false !== strpos( $html, esc_html( $expected ) ),
    'coverage' => false !== strpos( $html, esc_html( number_format_i18n( (int) $all['dates_count'] ) . ' dia(s)' ) ),
    'scope_note' => false !== strpos( $html, 'Valor líquido exibido na SB com Discount revenue share' ),
    'cost_regression' => false !== strpos( $html, 'Custo estimado de SMS' ),
);
foreach ( $checks as $name => $ok ) {
    if ( ! $ok ) { throw new RuntimeException( 'Revenue report smoke failed: ' . $name ); }
}
$empty = render_sms_revenue_report( '2020-01-01', '2020-01-02' );
if ( false === strpos( $empty, 'Não disponível' ) || false === strpos( $empty, 'Sem dados' ) ) {
    throw new RuntimeException( 'Empty revenue period state failed' );
}
echo wp_json_encode( array(
    'status' => 'REVENUE_REPORT_SMOKE_OK',
    'groups' => (int) $all['groups_count'],
    'dates' => (int) $all['dates_count'],
    'first_date' => $all['first_date'],
    'last_date' => $all['last_date'],
    'revenue' => $expected,
    'html_bytes' => strlen( $html ),
) ) . PHP_EOL;
