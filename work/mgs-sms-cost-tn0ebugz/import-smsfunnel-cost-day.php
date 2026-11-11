<?php
/**
 * Transactional one-day importer for actual SMS Funnel send costs.
 * Run with: wp eval-file /var/tmp/mgs-smsfunnel-cost/import-smsfunnel-cost-day.php --skip-themes
 */
$input_path = getenv( 'MGS_SMS_COST_PAYLOAD_PATH' ) ?: '/var/tmp/mgs-smsfunnel-cost/mgs-smsfunnel-cost-day.json';
if ( ! file_exists( $input_path ) ) {
    throw new RuntimeException( 'Daily SMS cost payload not found' );
}
$payload = json_decode( file_get_contents( $input_path ), true );
if ( ! is_array( $payload ) || empty( $payload['records'] ) || empty( $payload['expected'] ) ) {
    throw new RuntimeException( 'Invalid daily SMS cost payload' );
}
$target_date = $payload['target_date'] ?? '';
if ( ! preg_match( '/^\d{4}-\d{2}-\d{2}$/', $target_date ) ) {
    throw new RuntimeException( 'Invalid target date' );
}
if ( 'smsfunnel' !== ( $payload['provider'] ?? '' ) || 'creditoparaveiculo' !== ( $payload['domain'] ?? '' ) ) {
    throw new RuntimeException( 'Unexpected SMS cost scope' );
}
if ( 'America/Sao_Paulo' !== ( $payload['timezone'] ?? '' ) ) {
    throw new RuntimeException( 'Unexpected SMS cost timezone' );
}

$expected_keys = array();
foreach ( array( 'carro', 'moto' ) as $vehicle ) {
    for ( $manager = 1; $manager <= 6; $manager++ ) {
        for ( $stage = 1; $stage <= 3; $stage++ ) {
            $expected_keys[] = $vehicle . '|G' . str_pad( (string) $manager, 3, '0', STR_PAD_LEFT ) . '|' . $stage;
        }
    }
}
sort( $expected_keys );
$actual_keys = array();
foreach ( $payload['records'] as $row ) {
    $actual_keys[] = ( $row['vehicle'] ?? '' ) . '|' . ( $row['manager_code'] ?? '' ) . '|' . (string) ( $row['stage'] ?? '' );
}
sort( $actual_keys );
if ( $actual_keys !== $expected_keys ) {
    throw new RuntimeException( 'SMS cost payload topology mismatch' );
}

global $wpdb;
$table = $wpdb->prefix . 'mgs_quiz_sms_cost';
if ( $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $table ) ) !== $table ) {
    throw new RuntimeException( 'SMS cost table does not exist' );
}

