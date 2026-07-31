<?php
if ( ! defined( 'ABSPATH' ) ) { exit( 1 ); }
$config_path = WP_PLUGIN_DIR . '/mgs-chat-funnels/configs/car-br-01-sms.json';
$config = json_decode( (string) file_get_contents( $config_path ), true );
$instance = MGS_Chat_Funnels::instance();
$method = new ReflectionMethod( MGS_Chat_Funnels::class, 'render_human_editor' );
$method->setAccessible( true );
ob_start();
$method->invoke( $instance, $config, false );
$html = ob_get_clean();
$markers = array(
    'Permitir pular nome e telefone',
    'Mostrar consentimento para SMS',
    'Consentimento selecionado por padrão',
    'Formulário compacto, sem “Oferta encontrada”',
    'Mostrar região do visitante',
    'Pular loading do gate',
    'Provider de anúncios: ActView / Zuout',
);
$missing = array();
foreach ( $markers as $marker ) { if ( strpos( $html, $marker ) === false ) $missing[] = $marker; }
printf( "admin_bytes=%d markers=%d missing=%d\n", strlen( $html ), count( $markers ), count( $missing ) );
if ( $missing ) { fwrite( STDERR, implode( ' | ', $missing ) . "\n" ); exit( 2 ); }
