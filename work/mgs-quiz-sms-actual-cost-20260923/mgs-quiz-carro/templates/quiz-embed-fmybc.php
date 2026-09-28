<?php
/**
 * Layout compacto inspirado no modelo FMYBC: card central, dados primeiro,
 * checklist, barra de etapas, contador online e badges de segurança.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
$ts = (int) ( microtime( true ) * 1000 );
$title = ! empty( $cfg['title'] ) ? $cfg['title'] : 'Seu Carro Novo Sem Entrada';
$title_html = esc_html( $title );
$title_html = str_replace( 'Sem Entrada', '<span class="mgsq-fmybc-highlight">Sem Entrada</span>', $title_html );
$subtitle = ! empty( $cfg['subtitle'] ) ? $cfg['subtitle'] : 'Solicite agora em apenas 2 minutos';
$intro = ! empty( $cfg['question'] ) ? $cfg['question'] : 'Preencha os dados e responda apenas 3 perguntas e veja os modelos disponíveis para você hoje.';
?>
<div class="mgs-quiz mgsq-fmybc" data-slug="<?php echo esc_attr( $cfg['slug'] ); ?>">
  <main class="mgsq-fmybc-container">
    <h1 class="mgsq-fmybc-title"><?php echo $title_html; // already escaped above; constant span added for highlight. ?></h1>
    <p class="mgsq-fmybc-subtitle"><?php echo esc_html( $subtitle ); ?></p>

    <?php if ( ! empty( $cfg['car_image_url'] ) ) : ?>
      <div class="mgsq-fmybc-car-wrap"><img class="mgsq-fmybc-car" src="<?php echo esc_url( $cfg['car_image_url'] ); ?>" alt="Carro novo sem entrada"></div>
    <?php endif; ?>

    <ul class="mgsq-fmybc-checklist">
      <li><span>✓</span> Sem Consulta</li>
      <li><span>✓</span> Parcelas Reduzidas</li>
      <li><span>✓</span> Aprovação Online em Minutos</li>
    </ul>

    <div class="mgsq-fmybc-steps" aria-label="Etapas do quiz">
      <div class="mgsq-fmybc-step is-active">Dados<div class="mgsq-fmybc-track"><i></i></div></div>
      <div class="mgsq-fmybc-step">Perguntas<div class="mgsq-fmybc-track"></div></div>
      <div class="mgsq-fmybc-step">Resultado<div class="mgsq-fmybc-track"></div></div>
    </div>

    <div class="mgsq-fmybc-online"><span class="mgsq-fmybc-dot"></span><span id="mgsq-online-count">101</span> pessoas online agora</div>
    <p class="mgsq-fmybc-intro"><?php echo esc_html( $intro ); ?></p>

    <form class="mgs-quiz-step mgs-quiz-step-2 mgsq-fmybc-form" novalidate autocomplete="on">
      <div class="mgsq-fmybc-field">
        <label><?php echo esc_html( ! empty( $cfg['form_name_label'] ) ? $cfg['form_name_label'] : 'Nome' ); ?></label>
        <input type="text" name="name" required autocomplete="name" placeholder="Nome">
      </div>
      <div class="mgsq-fmybc-field">
        <label><?php echo esc_html( ! empty( $cfg['form_phone_label'] ) ? $cfg['form_phone_label'] : 'Telefone' ); ?></label>
        <input type="tel" name="phone" inputmode="numeric" required autocomplete="tel" placeholder="<?php echo esc_attr( ! empty( $cfg['form_phone_mask'] ) ? $cfg['form_phone_mask'] : '(99) 99999-9999' ); ?>">
      </div>

      <div class="mgsq-fmybc-notice">Não fazemos ligações, enviaremos apenas uma mensagem quando for aprovado.</div>

      <div class="mgs-quiz-hp" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden">
        <label>Não preencher</label>
        <input type="text" name="website" tabindex="-1" autocomplete="off">
      </div>
      <input type="hidden" name="ts" value="<?php echo esc_attr( $ts ); ?>">
      <button type="submit" class="mgs-quiz-submit mgsq-fmybc-submit"><?php echo esc_html( ! empty( $cfg['form_submit_label'] ) ? $cfg['form_submit_label'] : 'VER CARROS' ); ?></button>
      <p class="mgs-quiz-error-msg mgsq-fmybc-error" style="display:none"></p>
    </form>

    <div class="mgs-quiz-success mgsq-fmybc-success" style="display:none">
      <h2><?php echo esc_html( ! empty( $cfg['success_title'] ) ? $cfg['success_title'] : 'Cadastro realizado com sucesso!' ); ?></h2>
      <p><?php echo wp_kses_post( ! empty( $cfg['success_message'] ) ? $cfg['success_message'] : 'Estamos te redirecionando...' ); ?></p>
    </div>

    <div class="mgsq-fmybc-trust">
      <div><b>🔒</b><span>SSL Seguro</span></div>
      <div><b>🛡️</b><span>Protegido</span></div>
      <div><b>✓</b><span>Verificado</span></div>
    </div>
    <footer class="mgsq-fmybc-legal">
      <?php echo wp_kses_post( ! empty( $cfg['footer_html'] ) ? $cfg['footer_html'] : '<a href="/termos-de-uso">Termos e Condições</a> · <a href="/politica-de-privacidade">Política de Privacidade</a> · <a href="/contato">Contato</a>' ); ?>
    </footer>
  </main>
</div>
