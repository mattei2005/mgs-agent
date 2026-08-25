<?php
/**
 * Plugin Name: MGS Direct Quiz
 * Description: Cria e duplica landing pages simples de quiz para tráfego direto, com modelos LP1 e LP2.
 * Version: 1.0.3
 * Author: MGS Digital Corp
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

define( 'MGS_DQ_VERSION', '1.0.3' );
define( 'MGS_DQ_FILE', __FILE__ );
define( 'MGS_DQ_PATH', plugin_dir_path( __FILE__ ) );
define( 'MGS_DQ_URL', plugin_dir_url( __FILE__ ) );

require_once MGS_DQ_PATH . 'includes/class-mgs-direct-quiz.php';

register_activation_hook( __FILE__, array( 'MGS_Direct_Quiz', 'activate' ) );
register_deactivation_hook( __FILE__, array( 'MGS_Direct_Quiz', 'deactivate' ) );

MGS_Direct_Quiz::boot();
