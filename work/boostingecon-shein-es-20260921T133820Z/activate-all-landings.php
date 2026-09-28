<?php
$items = MGS_Direct_Quiz::items();
$expected = array( 'sh1-g002', 'sh2-g002', 'sh3-g001', 'sh3-g002', 'sh3-g003', 'sh3-g004', 'sh3-g005', 'sh3-g006' );
if ( 8 !== count( $items ) || array_map( static function ( $item ) { return $item['slug'] ?? ''; }, $items ) !== $expected ) {
    fwrite( STDERR, "Live config set mismatch\n" );
    exit( 60 );
}
$active_before = array_values( array_filter( $items, static function ( $item ) { return ! empty( $item['active'] ); } ) );
if ( 1 !== count( $active_before ) || 'sh1-g002' !== ( $active_before[0]['slug'] ?? '' ) ) {
    fwrite( STDERR, "Canary state mismatch\n" );
    exit( 61 );
}
$before = $items;
$now = current_time( 'mysql', true );
foreach ( $items as &$item ) {
    $item['active'] = 1;
    $item['updated_at'] = $now;
}
unset( $item );
if ( ! MGS_Direct_Quiz::save_items( $items ) ) {
    fwrite( STDERR, "Option write failed\n" );
    exit( 62 );
}
$results = MGS_Direct_Quiz::sync_static_pages();
if ( is_wp_error( $results ) || 8 !== count( $results ) ) {
    foreach ( $items as $item ) {
        if ( 'sh1-g002' !== ( $item['slug'] ?? '' ) ) {
            MGS_Direct_Quiz::unpublish_static_item( $item );
        }
    }
    MGS_Direct_Quiz::save_items( $before );
    MGS_Direct_Quiz::publish_static_item( $before[0] );
    fwrite( STDERR, is_wp_error( $results ) ? $results->get_error_message() . "\n" : "Unexpected publish count\n" );
    exit( 63 );
}
$readback = MGS_Direct_Quiz::items();
$active = array_values( array_filter( $readback, static function ( $item ) { return ! empty( $item['active'] ); } ) );
if ( 8 !== count( $active ) ) {
    fwrite( STDERR, "Active readback mismatch\n" );
    exit( 64 );
}
$published = array();
foreach ( $results as $result ) {
    if ( ! is_file( $result['path'] ) || hash_file( 'sha256', $result['path'] ) !== $result['sha256'] ) {
        fwrite( STDERR, "Static readback mismatch\n" );
        exit( 65 );
    }
    $published[] = array( 'path' => $result['path'], 'sha256' => $result['sha256'] );
}
echo wp_json_encode( array(
    'count' => count( $readback ),
    'active' => count( $active ),
    'routes' => array_map( static function ( $item ) { return $item['slug']; }, $readback ),
    'published' => $published,
) );
