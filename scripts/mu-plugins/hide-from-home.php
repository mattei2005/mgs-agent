<?php
/**
 * Plugin Name: Hide From Home
 * Description: Hides posts with _hide_from_home meta from public listings (home, feeds, categories, tags, search, archives).
 */
add_action('init', function () {
    register_post_meta('post', '_hide_from_home', [
        'show_in_rest'   => true,
        'single'         => true,
        'type'           => 'string',
        'default'        => '',
        'auth_callback'  => function () {
            return current_user_can('edit_posts');
        },
    ]);
});
add_action('pre_get_posts', function ($query) {
    if (is_admin()) {
        return;
    }
    if (
        $query->is_home() ||
        $query->is_front_page() ||
        $query->is_feed() ||
        $query->is_category() ||
        $query->is_tag() ||
        $query->is_search() ||
        $query->is_archive()
    ) {
        $meta_query = $query->get('meta_query');
        if (!is_array($meta_query)) {
            $meta_query = [];
        }
        $meta_query[] = [
            'relation' => 'OR',
            [
                'key'     => '_hide_from_home',
                'compare' => 'NOT EXISTS',
            ],
            [
                'key'     => '_hide_from_home',
                'value'   => '1',
                'compare' => '!=',
            ],
        ];
        $query->set('meta_query', $meta_query);
    }
});
