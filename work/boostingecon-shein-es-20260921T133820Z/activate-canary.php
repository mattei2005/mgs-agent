<?php
$items = MGS_Direct_Quiz::items();
if ( 8 !== count( $items ) ) {
    fwrite( STDERR, "Unexpected config count\n" );
    exit( 50 );
}
$index = null;
foreach ( $items as $i => $item ) {
    if ( ! empty( $item['active'] ) ) {
        fwrite( STDERR, "Expected all configs inactive before canary\n" );
        exit( 51 );
    }
    if ( 'sh1-g002' === ( $item['slug'] ?? '' ) ) {
        $index = $i;
    }
}
if ( null === $index ) {
    fwrite( STDERR, "Canary config not found\n" );
    exit( 52 );
}
$before = $items;
$items[ $index ]['active'] = 1;
$items[ $index ]['updated_at'] = current_time( 'mysql', true );
if ( ! MGS_Direct_Quiz::save_items( $items ) ) {
    fwrite( STDERR, "Option write failed\n" );
    exit( 53 );
}
$result = MGS_Direct_Quiz::sync_static_transition( $before[ $index ], $items[ $index ] );
if ( is_wp_error( $result ) ) {
    MGS_Direct_Quiz::save_items( $before );
    fwrite( STDERR, $result->get_error_message() . "\n" );
    exit( 54 );
}
$readback = MGS_Direct_Quiz::items();
$active = array_values( array_filter( $readback, static function ( $item ) { return ! empty( $item['active'] ); } ) );
if ( 1 !== count( $active ) || 'sh1-g002' !== $active[0]['slug'] || ! is_file( $result['path'] ) || hash_file( 'sha256', $result['path'] ) !== $result['sha256'] ) {
    MGS_Direct_Quiz::unpublish_static_item( $items[ $index ] );
    MGS_Direct_Quiz::save_items( $before );
    fwrite( STDERR, "Canary readback failed\n" );
    exit( 55 );
}
echo wp_json_encode( array(
    'active' => count( $active ),
    'slug' => $active[0]['slug'],
    'path' => $result['path'],
    'sha256' => $result['sha256'],
) );
