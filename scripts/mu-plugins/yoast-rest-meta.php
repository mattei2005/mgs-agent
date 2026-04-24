<?php
/**
 * MU Plugin: Yoast REST Meta
 * File: wp-content/mu-plugins/yoast-rest-meta.php
 *
 * Registra os campos do Yoast SEO e _hide_from_home no WordPress
 * REST API para leitura e escrita via API.
 *
 * IMPORTANTE: este plugin NÃO interfere no indexable do Yoast.
 * Deixa o Yoast construir/recalcular o indexable sozinho no timing
 * dele. Qualquer interferência (mesmo $indexable_builder->build()
 * no create) introduz estado intermediário que causa piscar no
 * editor ao dar F5.
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

add_action( 'init', function () {
    $meta_fields = array(
        '_yoast_wpseo_focuskw'  => array(
            'type'        => 'string',
            'description' => 'Yoast SEO Focus Keyphrase',
            'single'      => true,
            'default'     => '',
        ),
        '_yoast_wpseo_metadesc' => array(
            'type'        => 'string',
            'description' => 'Yoast SEO Meta Description',
            'single'      => true,
            'default'     => '',
        ),
        '_yoast_wpseo_title'    => array(
            'type'        => 'string',
            'description' => 'Yoast SEO Title',
            'single'      => true,
            'default'     => '',
        ),
        '_hide_from_home'       => array(
            'type'        => 'string',
            'description' => 'Hide From Home - ocultar da home e feeds',
            'single'      => true,
            'default'     => '',
        ),
    );

    foreach ( $meta_fields as $meta_key => $args ) {
        register_post_meta( 'post', $meta_key, array(
            'type'          => $args['type'],
            'description'   => $args['description'],
            'single'        => $args['single'],
            'default'       => $args['default'],
            'show_in_rest'  => true,
            'auth_callback' => function () {
                return current_user_can( 'edit_posts' );
            },
        ) );
    }
} );
