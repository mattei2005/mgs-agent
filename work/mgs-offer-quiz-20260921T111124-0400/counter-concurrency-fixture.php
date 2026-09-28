<?php
$result = MGS_Offer_Quiz::increment_daily_counter( '2099-12-31' );
if ( is_wp_error( $result ) ) {
    fwrite( STDERR, $result->get_error_message() . "\n" );
    exit( 1 );
}
echo wp_json_encode( $result, JSON_UNESCAPED_SLASHES ) . "\n";
