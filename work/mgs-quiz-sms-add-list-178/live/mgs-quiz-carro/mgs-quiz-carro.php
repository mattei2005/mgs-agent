<?php
/**
 * Plugin Name: MGS Quiz Carro
 * Description: Quiz de captação de leads (crédito veicular) com integração SMS Funnel. Autônomo, sem dependência externa.
 * Version:     1.7.7
 * Author:      MGS Digital Corp
 * License:     GPLv2 or later
 * Text Domain: mgs-quiz-carro
 * Requires PHP: 7.2
 * Requires at least: 5.6
 *
 * @package MGSQuizCarro
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

define( 'MGS_QUIZ_VERSION', '1.7.7' );
define( 'MGS_QUIZ_PATH', plugin_dir_path( __FILE__ ) );
define( 'MGS_QUIZ_URL', plugin_dir_url( __FILE__ ) );
define( 'MGS_QUIZ_DB_VERSION', '1.3.0' );

require_once MGS_QUIZ_PATH . 'includes/class-mgs-quiz-activator.php';
require_once MGS_QUIZ_PATH . 'includes/class-mgs-quiz-rest.php';
require_once MGS_QUIZ_PATH . 'includes/class-mgs-quiz-shortcode.php';
require_once MGS_QUIZ_PATH . 'includes/class-mgs-quiz-rewrite.php';
require_once MGS_QUIZ_PATH . 'includes/class-mgs-quiz-admin.php';
require_once MGS_QUIZ_PATH . 'includes/class-mgs-quiz-csv.php';

register_activation_hook( __FILE__, array( 'MGS_Quiz_Activator', 'activate' ) );
register_deactivation_hook( __FILE__, array( 'MGS_Quiz_Activator', 'deactivate' ) );

add_action( 'plugins_loaded', function () {
    if ( get_option( 'mgs_quiz_db_version' ) !== MGS_QUIZ_DB_VERSION ) {
        MGS_Quiz_Activator::activate();
    }
} );

add_action( 'init',          array( 'MGS_Quiz_Rewrite',   'register' ) );
add_action( 'init',          array( 'MGS_Quiz_Shortcode', 'register' ) );
add_action( 'rest_api_init', array( 'MGS_Quiz_REST',      'register' ) );
add_action( 'admin_menu',    array( 'MGS_Quiz_Admin',     'register_menu' ) );
add_action( 'admin_init',    array( 'MGS_Quiz_Admin',     'handle_post' ) );
add_action( 'wp_ajax_mgs_quiz_chart_days', array( 'MGS_Quiz_Admin', 'ajax_chart_days' ) );
add_action( 'wp_ajax_mgs_quiz_report_leads', array( 'MGS_Quiz_Admin', 'ajax_report_leads' ) );
add_action( 'admin_post_mgs_quiz_export_leads',  array( 'MGS_Quiz_CSV', 'export_leads' ) );
add_action( 'admin_post_mgs_quiz_import_config', array( 'MGS_Quiz_CSV', 'import_config' ) );

// Registra assets públicos (uma única vez). O carregamento real é feito pelo
// shortcode e pelo template público (rewrite) sob demanda.
add_action( 'wp_enqueue_scripts', function () {
    wp_register_style(
        'mgs-quiz',
        MGS_QUIZ_URL . 'public/css/quiz.css',
        array(),
        MGS_QUIZ_VERSION
    );
    wp_register_script(
        'mgs-quiz',
        MGS_QUIZ_URL . 'public/js/quiz.js',
        array(),
        MGS_QUIZ_VERSION,
        true
    );
} );
