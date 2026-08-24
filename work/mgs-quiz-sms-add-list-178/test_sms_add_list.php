<?php
error_reporting( E_ALL );
define( 'ABSPATH', __DIR__ . '/' );

class WP_Error {
    private $code;
    private $message;
    private $data;
    public function __construct( $code, $message, $data = null ) { $this->code = $code; $this->message = $message; $this->data = $data; }
    public function get_error_code() { return $this->code; }
    public function get_error_data() { return $this->data; }
}
function is_wp_error( $value ) { return $value instanceof WP_Error; }
function sanitize_text_field( $value ) { return trim( strip_tags( (string) $value ) ); }
function esc_url_raw( $value ) { return filter_var( trim( (string) $value ), FILTER_SANITIZE_URL ); }
function wp_parse_url( $value ) { return parse_url( $value ); }
function get_option( $key, $default = false ) { return $default; }
function esc_attr( $value ) { return htmlspecialchars( (string) $value, ENT_QUOTES, 'UTF-8' ); }
function esc_html( $value ) { return htmlspecialchars( (string) $value, ENT_QUOTES, 'UTF-8' ); }
function wp_nonce_field( $action ) { echo '<input type="hidden" name="_wpnonce" value="test">'; }
function submit_button( $label ) { echo '<button type="submit">' . esc_html( $label ) . '</button>'; }

require __DIR__ . '/candidate/mgs-quiz-carro/includes/class-mgs-quiz-admin.php';

function invoke_private( $name, array $args ) {
    $method = new ReflectionMethod( 'MGS_Quiz_Admin', $name );
    $method->setAccessible( true );
    return $method->invokeArgs( null, $args );
}
function expect_true( $condition, $message ) {
    if ( ! $condition ) { fwrite( STDERR, "FAIL: {$message}\n" ); exit( 1 ); }
    echo "PASS: {$message}\n";
}

$base = 'https://v2.smsfunnel.com.br/integrations/lists/00000000-0000-0000-0000-000000000000/add-lead';
$valid = invoke_private( 'build_sms_presets_from_input', array(
    array( 'G001', 'g007' ),
    array( 'G001 – Atual', 'G007 – Nova' ),
    array( $base, $base ),
    array( 'G001' ),
) );
expect_true( is_array( $valid ) && isset( $valid['G007'] ), 'aceita e normaliza uma nova lista G007' );
expect_true( 'G007' === $valid['G007']['gestor_code'], 'persiste o código normalizado' );

$duplicate = invoke_private( 'build_sms_presets_from_input', array(
    array( 'G001', 'g001' ), array( 'A', 'B' ), array( $base, $base ), array( 'G001' ),
) );
expect_true( is_wp_error( $duplicate ) && 'duplicate_code' === $duplicate->get_error_code(), 'bloqueia código duplicado' );

$invalid_url = invoke_private( 'build_sms_presets_from_input', array(
    array( 'G001' ), array( 'A' ), array( 'https://example.com/add-lead' ), array( 'G001' ),
) );
expect_true( is_wp_error( $invalid_url ) && 'invalid' === $invalid_url->get_error_code(), 'bloqueia URL fora do SMS Funnel' );

$missing = invoke_private( 'build_sms_presets_from_input', array(
    array( 'G007' ), array( 'Nova' ), array( $base ), array( 'G001' ),
) );
expect_true( is_wp_error( $missing ) && 'missing_code' === $missing->get_error_code(), 'impede remover uma lista existente por omissão' );

ob_start();
MGS_Quiz_Admin::render_sms_settings();
$html = ob_get_clean();
expect_true( false !== strpos( $html, 'id="mgsqAddSmsList"' ), 'renderiza o botão Adicionar lista' );
expect_true( false !== strpos( $html, 'name="sms_codes[]"' ), 'renderiza códigos de lista no POST' );
expect_true( false !== strpos( $html, 'padStart(3' ), 'gera automaticamente o próximo código' );
expect_true( false !== strpos( $html, 'grid.appendChild(row)' ), 'anexa uma nova linha editável na UI' );
file_put_contents( __DIR__ . '/sms-admin-fixture.html', $html );

echo "ALL TESTS PASSED\n";
