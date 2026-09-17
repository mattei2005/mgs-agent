<?php
$path = '/tmp/mavroa-landings-inactive.json';
if ( ! is_readable( $path ) ) {
    fwrite( STDERR, "Config file is not readable\n" );
    exit( 40 );
}
$items = json_decode( file_get_contents( $path ), true );
if ( ! is_array( $items ) || 8 !== count( $items ) ) {
    fwrite( STDERR, "Expected exactly eight landing configs\n" );
    exit( 41 );
}
$expected = array( 'sh1-g002', 'sh2-g002', 'sh3-g001', 'sh3-g002', 'sh3-g003', 'sh3-g004', 'sh3-g005', 'sh3-g006' );
$routes = array();
foreach ( $items as $item ) {
    $routes[] = (string) ( $item['slug'] ?? '' );
    if ( ! empty( $item['active'] ) || 'es' !== ( $item['language'] ?? '' ) || 'https://mavroa.com/rec-us-app-shein-productos-gratis/' !== ( $item['destination_a_url'] ?? '' ) || ( $item['destination_a_url'] ?? '' ) !== ( $item['destination_b_url'] ?? '' ) ) {
        fwrite( STDERR, "Config preflight failed\n" );
        exit( 42 );
    }
}
if ( $routes !== $expected || count( array_unique( $routes ) ) !== 8 ) {
    fwrite( STDERR, "Route set mismatch\n" );
    exit( 43 );
}
$before = MGS_Direct_Quiz::items();
if ( 0 !== count( $before ) ) {
    fwrite( STDERR, "Live option changed after preflight\n" );
    exit( 44 );
}
if ( ! MGS_Direct_Quiz::save_items( $items ) ) {
    fwrite( STDERR, "Option write failed\n" );
    exit( 45 );
}
$sync = MGS_Direct_Quiz::sync_static_pages();
if ( is_wp_error( $sync ) || array() !== $sync ) {
    MGS_Direct_Quiz::save_items( $before );
    fwrite( STDERR, "Inactive sync failed\n" );
    exit( 46 );
}
$readback = MGS_Direct_Quiz::items();
if ( $readback !== $items ) {
    MGS_Direct_Quiz::save_items( $before );
    fwrite( STDERR, "Option readback mismatch\n" );
    exit( 47 );
}
echo wp_json_encode( array(
    'count' => count( $readback ),
    'active' => count( array_filter( $readback, static function ( $item ) { return ! empty( $item['active'] ); } ) ),
    'routes' => $routes,
    'static_version' => get_option( MGS_Direct_Quiz::STATIC_VERSION_OPTION ),
) );
