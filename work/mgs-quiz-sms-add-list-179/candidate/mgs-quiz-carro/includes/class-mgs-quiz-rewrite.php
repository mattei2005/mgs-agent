<?php
/**
 * Rewrite: /quiz-car-parcelas[-gNNN]/ -> template do plugin.
 * Aceita qualquer slug que comece com quiz- para futuras campanhas.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

class MGS_Quiz_Rewrite {

    public static function register() {
        add_rewrite_rule( '^(quiz-[a-z0-9\-]+)/?$', 'index.php?mgs_quiz_slug=$matches[1]', 'top' );
        add_filter( 'query_vars', function( $v ) { $v[] = 'mgs_quiz_slug'; return $v; } );
        add_action( 'template_redirect', array( __CLASS__, 'maybe_render' ) );
    }

    public static function maybe_render() {
        $slug = get_query_var( 'mgs_quiz_slug' );
        if ( ! $slug ) return;

        $cfg = MGS_Quiz_REST::get_config_by_slug( sanitize_title( $slug ) );
        if ( ! $cfg ) return; // deixa o 404 padrão.

        status_header( 200 );
        nocache_headers();
        include MGS_QUIZ_PATH . 'templates/quiz-template.php';
        exit;
    }
}
