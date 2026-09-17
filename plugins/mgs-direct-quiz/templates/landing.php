<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}
$item      = $mgs_dq_item;
$layout    = in_array( (string) ( $item['layout_template'] ?? '' ), array( 'lp1', 'lp2', 'lp3' ), true ) ? $item['layout_template'] : 'lp1';
$country   = strtolower( (string) ( $item['country'] ?? 'us' ) );
$language  = in_array( strtolower( (string) ( $item['language'] ?? 'en' ) ), array( 'en', 'es' ), true ) ? strtolower( (string) ( $item['language'] ?? 'en' ) ) : 'en';
$lang      = 'es' === $language ? ( 'us' === $country ? 'es-US' : 'es' ) : ( 'us' === $country ? 'en-US' : 'en' );
$dest_a_base = (string) ( $item['destination_a_url'] ?? '' );
$dest_b_base = (string) ( $item['destination_b_url'] ?? $dest_a_base );
$dest_a      = ! empty( $mgs_dq_static_render ) ? $dest_a_base : MGS_Direct_Quiz::merge_query_params( $dest_a_base );
$dest_b      = ! empty( $mgs_dq_static_render ) ? $dest_b_base : MGS_Direct_Quiz::merge_query_params( $dest_b_base );
$asset_base  = ! empty( $mgs_dq_static_render ) ? preg_replace( '#^http://#i', 'https://', MGS_DQ_URL ) : MGS_DQ_URL;
$labels = 'es' === $language ? array(
    'privacy'             => 'Política de Privacidad',
    'terms'               => 'Términos de Servicio',
    'disclaimer'          => 'Descargo de responsabilidad',
    'legal_links'         => 'Enlaces legales',
    'lp2_badge'           => 'Verificación rápida de elegibilidad',
    'yes'                 => 'Sí',
    'no'                  => 'No',
    'urgency'             => 'La oferta de hoy termina en',
    'eyebrow'             => 'ARTÍCULOS GRATIS · DESCUBRE CÓMO OBTENERLOS',
    'category_title'      => '¿Qué te gustaría recibir?',
    'cta'                 => 'VER LAS MEJORES OFERTAS DE HOY',
    'micro'               => 'Seguirás en este sitio',
    'site_fallback'       => 'este sitio',
    'copyright_template'  => 'Copyright © %1$s %2$s. Todos los derechos reservados.',
    'disclaimer_template' => '%1$s nunca solicita ni procesa pagos ni cargos financieros. Todo el contenido se ofrece de forma gratuita. %1$s no está afiliado con ninguna marca, empresa o institución que pueda mencionarse en su contenido.',
) : array(
    'privacy'             => 'Privacy Policy',
    'terms'               => 'Terms of Service',
    'disclaimer'          => 'Disclaimer',
    'legal_links'         => 'Legal links',
    'lp2_badge'           => 'Quick Eligibility Check',
    'yes'                 => 'Yes',
    'no'                  => 'No',
    'urgency'             => "Today's offer ends in",
    'eyebrow'             => 'FREE ITEMS · SEE HOW TO GET',
    'category_title'      => 'What would you like to receive?',
    'cta'                 => "SEE TODAY'S BEST DEALS",
    'micro'               => "You'll stay on this site",
    'site_fallback'       => 'this site',
    'copyright_template'  => 'Copyright © %1$s %2$s. All rights reserved.',
    'disclaimer_template' => '%1$s never requests or processes any kind of payment or financial charge. All content is provided free of charge. %1$s is not affiliated with any brand, company, or institution that may be mentioned in its content.',
);
$legal     = array(
    $labels['privacy']    => (string) ( $item['privacy_url'] ?? '' ),
    $labels['terms']      => (string) ( $item['terms_url'] ?? '' ),
    $labels['disclaimer'] => (string) ( $item['disclaimer_url'] ?? '' ),
);
$category_defaults = array(
    array( 'text' => 'es' === $language ? 'Mujer' : 'Women', 'asset' => 'women.svg' ),
    array( 'text' => 'es' === $language ? 'Hombre' : 'Men', 'asset' => 'men.svg' ),
    array( 'text' => 'es' === $language ? 'Niños' : 'Kids', 'asset' => 'kids.svg' ),
    array( 'text' => 'es' === $language ? 'Calzado' : 'Shoes', 'asset' => 'shoes.svg' ),
    array( 'text' => 'es' === $language ? 'Teléfonos' : 'Phones', 'asset' => 'phones.svg' ),
    array( 'text' => 'es' === $language ? 'Accesorios' : 'Accessories', 'asset' => 'accessories.svg' ),
);
$stored_categories = isset( $item['categories'] ) && is_array( $item['categories'] ) ? array_values( $item['categories'] ) : array();
$categories = array();
foreach ( $category_defaults as $index => $default ) {
    $stored = isset( $stored_categories[ $index ] ) && is_array( $stored_categories[ $index ] ) ? $stored_categories[ $index ] : array();
    $categories[] = array(
        'text'      => trim( (string) ( $stored['text'] ?? '' ) ) ?: $default['text'],
        'image_url' => trim( (string) ( $stored['image_url'] ?? '' ) ) ?: $asset_base . 'assets/categories/' . $default['asset'],
    );
}
$site_host = (string) parse_url( $dest_a_base, PHP_URL_HOST );
$site_host = preg_replace( '/^www\./i', '', $site_host ) ?: $labels['site_fallback'];
$default_disclaimer = sprintf(
    $labels['disclaimer_template'],
    $site_host
);
$disclaimer_text = trim( (string) ( $item['disclaimer_text'] ?? '' ) ) ?: $default_disclaimer;
?><!doctype html>
<html lang="<?php echo esc_attr( $lang ); ?>">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title><?php echo esc_html( (string) ( $item['title'] ?? 'Quiz' ) ); ?></title>
<meta name="description" content="<?php echo esc_attr( (string) ( $item['question'] ?? '' ) ); ?>">
<?php if ( ! empty( $item['noindex'] ) ) : ?><meta name="robots" content="noindex,nofollow"><?php endif; ?>
<link rel="stylesheet" href="<?php echo esc_url( $asset_base . 'assets/direct-quiz.css?v=' . MGS_DQ_VERSION ); ?>">
</head>
<body class="mgs-dq-body mgs-dq-<?php echo esc_attr( $layout ); ?>" data-model="<?php echo esc_attr( $layout ); ?>" data-manager="<?php echo esc_attr( (string) ( $item['manager_code'] ?? '' ) ); ?>">
<?php if ( 'lp3' === $layout ) : ?>
  <div class="mgs-dq-urgency"><span><?php echo esc_html( (string) ( $item['urgency_text'] ?? $labels['urgency'] ) ); ?></span><strong data-mgs-dq-countdown aria-live="off">--:--:--</strong></div>
  <header class="mgs-dq-store-header">
    <div class="mgs-dq-store-brand">
      <?php if ( ! empty( $item['logo_url'] ) ) : ?><img src="<?php echo esc_url( $item['logo_url'] ); ?>" alt="<?php echo esc_attr( $site_host ); ?>"><?php else : ?><strong><?php echo esc_html( $site_host ); ?></strong><?php endif; ?>
    </div>
  </header>
  <main class="mgs-dq-category-shell">
    <section class="mgs-dq-category-card" aria-labelledby="mgs-dq-title">
      <p class="mgs-dq-category-eyebrow"><span aria-hidden="true"></span><?php echo esc_html( (string) ( $item['eyebrow_text'] ?? $labels['eyebrow'] ) ); ?><i aria-hidden="true"></i></p>
      <h1 id="mgs-dq-title"><?php echo esc_html( (string) ( $item['title'] ?? $labels['category_title'] ) ); ?></h1>
      <div class="mgs-dq-category-grid">
        <?php foreach ( $categories as $category ) : ?>
          <a class="mgs-dq-category" data-mgs-dq-cta href="<?php echo esc_url( $dest_a ); ?>">
            <span class="mgs-dq-category-image"><img src="<?php echo esc_url( $category['image_url'] ); ?>" alt="" width="300" height="300"></span>
            <span class="mgs-dq-category-name"><?php echo esc_html( $category['text'] ); ?></span>
          </a>
        <?php endforeach; ?>
      </div>
      <div class="mgs-dq-category-cta-row">
        <a class="mgs-dq-category-main-cta" data-mgs-dq-cta href="<?php echo esc_url( $dest_a ); ?>">
          <span><?php echo esc_html( (string) ( $item['cta_text'] ?? $labels['cta'] ) ); ?></span>
          <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false"><path d="M5 12h13M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </a>
        <p class="mgs-dq-category-micro"><span aria-hidden="true">✓</span> <?php echo esc_html( (string) ( $item['micro_text'] ?? $labels['micro'] ) ); ?></p>
      </div>
      <div class="mgs-dq-category-divider"></div>
      <section class="mgs-dq-category-legal">
        <button type="button" class="mgs-dq-disclaimer-toggle" data-mgs-dq-disclaimer-toggle aria-expanded="false" aria-controls="mgs-dq-disclaimer-box"><span><?php echo esc_html( $labels['disclaimer'] ); ?></span><span class="mgs-dq-disclaimer-chevron" aria-hidden="true">⌄</span></button>
        <div id="mgs-dq-disclaimer-box" class="mgs-dq-disclaimer-box" data-mgs-dq-disclaimer-box hidden>
          <p><?php echo esc_html( $disclaimer_text ); ?></p>
          <nav aria-label="<?php echo esc_attr( $labels['legal_links'] ); ?>">
            <?php foreach ( $legal as $label => $url ) : if ( ! $url ) continue; ?><a href="<?php echo esc_url( $url ); ?>"><?php echo esc_html( $label ); ?></a><?php endforeach; ?>
          </nav>
        </div>
        <p class="mgs-dq-category-copyright"><?php echo esc_html( sprintf( $labels['copyright_template'], gmdate( 'Y' ), $site_host ) ); ?></p>
      </section>
    </section>
  </main>
