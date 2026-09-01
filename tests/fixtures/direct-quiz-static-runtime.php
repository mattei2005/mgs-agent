<?php
if ( $argc < 2 ) {
    fwrite( STDERR, "fixture root required\n" );
    exit( 2 );
}
$root = rtrim( $argv[1], '/' ) . '/';
define( 'ABSPATH', $root );
define( 'MGS_DQ_PATH', '/root/mgs-agent/plugins/mgs-direct-quiz/' );
define( 'MGS_DQ_URL', 'https://example.test/wp-content/plugins/mgs-direct-quiz/' );
define( 'MGS_DQ_VERSION', '1.1.0' );

class WP_Error {
    private $code;
    private $message;
    public function __construct( $code, $message ) { $this->code = $code; $this->message = $message; }
    public function get_error_code() { return $this->code; }
    public function get_error_message() { return $this->message; }
}
function is_wp_error( $value ) { return $value instanceof WP_Error; }
function sanitize_key( $value ) { return strtolower( preg_replace( '/[^a-z0-9_\-]/', '', (string) $value ) ); }
function sanitize_title( $value ) { return strtolower( trim( preg_replace( '/[^a-zA-Z0-9\-]+/', '-', (string) $value ), '-' ) ); }
function trailingslashit( $value ) { return rtrim( (string) $value, '/\\' ) . '/'; }
function wp_json_encode( $value, $flags = 0 ) { return json_encode( $value, $flags ); }
function wp_mkdir_p( $path ) { return is_dir( $path ) || mkdir( $path, 0755, true ); }
function wp_generate_uuid4() { static $i = 0; $i++; return sprintf( '00000000-0000-4000-8000-%012d', $i ); }
function esc_attr( $value ) { return htmlspecialchars( (string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8' ); }
function esc_html( $value ) { return htmlspecialchars( (string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8' ); }
function esc_url( $value ) { return htmlspecialchars( (string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8' ); }
function update_option( $key, $value, $autoload = null ) { $GLOBALS['fixture_options'][ $key ] = $value; return true; }
function get_option( $key, $default = false ) { return $GLOBALS['fixture_options'][ $key ] ?? $default; }

require MGS_DQ_PATH . 'includes/class-mgs-direct-quiz.php';

$base = array(
    'id' => 'fixture-g002-v2',
    'name' => 'SHEIN US — G002 — V2',
    'country' => 'us',
    'manager_code' => 'G002',
    'slug' => 'sh2-g002',
    'layout_template' => 'lp2',
    'logo_url' => 'https://example.test/logo.png',
    'title' => 'Original title',
    'question' => 'Would you like to get free products?',
    'option_a_text' => 'Yes',
    'option_a_icon' => '',
    'option_b_text' => 'No',
    'option_b_icon' => '',
    'destination_a_url' => 'https://example.test/rec/?utm_source=fixed',
    'destination_b_url' => 'https://example.test/rec/?utm_source=fixed',
    'privacy_url' => 'https://example.test/privacy/',
    'terms_url' => 'https://example.test/terms/',
    'disclaimer_url' => 'https://example.test/disclaimer/',
    'noindex' => 1,
    'active' => 1,
);

$first = MGS_Direct_Quiz::publish_static_item( $base );
if ( is_wp_error( $first ) ) { throw new RuntimeException( $first->get_error_message() ); }
$index = $first['path'];
$html1 = file_get_contents( $index );

$edited = $base;
$edited['title'] = 'Edited title';
$second = MGS_Direct_Quiz::sync_static_transition( $base, $edited );
if ( is_wp_error( $second ) ) { throw new RuntimeException( $second->get_error_message() ); }
$html2 = file_get_contents( $index );

$route_changed = $edited;
$route_changed['slug'] = 'sh2-g003';
$route_guard = MGS_Direct_Quiz::sync_static_transition( $edited, $route_changed );

$inactive = $edited;
$inactive['active'] = 0;
$off = MGS_Direct_Quiz::sync_static_transition( $edited, $inactive );
if ( is_wp_error( $off ) ) { throw new RuntimeException( $off->get_error_message() ); }
$inactive_removed_public_path = ! is_dir( dirname( $index ) ) && ! is_file( $index );

$copy = $base;
$copy['id'] = 'copy';
$copy['slug'] = 'sh2-g004';
$copy['manager_code'] = 'G004';
$copy['active'] = 0;
$copy_result = MGS_Direct_Quiz::sync_static_transition( null, $copy );
$copy_path = MGS_Direct_Quiz::static_index_path( $copy );

$reactivated = $inactive;
$reactivated['active'] = 1;
$on = MGS_Direct_Quiz::sync_static_transition( $inactive, $reactivated );
if ( is_wp_error( $on ) ) { throw new RuntimeException( $on->get_error_message() ); }

$result = array(
    'first_marker' => false !== strpos( $html1, MGS_Direct_Quiz::STATIC_MARKER ),
    'first_raw_destination' => false !== strpos( $html1, 'href="https://example.test/rec/?utm_source=fixed"' ),
    'first_assets_versioned' => false !== strpos( $html1, 'direct-quiz.css?v=1.1.0' ) && false !== strpos( $html1, 'direct-quiz.js?v=1.1.0' ),
    'edit_replaced' => false === strpos( $html2, 'Original title' ) && false !== strpos( $html2, 'Edited title' ),
    'edit_path_same' => $index === $second['path'],
    'route_guard_code' => is_wp_error( $route_guard ) ? $route_guard->get_error_code() : '',
    'inactive_removed_public_path' => $inactive_removed_public_path,
    'inactive_archived' => is_array( $off ) && is_dir( $off['archived_path'] ),
    'inactive_copy_unpublished' => true === $copy_result && ! is_file( $copy_path ),
    'reactivated' => is_array( $on ) && is_file( $on['path'] ),
    'readback_sha_match' => hash_file( 'sha256', $on['path'] ) === $on['sha256'],
);
echo json_encode( $result, JSON_UNESCAPED_SLASHES ) . "\n";
