<?php
$post = get_post( 9001 );
if ( ! $post || 'post' !== $post->post_type || 'publish' !== $post->post_status ) {
    fwrite( STDERR, "Unexpected post state\n" );
    exit( 10 );
}
$needle = '© 2026 Vizioid';
$replacement = '© 2026 Mavroa';
$count = substr_count( $post->post_content, $needle );
if ( 1 !== $count ) {
    fwrite( STDERR, "Expected exactly one source occurrence; got {$count}\n" );
    exit( 11 );
}
$before_hash = hash( 'sha256', $post->post_content );
$after = str_replace( $needle, $replacement, $post->post_content, $replacements );
if ( 1 !== $replacements ) {
    fwrite( STDERR, "Replacement count mismatch\n" );
    exit( 12 );
}
$result = wp_update_post( array( 'ID' => 9001, 'post_content' => $after ), true );
if ( is_wp_error( $result ) || 9001 !== (int) $result ) {
    fwrite( STDERR, is_wp_error( $result ) ? $result->get_error_message() . "\n" : "Unexpected update result\n" );
    exit( 13 );
}
clean_post_cache( 9001 );
$readback = get_post( 9001 );
if ( 0 !== substr_count( $readback->post_content, 'Vizioid' ) || 1 !== substr_count( $readback->post_content, $replacement ) ) {
    fwrite( STDERR, "Readback validation failed\n" );
    exit( 14 );
}
echo wp_json_encode( array(
    'id' => 9001,
    'before_sha256' => $before_hash,
    'after_sha256' => hash( 'sha256', $readback->post_content ),
    'replacement_count' => 1,
    'status' => $readback->post_status,
) );
