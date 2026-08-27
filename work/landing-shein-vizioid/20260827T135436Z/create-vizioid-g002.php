<?php
if ( ! defined( 'ABSPATH' ) ) { exit; }

$existing = get_option( MGS_Direct_Quiz::OPTION, null );
if ( null !== $existing ) {
    WP_CLI::error( 'preexisting_option_detected' );
}

$now = current_time( 'mysql', true );
$common = array(
    'country'           => 'us',
    'manager_code'      => 'G002',
    'logo_url'          => 'https://vizioid.com/wp-content/uploads/2026/08/cropped-Inserir-um-titulo-2.png',
    'title'             => 'Get Free SHEIN Products Delivered to Your Home',
    'question'          => 'Would you like to get free SHEIN products?',
    'option_a_text'     => 'Yes',
    'option_a_icon'     => '',
    'option_b_text'     => 'No',
    'option_b_icon'     => '',
    'destination_a_url'=> 'https://vizioid.com/rec-us-app-shein-circle-of-style/',
    'destination_b_url'=> 'https://vizioid.com/rec-us-app-shein-circle-of-style/',
    'privacy_url'       => 'https://vizioid.com/privacy-policy/',
    'terms_url'         => 'https://vizioid.com/terms-of-service/',
    'disclaimer_url'    => 'https://vizioid.com/disclaimer/',
    'noindex'           => 1,
    'active'            => 1,
    'created_at'        => $now,
    'updated_at'        => $now,
);

$items = array(
    array_merge( $common, array(
        'id'              => 'vizioid-us-g002-v2',
        'name'            => 'SHEIN US — G002 — V2',
        'slug'            => 'sh2-g002',
        'layout_template' => 'lp2',
    ) ),
    array_merge( $common, array(
        'id'              => 'vizioid-us-g002-v1',
        'name'            => 'SHEIN US — G002 — V1',
        'slug'            => 'sh1-g002',
        'layout_template' => 'lp1',
    ) ),
);

if ( ! MGS_Direct_Quiz::save_items( $items ) ) {
    WP_CLI::error( 'option_write_failed' );
}

$readback = MGS_Direct_Quiz::items();
if ( 2 !== count( $readback ) ) {
    WP_CLI::error( 'readback_count_' . count( $readback ) );
}

$expected = array(
    'sh2-g002' => array( 'name' => 'SHEIN US — G002 — V2', 'model' => 'lp2' ),
    'sh1-g002' => array( 'name' => 'SHEIN US — G002 — V1', 'model' => 'lp1' ),
);
$result = array();
foreach ( $readback as $item ) {
    $slug = (string) ( $item['slug'] ?? '' );
    if ( ! isset( $expected[ $slug ] ) ) {
        WP_CLI::error( 'unexpected_slug_' . $slug );
    }
    if ( $expected[ $slug ]['name'] !== ( $item['name'] ?? '' ) || $expected[ $slug ]['model'] !== ( $item['layout_template'] ?? '' ) ) {
        WP_CLI::error( 'landing_mismatch_' . $slug );
    }
    if ( 1 !== (int) ( $item['active'] ?? 0 ) || 1 !== (int) ( $item['noindex'] ?? 0 ) ) {
        WP_CLI::error( 'flags_mismatch_' . $slug );
    }
    if ( $common['destination_a_url'] !== ( $item['destination_a_url'] ?? '' ) || $common['destination_b_url'] !== ( $item['destination_b_url'] ?? '' ) ) {
        WP_CLI::error( 'destination_mismatch_' . $slug );
    }
    $result[] = array(
        'id' => $item['id'],
        'name' => $item['name'],
        'slug' => $slug,
        'model' => 'V' . substr( $item['layout_template'], 2 ),
        'active' => (int) $item['active'],
        'noindex' => (int) $item['noindex'],
    );
}

WP_CLI::log( wp_json_encode( $result, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