<?php else : ?>
  <main class="mgs-dq-shell">
    <section class="mgs-dq-card" aria-labelledby="mgs-dq-title">
      <?php if ( 'lp2' === $layout && ! empty( $item['logo_url'] ) ) : ?>
        <div class="mgs-dq-logo"><img src="<?php echo esc_url( $item['logo_url'] ); ?>" alt=""></div>
      <?php endif; ?>
      <?php if ( 'lp2' === $layout ) : ?><div class="mgs-dq-badge"><?php echo esc_html( $labels['lp2_badge'] ); ?></div><?php endif; ?>
      <header class="mgs-dq-header">
        <h1 id="mgs-dq-title"><?php echo esc_html( (string) ( $item['title'] ?? '' ) ); ?></h1>
      </header>
      <p class="mgs-dq-question"><?php echo esc_html( (string) ( $item['question'] ?? '' ) ); ?></p>
      <div class="mgs-dq-options">
        <a class="mgs-dq-cta mgs-dq-cta-a" data-mgs-dq-cta href="<?php echo esc_url( $dest_a ); ?>">
          <?php if ( ! empty( $item['option_a_icon'] ) ) : ?><span class="mgs-dq-icon" aria-hidden="true"><?php echo esc_html( $item['option_a_icon'] ); ?></span><?php endif; ?>
          <span><?php echo esc_html( (string) ( $item['option_a_text'] ?? $labels['yes'] ) ); ?></span>
        </a>
        <a class="mgs-dq-cta mgs-dq-cta-b" data-mgs-dq-cta href="<?php echo esc_url( $dest_b ); ?>">
          <?php if ( ! empty( $item['option_b_icon'] ) ) : ?><span class="mgs-dq-icon" aria-hidden="true"><?php echo esc_html( $item['option_b_icon'] ); ?></span><?php endif; ?>
          <span><?php echo esc_html( (string) ( $item['option_b_text'] ?? $labels['no'] ) ); ?></span>
        </a>
      </div>
      <footer class="mgs-dq-footer">
        <?php $shown = 0; foreach ( $legal as $label => $url ) : if ( ! $url ) continue; if ( $shown ) echo '<span aria-hidden="true"> | </span>'; ?>
          <a href="<?php echo esc_url( $url ); ?>"><?php echo esc_html( $label ); ?></a>
        <?php $shown++; endforeach; ?>
      </footer>
    </section>
  </main>
<?php endif; ?>
<script src="<?php echo esc_url( $asset_base . 'assets/direct-quiz.js?v=' . MGS_DQ_VERSION ); ?>" defer></script>
</body>
</html>
