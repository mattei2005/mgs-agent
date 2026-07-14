<?php
/**
 * Layout Quiz Maker SB: réplica visual first-party do quiz de duas etapas
 * (pergunta de faixa de preço -> nome/telefone), mantendo o backend MGS.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

$opts       = ( isset( $cfg['options'] ) && is_array( $cfg['options'] ) ) ? $cfg['options'] : array();
$ts         = (int) ( microtime( true ) * 1000 );
$title      = ! empty( $cfg['title'] ) ? $cfg['title'] : 'Carros sem entrada disponíveis';
$subtitle   = ! empty( $cfg['subtitle'] ) ? $cfg['subtitle'] : 'Ofertas liberadas HOJE, descubra em segundos quanto irá ficar sua parcela.';
$form_intro = ! empty( $cfg['form_title'] ) ? $cfg['form_title'] : 'Não perca tempo: complete seus dados abaixo e descubra se o carro já pode ser seu.';
?>
<div class="mgs-quiz mgsq-sb" data-slug="<?php echo esc_attr( $cfg['slug'] ); ?>">
  <header class="mgsq-sb-header">
    <div class="mgsq-sb-copy mgsq-sb-copy-step1">
      <h1><?php echo esc_html( $title ); ?></h1>
      <p><?php echo esc_html( $subtitle ); ?></p>
    </div>

    <div class="mgsq-sb-copy mgsq-sb-copy-step2" aria-live="polite">
      <h1><?php echo esc_html( $title ); ?></h1>
      <p><?php echo esc_html( $form_intro ); ?></p>
    </div>

    <div class="mgsq-sb-progress" aria-label="Etapa 1 de 2">
      <div class="mgsq-sb-progress-track"><div class="mgs-quiz-progress-bar" style="width:50%"></div></div>
      <span>(1/2)</span>
    </div>

    <?php if ( ! empty( $cfg['car_image_url'] ) ) : ?>
      <img class="mgsq-sb-car" src="<?php echo esc_url( $cfg['car_image_url'] ); ?>" alt="Carro disponível para financiamento">
    <?php endif; ?>
  </header>

  <main class="mgsq-sb-main">
    <section class="mgs-quiz-step mgs-quiz-step-1 mgsq-sb-question">
      <h2><?php echo esc_html( ! empty( $cfg['question'] ) ? $cfg['question'] : 'Qual é a faixa de preço do carro que você deseja comprar?' ); ?></h2>
      <div class="mgsq-sb-options">
        <?php foreach ( $opts as $opt ) : ?>
          <button type="button" class="mgs-quiz-option" data-value="<?php echo esc_attr( $opt ); ?>"><?php echo esc_html( $opt ); ?></button>
        <?php endforeach; ?>
      </div>
    </section>

    <form class="mgs-quiz-step mgs-quiz-step-2 mgsq-sb-form" style="display:none" novalidate autocomplete="on">
      <label for="mgsq-sb-name"><?php echo esc_html( ! empty( $cfg['form_name_label'] ) ? $cfg['form_name_label'] : 'Nome' ); ?></label>
      <input id="mgsq-sb-name" type="text" name="name" required autocomplete="name" placeholder="Digite seu Nome">

      <label for="mgsq-sb-phone"><?php echo esc_html( ! empty( $cfg['form_phone_label'] ) ? $cfg['form_phone_label'] : 'Telefone' ); ?></label>
      <div class="mgsq-sb-phone-wrap">
        <?php if ( ! empty( $cfg['flag_image_url'] ) ) : ?>
          <img src="<?php echo esc_url( $cfg['flag_image_url'] ); ?>" alt="Brasil">
        <?php endif; ?>
        <input id="mgsq-sb-phone" type="tel" name="phone" inputmode="numeric" required autocomplete="tel" placeholder="Digite seu telefone aqui">
      </div>

      <div class="mgs-quiz-hp" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden">
        <label>Não preencher</label>
        <input type="text" name="website" tabindex="-1" autocomplete="off">
      </div>
      <input type="hidden" name="ts" value="<?php echo esc_attr( $ts ); ?>">

      <button type="submit" class="mgs-quiz-submit"><?php echo esc_html( ! empty( $cfg['form_submit_label'] ) ? $cfg['form_submit_label'] : 'VER PARCELAS' ); ?></button>
      <p class="mgs-quiz-error-msg" style="display:none"></p>
    </form>

    <div class="mgs-quiz-success mgsq-sb-success" style="display:none">
      <h2><?php echo esc_html( ! empty( $cfg['success_title'] ) ? $cfg['success_title'] : 'Cadastro realizado com sucesso!' ); ?></h2>
      <p><?php echo wp_kses_post( ! empty( $cfg['success_message'] ) ? $cfg['success_message'] : 'Estamos te redirecionando...' ); ?></p>
    </div>
  </main>

  <footer class="mgsq-sb-footer">
    <?php echo wp_kses_post( ! empty( $cfg['footer_html'] ) ? $cfg['footer_html'] : '<a href="/politica-de-privacidade">Política de Privacidade</a> | <a href="/termos-de-uso">Termos de Uso</a>' ); ?>
  </footer>
</div>
