<?php
/**
 * Layout ApplyZeo: réplica first-party da experiência visual de duas etapas,
 * mantendo captura, SMS Funnel e redirecionamento no backend MGS.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

$opts       = ( isset( $cfg['options'] ) && is_array( $cfg['options'] ) ) ? $cfg['options'] : array();
$ts         = (int) ( microtime( true ) * 1000 );
$title      = ! empty( $cfg['title'] ) ? $cfg['title'] : 'Veja as melhores condições para financiar seu carro';
$subtitle   = ! empty( $cfg['subtitle'] ) ? $cfg['subtitle'] : 'Escolha a faixa de preço e veja em 1 minuto as condições de financiamento mais comuns para ela — direto no seu celular.';
$question   = ! empty( $cfg['question'] ) ? $cfg['question'] : 'Qual é a faixa de preço do carro que você procura?';
$form_title = ! empty( $cfg['form_title'] ) ? $cfg['form_title'] : 'Você está a um passo de conhecer as opções disponíveis para o seu perfil';
$privacy    = ! empty( $cfg['privacy_url'] ) ? $cfg['privacy_url'] : home_url( '/politica-de-privacidade/' );
$terms      = ! empty( $cfg['terms_url'] ) ? $cfg['terms_url'] : home_url( '/termos-de-uso/' );
$contact    = home_url( '/contato/' );
?>
<div class="mgs-quiz mgsq-zeo" data-slug="<?php echo esc_attr( $cfg['slug'] ); ?>">
  <div class="mgsq-zeo-shell">
    <aside class="mgsq-zeo-brand">
      <?php if ( ! empty( $cfg['logo_url'] ) ) : ?>
        <img src="<?php echo esc_url( $cfg['logo_url'] ); ?>" alt="Credito para Veiculo">
      <?php else : ?>
        <span>Credito para Veiculo</span>
      <?php endif; ?>
    </aside>

    <main class="mgsq-zeo-col">
      <div class="mgsq-zeo-track" aria-label="Progresso do formulário"><div class="mgs-quiz-progress-bar" style="width:41.3333%"></div></div>

      <div class="mgsq-zeo-head">
        <h1><?php echo esc_html( $title ); ?></h1>
        <p><?php echo esc_html( $subtitle ); ?></p>
      </div>

      <section class="mgs-quiz-step mgs-quiz-step-1 mgsq-zeo-question">
        <h2><?php echo esc_html( $question ); ?></h2>
        <div class="mgsq-zeo-options">
          <?php foreach ( $opts as $opt ) : ?>
            <button type="button" class="mgs-quiz-option" data-value="<?php echo esc_attr( $opt ); ?>"><span class="mgsq-zeo-radio" aria-hidden="true"></span><span><?php echo esc_html( $opt ); ?></span></button>
          <?php endforeach; ?>
        </div>
      </section>

      <div class="mgsq-zeo-backrow">
        <button type="button" class="mgsq-zeo-back" aria-label="Voltar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"></path></svg>
          <span>Voltar</span>
        </button>
      </div>

      <div class="mgsq-zeo-loading" role="status" aria-live="polite">
        <div class="mgsq-zeo-scene">
          <div class="mgsq-zeo-car">
            <svg viewBox="0 0 240 130" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M18 96c-6 0-10-5-10-10 0-6 4-10 9-11l11-27c4-9 12-15 22-15h82c10 0 20 5 26 13l17 24 26 5c9 2 16 10 16 19v8c0 4-3 8-7 8h-12" fill="var(--mgs-primary)" opacity=".14"></path>
              <path d="M14 88c0-7 5-12 12-12h5l13-30c4-9 12-14 21-14h84c10 0 19 5 24 14l15 25 27 5c10 2 17 10 17 20v9c0 4-3 7-7 7h-13" fill="var(--mgs-primary)"></path>
              <path d="M14 92h226v5c0 4-3 7-7 7H21c-4 0-7-3-7-7z" fill="#123d32"></path>
              <path d="M55 74l11-26c2-6 8-9 14-9h37v35zM128 39h26c7 0 13 3 17 9l15 26h-58z" fill="#fff" opacity=".9"></path>
              <rect x="117" y="39" width="11" height="35" fill="#123d32"></rect>
              <circle cx="66" cy="104" r="20" fill="#232b38"></circle><circle cx="66" cy="104" r="9" fill="#e7ebf2"></circle>
              <circle cx="188" cy="104" r="20" fill="#232b38"></circle><circle cx="188" cy="104" r="9" fill="#e7ebf2"></circle>
            </svg>
          </div>
          <div class="mgsq-zeo-lens">
            <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="26" cy="26" r="17" fill="rgba(255,255,255,.55)" stroke="#232b38" stroke-width="5"></circle><path d="M39 39l16 16" stroke="#232b38" stroke-width="7" stroke-linecap="round"></path></svg>
          </div>
        </div>
        <div class="mgsq-zeo-dots"><span></span><span></span><span></span></div>
        <p>Separando as condições da sua faixa...</p>
      </div>

      <form class="mgs-quiz-step mgs-quiz-step-2 mgsq-zeo-form" style="display:none" novalidate autocomplete="on">
        <h2><span aria-hidden="true">🚙</span> <?php echo esc_html( $form_title ); ?></h2>

        <label for="mgsq-zeo-name"><?php echo esc_html( ! empty( $cfg['form_name_label'] ) ? $cfg['form_name_label'] : 'Seu nome' ); ?> *</label>
        <input id="mgsq-zeo-name" type="text" name="name" required autocomplete="name" autocapitalize="words" placeholder="Ex: João">

        <label for="mgsq-zeo-phone"><?php echo esc_html( ! empty( $cfg['form_phone_label'] ) ? $cfg['form_phone_label'] : 'Celular com DDD' ); ?> *</label>
        <input id="mgsq-zeo-phone" type="tel" name="phone" inputmode="numeric" required autocomplete="tel-national" maxlength="16" placeholder="Digite seu telefone com DDD">

        <div class="mgs-quiz-hp" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden">
          <label>Não preencher</label><input type="text" name="website" tabindex="-1" autocomplete="off">
        </div>
        <input type="hidden" name="ts" value="<?php echo esc_attr( $ts ); ?>">

        <p class="mgs-quiz-error-msg" role="alert" style="display:none"></p>
        <button type="submit" class="mgs-quiz-submit"><span class="mgsq-zeo-spinner" aria-hidden="true"></span><span><?php echo esc_html( ! empty( $cfg['form_submit_label'] ) ? $cfg['form_submit_label'] : 'SIMULAR AGORA' ); ?></span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"></path></svg></button>
        <div class="mgsq-zeo-trust"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>Dados protegidos · usados apenas para contato · sem spam</div>
      </form>

      <div class="mgs-quiz-success mgsq-zeo-success" style="display:none">
        <div class="mgsq-zeo-success-icon"><svg viewBox="0 0 24 24" fill="none" stroke="#17a34a" stroke-width="2.4" aria-hidden="true"><path d="M20 6L9 17l-5-5"></path></svg></div>
        <h2><?php echo esc_html( ! empty( $cfg['success_title'] ) ? $cfg['success_title'] : 'Pronto!' ); ?></h2>
        <p><?php echo wp_kses_post( ! empty( $cfg['success_message'] ) ? $cfg['success_message'] : 'Recebemos suas informações. Em instantes você receberá o contato.' ); ?></p>
      </div>
    </main>
  </div>

  <footer class="mgsq-zeo-footer">
    <div class="mgsq-zeo-footin">
      <nav><a href="<?php echo esc_url( $privacy ); ?>">Política de privacidade</a><a href="<?php echo esc_url( $terms ); ?>">Termos de Serviço</a><a href="<?php echo esc_url( $contact ); ?>">Contato</a></nav>
      <p class="mgsq-zeo-disclaimer">Este é um portal de conteúdo informativo e educativo sobre financiamento de veículos, crédito e finanças pessoais. Não somos instituição financeira: não oferecemos, intermediamos ou concedemos crédito, e não temos vínculo com as instituições eventualmente mencionadas. Nenhum conteúdo constitui oferta, recomendação ou aconselhamento financeiro — antes de decidir, consulte a instituição de sua escolha e um profissional qualificado. Este site exibe anúncios de terceiros e pode receber remuneração por parcerias, sem custo adicional para você.</p>
      <p class="mgsq-zeo-legal">MARKETING DIGITAL ADS LTDA – CNPJ: 34.355.241/0001-75 · ©<?php echo esc_html( wp_date( 'Y' ) ); ?> Todos os direitos reservados</p>
    </div>
  </footer>
</div>
