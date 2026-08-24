<?php
/**
 * Template público de página inteira (usado pelo rewrite).
 * $cfg vem do MGS_Quiz_Rewrite::maybe_render().
 *
 * Faz o mesmo trabalho que o shortcode faria em termos de assets / globais,
 * mas em um documento HTML autônomo (sem header/footer do tema).
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
$primary = ! empty( $cfg['primary_color'] ) ? $cfg['primary_color'] : '#1e8323';
$title   = ! empty( $cfg['seo_title'] ) ? $cfg['seo_title'] : ( ! empty( $cfg['title'] ) ? $cfg['title'] : 'Quiz' );
$desc    = ! empty( $cfg['seo_description'] ) ? $cfg['seo_description'] : '';

$public_cfg = $cfg;
unset( $public_cfg['sms_funnel_url'], $public_cfg['sms_funnel_urls'] );

$pixel = preg_match( '/^\d{10,20}$/', isset( $cfg['meta_pixel_id'] ) ? (string) $cfg['meta_pixel_id'] : '' ) ? $cfg['meta_pixel_id'] : '';
$gtm   = preg_match( '/^GTM-[A-Z0-9]{4,10}$/', isset( $cfg['gtm_id'] ) ? (string) $cfg['gtm_id'] : '' ) ? $cfg['gtm_id'] : '';
?><!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title><?php echo esc_html( $title ); ?></title>
<?php if ( $desc ) : ?><meta name="description" content="<?php echo esc_attr( $desc ); ?>"><?php endif; ?>
<?php if ( isset( $cfg['layout_template'] ) && 'quiz_maker_sb' === sanitize_key( $cfg['layout_template'] ) ) : ?>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cabin:wght@400;500;600&amp;display=swap">
<?php endif; ?>
<link rel="stylesheet" href="<?php echo esc_url( MGS_QUIZ_URL . 'public/css/quiz.css?v=' . MGS_QUIZ_VERSION ); ?>">
<style>:root{--mgs-primary:<?php echo esc_html( $primary ); ?>}</style>
<?php if ( $pixel ) : ?>
<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init','<?php echo esc_js( $pixel ); ?>');fbq('track','PageView');</script>
<?php endif; if ( $gtm ) : ?>
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);})(window,document,'script','dataLayer','<?php echo esc_js( $gtm ); ?>');</script>
<?php endif; ?>
</head>
<body class="mgs-quiz-body">
<?php include MGS_QUIZ_PATH . 'templates/quiz-embed.php'; ?>
<script>
  window.MGS_QUIZ_REST = <?php echo wp_json_encode( esc_url_raw( rest_url( 'mgs-quiz/v1' ) ) ); ?>;
  window.MGS_QUIZ_CFG  = <?php echo wp_json_encode( $public_cfg ); ?>;
</script>
<script src="<?php echo esc_url( MGS_QUIZ_URL . 'public/js/quiz.js?v=' . MGS_QUIZ_VERSION ); ?>"></script>
</body>
</html>
