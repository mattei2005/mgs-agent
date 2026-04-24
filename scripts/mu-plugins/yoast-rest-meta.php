<?php
/**
 * Plugin Name: MGS REST Meta
 * Description: Registra campos do Yoast SEO e _hide_from_home no
 *              WordPress REST API. Oculta posts marcados da home,
 *              feeds, categorias, tags, busca e archives.
 * Version: 1.0
 * Author: MGS Digital Corp
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

// ─── 1. Registra meta fields no REST API ─────────────────────────
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

// ─── 2. Oculta posts marcados no frontend ────────────────────────
add_action( 'pre_get_posts', function ( $query ) {
    if ( is_admin() ) {
        return;
    }
    if (
        $query->is_home()       ||
        $query->is_front_page() ||
        $query->is_feed()       ||
        $query->is_category()   ||
        $query->is_tag()        ||
        $query->is_search()     ||
        $query->is_archive()
    ) {
        $meta_query = $query->get( 'meta_query' );
        if ( ! is_array( $meta_query ) ) {
            $meta_query = array();
        }
        $meta_query[] = array(
            'relation' => 'OR',
            array(
                'key'     => '_hide_from_home',
                'compare' => 'NOT EXISTS',
            ),
            array(
                'key'     => '_hide_from_home',
                'value'   => '1',
                'compare' => '!=',
            ),
        );
        $query->set( 'meta_query', $meta_query );
    }
} );
