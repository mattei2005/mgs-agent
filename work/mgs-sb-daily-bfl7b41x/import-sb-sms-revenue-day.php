<?php
/**
 * Transactional one-day Smart Bidding SMS revenue importer.
 * Run with: wp eval-file /tmp/import-sb-sms-revenue-day.php --skip-themes
 */
$input_path = getenv( 'MGS_SB_PAYLOAD_PATH' ) ?: '/tmp/mgs-sb-sms-revenue-day.json';
if ( ! file_exists( $input_path ) ) {
    throw new RuntimeException( 'Daily revenue payload not found' );
}
$payload = json_decode( file_get_contents( $input_path ), true );
if ( ! is_array( $payload ) || empty( $payload['records'] ) || empty( $payload['expected'] ) ) {
    throw new RuntimeException( 'Invalid daily revenue payload' );
}
$target_date = $payload['target_date'] ?? '';
if ( ! preg_match( '/^\d{4}-\d{2}-\d{2}$/', $target_date ) ) {
    throw new RuntimeException( 'Invalid target date' );
}
if ( 'digital-trust_creditoparaveiculo' !== ( $payload['publisher'] ?? '' ) || 'creditoparaveiculo' !== ( $payload['domain'] ?? '' ) ) {
    throw new RuntimeException( 'Unexpected publisher/domain scope' );
}
if ( 'NET_REVENUE' !== ( $payload['metric'] ?? '' ) ) {
    throw new RuntimeException( 'Unexpected revenue metric' );
}

global $wpdb;
$table = $wpdb->prefix . 'mgs_quiz_sms_revenue';
if ( $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $table ) ) !== $table ) {
    throw new RuntimeException( 'Revenue table does not exist' );
}

$wpdb->query( 'START TRANSACTION' );
try {
    foreach ( $payload['records'] as $row ) {
        if ( $target_date !== ( $row['revenue_date'] ?? '' ) ) {
            throw new RuntimeException( 'Row escaped target date' );
        }
        if ( $payload['publisher'] !== ( $row['publisher'] ?? '' ) || $payload['domain'] !== ( $row['domain'] ?? '' ) ) {
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
            "INSERT INTO {$table} (revenue_date,publisher,domain,utm_campaign,currency,discount_revenue_share,revenue_cents,net_revenue_cents,investment_cents,source_rows,source_hash,synced_at)
             VALUES (%s,%s,%s,%s,'BRL',1,%d,%d,%d,%d,%s,UTC_TIMESTAMP())
             ON DUPLICATE KEY UPDATE domain=VALUES(domain),currency='BRL',discount_revenue_share=1,revenue_cents=VALUES(revenue_cents),net_revenue_cents=VALUES(net_revenue_cents),investment_cents=VALUES(investment_cents),source_rows=VALUES(source_rows),source_hash=VALUES(source_hash),synced_at=UTC_TIMESTAMP()",
            $row['revenue_date'], $row['publisher'], $row['domain'], $row['utm_campaign'],
            $row['revenue_cents'], $row['net_revenue_cents'], $row['investment_cents'],
            $row['source_rows'], $row['source_hash']
        );
        if ( false === $wpdb->query( $sql ) ) {
            throw new RuntimeException( 'Upsert failed: ' . $wpdb->last_error );
        }
    }

    $actual = $wpdb->get_row( $wpdb->prepare(
        "SELECT COUNT(*) groups_count, COALESCE(SUM(source_rows),0) source_rows,
                COALESCE(SUM(revenue_cents),0) revenue_cents,
                COALESCE(SUM(net_revenue_cents),0) net_revenue_cents,
                COALESCE(SUM(investment_cents),0) investment_cents
           FROM {$table}
          WHERE revenue_date=%s AND publisher=%s AND domain=%s",
        $target_date, $payload['publisher'], $payload['domain']
    ), ARRAY_A );
    $checks = array(
        'groups' => (int) $actual['groups_count'],
        'source_rows' => (int) $actual['source_rows'],
        'revenue_cents' => (int) $actual['revenue_cents'],
        'net_revenue_cents' => (int) $actual['net_revenue_cents'],
        'investment_cents' => (int) $actual['investment_cents'],
    );
    foreach ( $checks as $field => $value ) {
        if ( (string) $value !== (string) $payload['expected'][ $field ] ) {
            throw new RuntimeException( "Readback mismatch {$field}: expected {$payload['expected'][$field]}, got {$value}" );
        }
    }
    if ( false === $wpdb->query( 'COMMIT' ) ) {
        throw new RuntimeException( 'Commit failed: ' . $wpdb->last_error );
    }
    echo wp_json_encode( array( 'status' => 'DAILY_REVENUE_IMPORT_OK', 'target_date' => $target_date ) + $checks ) . PHP_EOL;
} catch ( Throwable $e ) {
    $wpdb->query( 'ROLLBACK' );
    throw $e;
}
