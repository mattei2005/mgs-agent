<?php
/**
 * Plugin Name: MGS Offer Quiz
 * Description: Publica quizzes estáticas de oferta por gestor, sem captação de leads, com preservação de parâmetros.
 * Version: 1.4.1
 * Author: MGS Digital Corp
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

define( 'MGS_OQ_VERSION', '1.4.1' );
define( 'MGS_OQ_FILE', __FILE__ );
define( 'MGS_OQ_PATH', plugin_dir_path( __FILE__ ) );

require_once MGS_OQ_PATH . 'includes/class-mgs-offer-quiz.php';

register_activation_hook( __FILE__, array( 'MGS_Offer_Quiz', 'activate' ) );
register_deactivation_hook( __FILE__, array( 'MGS_Offer_Quiz', 'deactivate' ) );

MGS_Offer_Quiz::boot();
