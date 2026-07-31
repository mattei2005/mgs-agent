<?php
if ( ! defined( 'ABSPATH' ) ) { exit( 1 ); }
global $wpdb;
$campaign = 'zeus_mock_043_' . gmdate( 'YmdHis' );
$name = 'Zeus Smoke 0.4.3';
$phone = '11999990000';
$table = $wpdb->prefix . 'mgs_chat_leads';
$before = (int) $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$table} WHERE name=%s AND utm_campaign=%s", $name, $campaign ) );
if ( $before !== 0 ) { fwrite( STDERR, "preexisting_test_row\n" ); exit( 2 ); }
add_filter( 'pre_http_request', function( $pre, $args, $url ) {
    $host = strtolower( (string) wp_parse_url( $url, PHP_URL_HOST ) );
    if ( $host === 'v2.smsfunnel.com.br' ) {
        return array(
            'headers' => array( 'content-type' => 'application/json' ),
            'body' => wp_json_encode( array( 'success' => true, 'list_id' => 'mock-g002' ) ),
            'response' => array( 'code' => 200, 'message' => 'OK' ),
            'cookies' => array(),
            'filename' => null,
        );
    }
    return $pre;
}, 10, 3 );
$request = new WP_REST_Request( 'POST', '/mgs-chat/v1/lead' );
$request->set_header( 'content-type', 'application/json' );
$request->set_body( wp_json_encode( array(
    'chat_id' => 'CAR-BR-01-SMS',
    'route' => '/chat-sms/car/br1',
    'name' => $name,
    'phone' => $phone,
    'website' => '',
    'ts' => (int) round( microtime( true ) * 1000 ) - 4000,
    'utm_source' => 'zeus_canary',
    'utm_medium' => 'g002-s',
    'utm_campaign' => $campaign,
    'fbclid' => 'TEST123',
    'extra' => array( 'sms_consent' => 'yes', 'smoke' => 'transactional' ),
) ) );
$response = MGS_Chat_SMS::create_lead( $request );
$data = $response instanceof WP_REST_Response ? $response->get_data() : array();
$status_code = $response instanceof WP_REST_Response ? $response->get_status() : 0;
$lead_id = (int) ( $data['lead_id'] ?? 0 );
$row = $lead_id ? $wpdb->get_row( $wpdb->prepare( "SELECT id,chat_id,manager_code,sms_funnel_status,utm_campaign,extra_params FROM {$table} WHERE id=%d", $lead_id ), ARRAY_A ) : null;
$after_insert = (int) $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$table} WHERE name=%s AND utm_campaign=%s", $name, $campaign ) );
$pass = $status_code === 200 && ! empty( $data['ok'] ) && $after_insert === 1 && is_array( $row ) && $row['chat_id'] === 'CAR-BR-01-SMS' && $row['manager_code'] === 'G002' && $row['sms_funnel_status'] === 'ok:G002' && strpos( (string) $row['extra_params'], 'sms_consent' ) !== false;
if ( $lead_id ) { $wpdb->delete( $table, array( 'id' => $lead_id ), array( '%d' ) ); }
$after_rollback = (int) $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$table} WHERE name=%s AND utm_campaign=%s", $name, $campaign ) );
printf( "http=%d ok=%s before=%d inserted=%d status=%s manager=%s rollback=%d\n", $status_code, ! empty( $data['ok'] ) ? 'true' : 'false', $before, $after_insert, is_array( $row ) ? $row['sms_funnel_status'] : 'missing', is_array( $row ) ? $row['manager_code'] : 'missing', $after_rollback );
if ( ! $pass || $after_rollback !== 0 ) { exit( 3 ); }
