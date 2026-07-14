<?php
/**
 * Markup do quiz (compartilhado por shortcode e template público).
 * Recebe $cfg.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
$layout = isset( $cfg['layout_template'] ) ? sanitize_key( $cfg['layout_template'] ) : '';
if ( 'quiz_maker_sb' === $layout ) {
  include MGS_QUIZ_PATH . 'templates/quiz-embed-sb.php';
  return;
}
if ( 'fmybc_sms' === $layout ) {
  include MGS_QUIZ_PATH . 'templates/quiz-embed-fmybc.php';
  return;
}
$opts = ( isset( $cfg['options'] ) && is_array( $cfg['options'] ) ) ? $cfg['options'] : array();
$ts   = (int) ( microtime( true ) * 1000 );
?>
<div class="mgs-quiz" data-slug="<?php echo esc_attr( $cfg['slug'] ); ?>">
  <header class="mgs-quiz-header">
    <?php if ( ! empty( $cfg['logo_url'] ) ) : ?>
      <img src="<?php echo esc_url( $cfg['logo_url'] ); ?>" alt="Logo" class="mgs-quiz-logo">
    <?php endif; ?>
    <?php if ( ! empty( $cfg['flag_image_url'] ) ) : ?>
      <img src="<?php echo esc_url( $cfg['flag_image_url'] ); ?>" alt="" class="mgs-quiz-flag">
    <?php endif; ?>
  </header>

  <section class="mgs-quiz-main">
    <div class="mgs-quiz-left">
      <h1><?php echo esc_html( $cfg['title'] ); ?></h1>
      <p><?php echo esc_html( $cfg['subtitle'] ); ?></p>
      <?php if ( ! empty( $cfg['car_image_url'] ) ) : ?>
        <img src="<?php echo esc_url( $cfg['car_image_url'] ); ?>" alt="" class="mgs-quiz-car">
      <?php endif; ?>
    </div>

    <div class="mgs-quiz-right">
      <div class="mgs-quiz-card">
        <p class="mgs-quiz-step-title"
           data-step1="<?php echo esc_attr( $cfg['question'] ); ?>"
           data-step2="<?php echo esc_attr( ! empty( $cfg['form_title'] ) ? $cfg['form_title'] : 'Preencha suas informações' ); ?>">
          <?php echo esc_html( $cfg['question'] ); ?>
        </p>
        <div class="mgs-quiz-progress"><div class="mgs-quiz-progress-bar" style="width:50%"></div></div>

        <div class="mgs-quiz-step mgs-quiz-step-1">
          <?php foreach ( $opts as $opt ) : ?>
            <button type="button" class="mgs-quiz-option" data-value="<?php echo esc_attr( $opt ); ?>"><?php echo esc_html( $opt ); ?></button>
          <?php endforeach; ?>
        </div>

        <form class="mgs-quiz-step mgs-quiz-step-2" style="display:none" novalidate autocomplete="on">
          <label><?php echo esc_html( ! empty( $cfg['form_name_label'] ) ? $cfg['form_name_label'] : 'Nome' ); ?> *</label>
          <input type="text" name="name" required autocomplete="name">

          <label><?php echo esc_html( ! empty( $cfg['form_phone_label'] ) ? $cfg['form_phone_label'] : 'Telefone' ); ?> *</label>
          <input type="tel" name="phone" inputmode="numeric" required autocomplete="tel"
                 placeholder="<?php echo esc_attr( ! empty( $cfg['form_phone_mask'] ) ? $cfg['form_phone_mask'] : '(99) 99999-9999' ); ?>">

          <!-- Anti-spam: honeypot invisível + timestamp de carregamento -->
          <div class="mgs-quiz-hp" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden">
            <label>Não preencher</label>
            <input type="text" name="website" tabindex="-1" autocomplete="off">
          </div>
          <input type="hidden" name="ts" value="<?php echo esc_attr( $ts ); ?>">

          <button type="submit" class="mgs-quiz-submit"><?php echo esc_html( ! empty( $cfg['form_submit_label'] ) ? $cfg['form_submit_label'] : 'ESCOLHER CARRO' ); ?></button>
          <p class="mgs-quiz-error-msg" style="display:none;color:#e32;margin-top:10px"></p>
        </form>

        <div class="mgs-quiz-success" style="display:none">
          <h2><?php echo esc_html( ! empty( $cfg['success_title'] ) ? $cfg['success_title'] : 'Obrigado!' ); ?></h2>
          <p><?php echo wp_kses_post( ! empty( $cfg['success_message'] ) ? $cfg['success_message'] : 'Estamos te redirecionando...' ); ?></p>
        </div>
      </div>
    </div>
  </section>

  <footer class="mgs-quiz-footer">
    <?php echo wp_kses_post( ! empty( $cfg['footer_html'] ) ? $cfg['footer_html'] : ( '© ' . date( 'Y' ) . ' — Todos os direitos reservados.' ) ); ?>
  </footer>
</div>