$wpdb->query( 'START TRANSACTION' );
try {
    foreach ( $payload['records'] as $row ) {
        if ( $target_date !== ( $row['cost_date'] ?? '' ) || $payload['provider'] !== ( $row['provider'] ?? '' ) || $payload['domain'] !== ( $row['domain'] ?? '' ) ) {
            throw new RuntimeException( 'SMS cost row escaped target scope' );
        }
        if ( ! in_array( $row['vehicle'] ?? '', array( 'carro', 'moto' ), true ) ) {
            throw new RuntimeException( 'Invalid SMS cost vehicle' );
        }
        if ( ! preg_match( '/^G00[1-6]$/', $row['manager_code'] ?? '' ) || ! in_array( (int) ( $row['stage'] ?? 0 ), array( 1, 2, 3 ), true ) ) {
            throw new RuntimeException( 'Invalid SMS cost manager/stage' );
        }
        if ( ! preg_match( '/^[a-f0-9]{64}$/', $row['source_hash'] ?? '' ) ) {
            throw new RuntimeException( 'Invalid SMS cost source hash' );
        }
        foreach ( array( 'sms_sent', 'unit_cost_cents', 'cost_cents' ) as $field ) {
            if ( ! isset( $row[ $field ] ) || ! is_int( $row[ $field ] ) || $row[ $field ] < 0 ) {
                throw new RuntimeException( 'Invalid SMS cost integer field: ' . $field );
            }
        }
        if ( (int) $row['cost_cents'] !== (int) $row['sms_sent'] * (int) $row['unit_cost_cents'] ) {
            throw new RuntimeException( 'SMS cost arithmetic mismatch' );
        }
        foreach ( array( 'campaign_id', 'campaign_name', 'sequence_id' ) as $field ) {
            if ( '' === trim( (string) ( $row[ $field ] ?? '' ) ) ) {
                throw new RuntimeException( 'Missing SMS cost identity field: ' . $field );
            }
        }
        $sql = $wpdb->prepare(
            "INSERT INTO {$table} (cost_date,provider,domain,vehicle,manager_code,stage,campaign_id,campaign_name,sequence_id,sms_sent,unit_cost_cents,cost_cents,source_hash,synced_at)
             VALUES (%s,%s,%s,%s,%s,%d,%s,%s,%s,%d,%d,%d,%s,UTC_TIMESTAMP())
             ON DUPLICATE KEY UPDATE campaign_id=VALUES(campaign_id),campaign_name=VALUES(campaign_name),sequence_id=VALUES(sequence_id),sms_sent=VALUES(sms_sent),unit_cost_cents=VALUES(unit_cost_cents),cost_cents=VALUES(cost_cents),source_hash=VALUES(source_hash),synced_at=UTC_TIMESTAMP()",
            $row['cost_date'], $row['provider'], $row['domain'], $row['vehicle'], $row['manager_code'], $row['stage'],
            $row['campaign_id'], $row['campaign_name'], $row['sequence_id'], $row['sms_sent'], $row['unit_cost_cents'], $row['cost_cents'], $row['source_hash']
        );
        if ( false === $wpdb->query( $sql ) ) {
            throw new RuntimeException( 'SMS cost upsert failed: ' . $wpdb->last_error );
        }
    }

    $actual = $wpdb->get_row( $wpdb->prepare(
        "SELECT COUNT(*) records_count,
                COALESCE(SUM(sms_sent),0) sms_sent,
                COALESCE(SUM(cost_cents),0) cost_cents,
                COALESCE(MAX(unit_cost_cents),0) unit_cost_cents,
                COALESCE(SUM(CASE WHEN stage=1 THEN sms_sent ELSE 0 END),0) stage_1_sent,
                COALESCE(SUM(CASE WHEN stage=2 THEN sms_sent ELSE 0 END),0) stage_2_sent,
                COALESCE(SUM(CASE WHEN stage=3 THEN sms_sent ELSE 0 END),0) stage_3_sent
           FROM {$table}
          WHERE cost_date=%s AND provider=%s AND domain=%s",
        $target_date, $payload['provider'], $payload['domain']
    ), ARRAY_A );
    $checks = array(
        'records' => (int) $actual['records_count'],
        'sms_sent' => (int) $actual['sms_sent'],
        'cost_cents' => (int) $actual['cost_cents'],
        'unit_cost_cents' => (int) $actual['unit_cost_cents'],
        'stage_1_sent' => (int) $actual['stage_1_sent'],
        'stage_2_sent' => (int) $actual['stage_2_sent'],
        'stage_3_sent' => (int) $actual['stage_3_sent'],
    );
    foreach ( $checks as $field => $value ) {
        if ( (string) $value !== (string) ( $payload['expected'][ $field ] ?? '' ) ) {
            throw new RuntimeException( "SMS cost readback mismatch {$field}: expected {$payload['expected'][$field]}, got {$value}" );
        }
    }
    if ( false === $wpdb->query( 'COMMIT' ) ) {
        throw new RuntimeException( 'SMS cost commit failed: ' . $wpdb->last_error );
    }
    echo wp_json_encode( array( 'status' => 'DAILY_SMS_COST_IMPORT_OK', 'target_date' => $target_date ) + $checks ) . PHP_EOL;
} catch ( Throwable $e ) {
    $wpdb->query( 'ROLLBACK' );
    throw $e;
}
