<?php
$target = getenv( 'MGS_SB_VERIFY_DATE' ) ?: '2026-07-10';
$_GET = array(
    'page' => 'mgs-quiz-report',
    'from' => $target,
    'to' => $target,
    'slug' => '',
    'gestor' => '',
    'parcela' => '',
    'q' => '',
    'leads_per_page' => '5',
    'days_per_page' => '5',
);
ob_start();
MGS_Quiz_Admin::render_report();
$html = ob_get_clean();
$text = preg_replace( '/\s+/u', ' ', wp_strip_all_tags( html_entity_decode( $html, ENT_QUOTES | ENT_HTML5, 'UTF-8' ) ) );
$checks = array(
    'date_from' => false !== strpos( $html, 'name="from" value="' . esc_attr( $target ) . '"' ),
    'date_to' => false !== strpos( $html, 'name="to" value="' . esc_attr( $target ) . '"' ),
    'revenue' => false !== strpos( $text, 'R$ 346,64' ),
    'cost' => false !== strpos( $text, 'R$ 175,92' ),
    'profit' => false !== strpos( $text, 'Lucro estimado: R$ 170,72' ),
    'roi' => false !== strpos( $text, '97,04%' ),
);
foreach ( $checks as $name => $ok ) {
    if ( ! $ok ) {
        throw new RuntimeException( 'Daily report verification failed: ' . $name );
    }
}
echo wp_json_encode( array( 'status' => 'DAILY_REPORT_VERIFY_OK', 'target_date' => $target ) + $checks ) . PHP_EOL;
