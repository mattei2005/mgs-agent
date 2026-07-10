<?php
$input_path = '/tmp/historical-creditoparaveiculo-import.json';
if ( ! file_exists( $input_path ) ) {
    throw new RuntimeException( 'Import payload not found' );
}
$payload = json_decode( file_get_contents( $input_path ), true );
if ( ! is_array( $payload ) || empty( $payload['records'] ) || empty( $payload['expected'] ) ) {
    throw new RuntimeException( 'Invalid import payload' );
}
if ( 'digital-trust_creditoparaveiculo' !== $payload['publisher'] || 'creditoparaveiculo' !== $payload['domain'] ) {
    throw new RuntimeException( 'Unexpected publisher/domain scope' );
}

global $wpdb;
$table = $wpdb->prefix . 'mgs_quiz_sms_revenue';
if ( $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $table ) ) !== $table ) {
    throw new RuntimeException( 'Revenue table does not exist' );
}

$expected = $payload['expected'];
$wpdb->query( 'START TRANSACTION' );
try {
    foreach ( $payload['records'] as $row ) {
        if ( ! preg_match( '/^\d{4}-\d{2}-\d{2}$/', $row['revenue_date'] ?? '' ) ) {
            throw new RuntimeException( 'Invalid revenue date' );
        }
        if ( 'digital-trust_creditoparaveiculo' !== ( $row['publisher'] ?? '' ) || 'creditoparaveiculo' !== ( $row['domain'] ?? '' ) ) {
            throw new RuntimeException( 'Row escaped target scope' );
        }
        if ( ! preg_match( '/^[a-f0-9]{64}$/', $row['source_hash'] ?? '' ) ) {
            throw new RuntimeException( 'Invalid source hash' );
        }
        foreach ( array( 'revenue_cents', 'net_revenue_cents', 'investment_cents', 'source_rows' ) as $field ) {
            if ( ! isset( $row[ $field ] ) || ! is_int( $row[ $field ] ) ) {
                throw new RuntimeException( 'Invalid integer field: ' . $field );
            }
        }
        $sql = $wpdb->prepare(
            "INSERT INTO {$table} (revenue_date,publisher,domain,utm_campaign,revenue_cents,net_revenue_cents,investment_cents,source_rows,source_hash,synced_at)
             VALUES (%s,%s,%s,%s,%d,%d,%d,%d,%s,UTC_TIMESTAMP())
             ON DUPLICATE KEY UPDATE domain=VALUES(domain),revenue_cents=VALUES(revenue_cents),net_revenue_cents=VALUES(net_revenue_cents),investment_cents=VALUES(investment_cents),source_rows=VALUES(source_rows),source_hash=VALUES(source_hash),synced_at=UTC_TIMESTAMP()",
            $row['revenue_date'], $row['publisher'], $row['domain'], $row['utm_campaign'],
            $row['revenue_cents'], $row['net_revenue_cents'], $row['investment_cents'],
            $row['source_rows'], $row['source_hash']
        );
        if ( false === $wpdb->query( $sql ) ) {
            throw new RuntimeException( 'Upsert failed: ' . $wpdb->last_error );
        }
    }

    $actual = $wpdb->get_row( $wpdb->prepare(
        "SELECT COUNT(*) groups_count, COALESCE(SUM(source_rows),0) source_rows, COUNT(DISTINCT revenue_date) dates_count,
                MIN(revenue_date) first_date, MAX(revenue_date) last_date,
                COALESCE(SUM(revenue_cents),0) revenue_cents,
                COALESCE(SUM(net_revenue_cents),0) net_revenue_cents,
                COALESCE(SUM(investment_cents),0) investment_cents
           FROM {$table} WHERE publisher=%s AND domain=%s",
        $payload['publisher'], $payload['domain']
    ), ARRAY_A );
    $checks = array(
        'groups' => (int) $actual['groups_count'],
        'source_rows' => (int) $actual['source_rows'],
        'dates' => (int) $actual['dates_count'],
        'first_date' => $actual['first_date'],
        'last_date' => $actual['last_date'],
        'revenue_cents' => (int) $actual['revenue_cents'],
        'net_revenue_cents' => (int) $actual['net_revenue_cents'],
        'investment_cents' => (int) $actual['investment_cents'],
    );
    foreach ( $checks as $field => $value ) {
        if ( (string) $value !== (string) $expected[ $field ] ) {
            throw new RuntimeException( "Readback mismatch {$field}: expected {$expected[$field]}, got {$value}" );
        }
    }
    if ( false === $wpdb->query( 'COMMIT' ) ) {
        throw new RuntimeException( 'Commit failed: ' . $wpdb->last_error );
    }
    echo wp_json_encode( array( 'status' => 'BACKFILL_OK' ) + $checks ) . PHP_EOL;
} catch ( Throwable $e ) {
    $wpdb->query( 'ROLLBACK' );
    throw $e;
}
