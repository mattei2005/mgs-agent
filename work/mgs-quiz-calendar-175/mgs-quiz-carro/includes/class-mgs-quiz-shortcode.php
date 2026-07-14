<?php
/**
 * Shortcode [mgs_quiz slug="quiz-car-parcelas-g002"]
 *
 * Garante:
 *   - enqueue do CSS e do JS
 *   - injeção de window.MGS_QUIZ_REST e window.MGS_QUIZ_CFG
 *   - markup do quiz via templates/quiz-embed.php
 *
 * Em caso de erro (slug inválido / não encontrado), renderiza mensagem
 * amigável e nunca dispara fatal — seguro para uso em qualquer página.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

class MGS_Quiz_Shortcode {

    public static function register() {
        add_shortcode( 'mgs_quiz', array( __CLASS__, 'render' ) );
    }

    public static function render( $atts ) {
        $atts = shortcode_atts( array( 'slug' => '' ), $atts, 'mgs_quiz' );
        $slug = sanitize_title( $atts['slug'] );
        if ( ! $slug ) {
            return '<p class="mgs-quiz-error">[mgs_quiz]: atributo "slug" obrigatório.</p>';
        }

        if ( ! class_exists( 'MGS_Quiz_REST' ) ) {
            return '<p class="mgs-quiz-error">[mgs_quiz]: plugin não inicializado corretamente.</p>';
        }

        $cfg = MGS_Quiz_REST::get_config_by_slug( $slug );
        if ( ! $cfg ) {
            return '<p class="mgs-quiz-error">[mgs_quiz]: quiz "' . esc_html( $slug ) . '" não encontrado.</p>';
        }

        // Remove campos sensíveis antes de expor no JS público.
        $public_cfg = $cfg;
        unset( $public_cfg['sms_funnel_url'], $public_cfg['sms_funnel_urls'] );

        // Enqueue + localize (apenas quando o shortcode é realmente usado).
        wp_enqueue_style( 'mgs-quiz' );
        wp_enqueue_script( 'mgs-quiz' );

        if ( isset( $cfg['layout_template'] ) && 'quiz_maker_sb' === sanitize_key( $cfg['layout_template'] ) ) {
            wp_enqueue_style( 'mgs-quiz-cabin', 'https://fonts.googleapis.com/css2?family=Cabin:wght@400;500;600&display=swap', array(), null );
        }

        $primary = ! empty( $cfg['primary_color'] ) ? $cfg['primary_color'] : '#1e8323';
        wp_add_inline_style( 'mgs-quiz', ':root{--mgs-primary:' . esc_html( $primary ) . '}' );

        wp_localize_script( 'mgs-quiz', 'MGS_QUIZ_REST', esc_url_raw( rest_url( 'mgs-quiz/v1' ) ) );
        wp_localize_script( 'mgs-quiz', 'MGS_QUIZ_CFG',  $public_cfg );

        ob_start();
        include MGS_QUIZ_PATH . 'templates/quiz-embed.php';
        return ob_get_clean();
    }
}
