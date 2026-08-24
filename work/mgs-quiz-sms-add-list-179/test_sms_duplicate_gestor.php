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
function wp_generate_uuid4() { static $n = 0; $n++; return sprintf( '00000000-0000-4000-8000-%012d', $n ); }
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

$url_a = 'https://v2.smsfunnel.com.br/integrations/lists/00000000-0000-0000-0000-000000000001/add-lead';
$url_b = 'https://v2.smsfunnel.com.br/integrations/lists/00000000-0000-0000-0000-000000000002/add-lead';
$valid = invoke_private( 'build_sms_presets_from_input', array(
    array( 'G004', '' ),
    array( 'G004', 'G004' ),
    array( 'G004 – Joe', 'G004 Moto – Joe' ),
    array( $url_a, $url_b ),
    array( 'G004' ),
) );
expect_true( is_array( $valid ) && 2 === count( $valid ), 'aceita duas listas para o mesmo gestor G004' );
$custom_ids = array_values( array_diff( array_keys( $valid ), array( 'G004' ) ) );
expect_true( 1 === count( $custom_ids ) && 0 === strpos( $custom_ids[0], 'sms_' ), 'gera identificador interno para a lista nova' );
$custom_id = $custom_ids[0];
expect_true( 'G004' === $valid[ $custom_id ]['gestor_code'], 'mantém G004 como gestor da segunda lista' );

$resolved = invoke_private( 'sms_preset_id_for_row', array(
    array( 'gestor_code' => 'G004', 'url' => $url_b, 'label' => 'G004 Moto – Joe' ),
    $valid,
) );
expect_true( $custom_id === $resolved, 'resolve a lista G004 correta pela URL, sem confundir com a G004 original' );

$invalid_url = invoke_private( 'build_sms_presets_from_input', array(
    array( 'G004' ), array( 'G004' ), array( 'A' ), array( 'https://example.com/add-lead' ), array( 'G004' ),
) );
expect_true( is_wp_error( $invalid_url ) && 'invalid' === $invalid_url->get_error_code(), 'bloqueia URL fora do SMS Funnel' );

$missing = invoke_private( 'build_sms_presets_from_input', array(
    array( '' ), array( 'G004' ), array( 'Nova' ), array( $url_b ), array( 'G004' ),
) );
expect_true( is_wp_error( $missing ) && 'missing_list' === $missing->get_error_code(), 'impede remover uma lista existente por omissão' );

ob_start();
MGS_Quiz_Admin::render_sms_settings();
$html = ob_get_clean();
expect_true( false !== strpos( $html, 'id="mgsqAddSmsList"' ), 'renderiza o botão Adicionar lista' );
expect_true( false !== strpos( $html, 'name="sms_preset_ids[]"' ), 'renderiza identificadores internos ocultos' );
expect_true( false === strpos( $html, 'padStart(3' ), 'não calcula G007 automaticamente' );
expect_true( false !== strpos( $html, 'name="sms_codes[]" required pattern="G[0-9]{3,}" maxlength="12" value=""' ), 'nova linha inicia com Gestor em branco' );
expect_true( false !== strpos( $html, 'O mesmo gestor pode ter mais de uma lista.' ), 'mensagem da tela documenta gestores repetidos' );
file_put_contents( __DIR__ . '/sms-admin-fixture.html', $html );

echo "ALL TESTS PASSED\n";
