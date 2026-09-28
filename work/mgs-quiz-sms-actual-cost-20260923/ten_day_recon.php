<?php
/** Read-only 10-day SMS cost/revenue reconciliation. */
global $wpdb;
$cost_t = $wpdb->prefix . 'mgs_quiz_sms_cost';
$revenue_t = $wpdb->prefix . 'mgs_quiz_sms_revenue';
$from = '2026-09-13';
$to = '2026-09-22';
$cost_rows = $wpdb->get_results( $wpdb->prepare(
    "SELECT cost_date d,
            SUM(CASE WHEN stage=1 THEN sms_sent ELSE 0 END) d1,
            SUM(CASE WHEN stage=2 THEN sms_sent ELSE 0 END) d2,
            SUM(CASE WHEN stage=3 THEN sms_sent ELSE 0 END) d3,
            SUM(sms_sent) sent, SUM(cost_cents) cost_cents, COUNT(*) records
       FROM {$cost_t}
      WHERE provider='smsfunnel' AND domain='creditoparaveiculo' AND cost_date BETWEEN %s AND %s
      GROUP BY cost_date ORDER BY cost_date",
    $from, $to
), ARRAY_A );
$revenue_rows = $wpdb->get_results( $wpdb->prepare(
    "SELECT revenue_date d, SUM(net_revenue_cents) revenue_cents, COUNT(*) records
       FROM {$revenue_t}
      WHERE publisher='digital-trust_creditoparaveiculo' AND domain='creditoparaveiculo' AND revenue_date BETWEEN %s AND %s
      GROUP BY revenue_date ORDER BY revenue_date",
    $from, $to
), ARRAY_A );
$revenue = array();
foreach ( $revenue_rows as $row ) { $revenue[ $row['d'] ] = $row; }
$out = array();
foreach ( $cost_rows as $row ) {
    $rev = $revenue[ $row['d'] ] ?? null;
    $cost = (int) $row['cost_cents'];
    $net = $rev ? (int) $rev['revenue_cents'] : null;
    $out[] = array(
        'date' => $row['d'],
        'd1' => (int) $row['d1'],
        'd2' => (int) $row['d2'],
        'd3' => (int) $row['d3'],
        'sms_sent' => (int) $row['sent'],
        'cost_cents' => $cost,
        'cost_records' => (int) $row['records'],
        'revenue_cents' => $net,
        'profit_cents' => null === $net ? null : $net - $cost,
        'roi_percent' => null === $net || $cost <= 0 ? null : round( ( ( $net - $cost ) / $cost ) * 100, 2 ),
        'revenue_records' => $rev ? (int) $rev['records'] : 0,
    );
}
echo wp_json_encode( array(
    'status' => 'TEN_DAY_RECON_OK',
    'from' => $from,
    'to' => $to,
    'cost_days' => count( $cost_rows ),
    'revenue_days' => count( $revenue_rows ),
    'rows' => $out,
), JSON_UNESCAPED_SLASHES ) . PHP_EOL;
