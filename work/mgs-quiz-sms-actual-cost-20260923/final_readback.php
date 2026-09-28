<?php
/** Final readback for MGS Quiz actual SMS cost rollout. */
global $wpdb;
$table = $wpdb->prefix . 'mgs_quiz_sms_cost';
$summary = $wpdb->get_row(
    "SELECT COUNT(*) records_count, COUNT(DISTINCT cost_date) days_count,
            MIN(cost_date) first_date, MAX(cost_date) last_date,
            SUM(sms_sent) sms_sent, SUM(cost_cents) cost_cents,
            MIN(unit_cost_cents) min_unit_cost_cents, MAX(unit_cost_cents) max_unit_cost_cents
       FROM {$table}
      WHERE provider='smsfunnel' AND domain='creditoparaveiculo' AND cost_date BETWEEN '2026-08-24' AND '2026-09-22'",
    ARRAY_A
);
$duplicates = (int) $wpdb->get_var(
    "SELECT COUNT(*) FROM (
        SELECT cost_date,provider,vehicle,manager_code,stage,COUNT(*) c
          FROM {$table}
         GROUP BY cost_date,provider,vehicle,manager_code,stage
        HAVING c>1
    ) d"
);
$target = $wpdb->get_row(
    "SELECT COUNT(*) records_count, SUM(sms_sent) sms_sent, SUM(cost_cents) cost_cents,
            SUM(CASE WHEN stage=1 THEN sms_sent ELSE 0 END) stage_1_sent,
            SUM(CASE WHEN stage=2 THEN sms_sent ELSE 0 END) stage_2_sent,
            SUM(CASE WHEN stage=3 THEN sms_sent ELSE 0 END) stage_3_sent
       FROM {$table}
      WHERE cost_date='2026-09-20' AND provider='smsfunnel' AND domain='creditoparaveiculo'",
    ARRAY_A
);
$expected = array(
    'records_count' => 1080,
    'days_count' => 30,
    'first_date' => '2026-08-24',
    'last_date' => '2026-09-22',
    'sms_sent' => 775503,
    'cost_cents' => 6204024,
    'min_unit_cost_cents' => 8,
    'max_unit_cost_cents' => 8,
);
foreach ( $expected as $field => $value ) {
    if ( (string) $summary[ $field ] !== (string) $value ) {
        throw new RuntimeException( "Summary mismatch {$field}: {$summary[$field]}" );
    }
}
$target_expected = array(
    'records_count' => 36,
    'sms_sent' => 48095,
    'cost_cents' => 384760,
    'stage_1_sent' => 22692,
    'stage_2_sent' => 14813,
    'stage_3_sent' => 10590,
);
foreach ( $target_expected as $field => $value ) {
    if ( (string) $target[ $field ] !== (string) $value ) {
        throw new RuntimeException( "Target mismatch {$field}: {$target[$field]}" );
    }
}
if ( 0 !== $duplicates ) {
    throw new RuntimeException( 'Duplicate SMS cost keys found' );
}
echo wp_json_encode( array(
    'status' => 'SMS_COST_FINAL_READBACK_OK',
    'db_version' => get_option( 'mgs_quiz_db_version' ),
    'summary' => array_map( 'intval', array_diff_key( $summary, array( 'first_date' => true, 'last_date' => true ) ) ) + array( 'first_date' => $summary['first_date'], 'last_date' => $summary['last_date'] ),
    'target_2026_09_20' => array_map( 'intval', $target ),
    'duplicates' => $duplicates,
), JSON_UNESCAPED_SLASHES ) . PHP_EOL;
