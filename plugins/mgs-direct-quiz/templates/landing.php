<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}
$item      = $mgs_dq_item;
$layout    = in_array( (string) ( $item['layout_template'] ?? '' ), array( 'lp1', 'lp2' ), true ) ? $item['layout_template'] : 'lp1';
$country   = strtolower( (string) ( $item['country'] ?? 'us' ) );
$lang      = 'us' === $country ? 'en-US' : 'en';
$dest_a    = MGS_Direct_Quiz::merge_query_params( (string) ( $item['destination_a_url'] ?? '' ) );
$dest_b    = MGS_Direct_Quiz::merge_query_params( (string) ( $item['destination_b_url'] ?? $dest_a ) );
$legal     = array(
    'Privacy Policy'  => (string) ( $item['privacy_url'] ?? '' ),
    'Terms of Service' => (string) ( $item['terms_url'] ?? '' ),
    'Disclaimer'      => (string) ( $item['disclaimer_url'] ?? '' ),
);
?><!doctype html>
<html lang="<?php echo esc_attr( $lang ); ?>">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title><?php echo esc_html( (string) ( $item['title'] ?? 'Quiz' ) ); ?></title>
<meta name="description" content="<?php echo esc_attr( (string) ( $item['question'] ?? '' ) ); ?>">
<?php if ( ! empty( $item['noindex'] ) ) : ?><meta name="robots" content="noindex,nofollow"><?php endif; ?>
<link rel="stylesheet" href="<?php echo esc_url( MGS_DQ_URL . 'assets/direct-quiz.css?v=' . MGS_DQ_VERSION ); ?>">
</head>
<body class="mgs-dq-body mgs-dq-<?php echo esc_attr( $layout ); ?>" data-model="<?php echo esc_attr( $layout ); ?>" data-manager="<?php echo esc_attr( (string) ( $item['manager_code'] ?? '' ) ); ?>">
<main class="mgs-dq-shell">
  <section class="mgs-dq-card" aria-labelledby="mgs-dq-title">
    <?php if ( 'lp2' === $layout && ! empty( $item['logo_url'] ) ) : ?>
      <div class="mgs-dq-logo"><img src="<?php echo esc_url( $item['logo_url'] ); ?>" alt=""></div>
    <?php endif; ?>
    <?php if ( 'lp2' === $layout ) : ?><div class="mgs-dq-badge">Quick Eligibility Check</div><?php endif; ?>
    <header class="mgs-dq-header">
      <h1 id="mgs-dq-title"><?php echo esc_html( (string) ( $item['title'] ?? '' ) ); ?></h1>
    </header>
    <p class="mgs-dq-question"><?php echo esc_html( (string) ( $item['question'] ?? '' ) ); ?></p>
    <div class="mgs-dq-options">
      <a class="mgs-dq-cta mgs-dq-cta-a" data-mgs-dq-cta href="<?php echo esc_url( $dest_a ); ?>">
        <?php if ( ! empty( $item['option_a_icon'] ) ) : ?><span class="mgs-dq-icon" aria-hidden="true"><?php echo esc_html( $item['option_a_icon'] ); ?></span><?php endif; ?>
        <span><?php echo esc_html( (string) ( $item['option_a_text'] ?? 'Yes' ) ); ?></span>
      </a>
      <a class="mgs-dq-cta mgs-dq-cta-b" data-mgs-dq-cta href="<?php echo esc_url( $dest_b ); ?>">
        <?php if ( ! empty( $item['option_b_icon'] ) ) : ?><span class="mgs-dq-icon" aria-hidden="true"><?php echo esc_html( $item['option_b_icon'] ); ?></span><?php endif; ?>
        <span><?php echo esc_html( (string) ( $item['option_b_text'] ?? 'No' ) ); ?></span>
      </a>
    </div>
    <footer class="mgs-dq-footer">
      <?php $shown = 0; foreach ( $legal as $label => $url ) : if ( ! $url ) continue; if ( $shown ) echo '<span aria-hidden="true"> | </span>'; ?>
        <a href="<?php echo esc_url( $url ); ?>"><?php echo esc_html( $label ); ?></a>
      <?php $shown++; endforeach; ?>
    </footer>
  </section>
</main>
<script src="<?php echo esc_url( MGS_DQ_URL . 'assets/direct-quiz.js?v=' . MGS_DQ_VERSION ); ?>" defer></script>
</body>
</html>
