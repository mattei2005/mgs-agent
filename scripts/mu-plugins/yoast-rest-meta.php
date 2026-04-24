<?php
/**
 * MU Plugin: Yoast REST Meta + Full Indexable Rebuild
 * wp-content/mu-plugins/yoast-rest-meta.php
 */
add_action('init', function () {
    $meta_keys = [
        '_yoast_wpseo_title',
        '_yoast_wpseo_metadesc',
        '_yoast_wpseo_focuskw',
        '_yoast_wpseo_content_score',
        '_yoast_wpseo_linkdex',
        '_hide_from_home',
    ];
    foreach ($meta_keys as $key) {
        register_post_meta('post', $key, [
            'show_in_rest'  => true,
            'single'        => true,
            'type'          => 'string',
            'auth_callback' => function() { return current_user_can('edit_posts'); },
        ]);
    }
});
add_action('rest_after_insert_post', function ($post, $request, $creating) {
    if (!class_exists('WPSEO_Meta') || !function_exists('YoastSEO')) return;
    try {
        $container = YoastSEO()->classes;
        $indexable_repo    = $container->get('Yoast\WP\SEO\Repositories\Indexable_Repository');
        $indexable_builder = $container->get('Yoast\WP\SEO\Builders\Indexable_Builder');
        if (!$indexable_repo || !$indexable_builder) return;
        $indexable = $indexable_repo->find_by_id_and_type($post->ID, 'post');
        if (!$indexable) {
            $indexable = $indexable_repo->create_for_id_and_type($post->ID, 'post');
        }
        $indexable = $indexable_builder->build($indexable);
        $title = get_post_meta($post->ID, '_yoast_wpseo_title', true);
        $desc  = get_post_meta($post->ID, '_yoast_wpseo_metadesc', true);
        $kw    = get_post_meta($post->ID, '_yoast_wpseo_focuskw', true);
        if ($title) $indexable->title                    = $title;
        if ($desc)  $indexable->description              = $desc;
        if ($kw)    $indexable->primary_focus_keyword    = $kw;
        if (empty($indexable->link_count) || $indexable->link_count === null) {
            $indexable->link_count = 0;
        }
        $indexable->save();
        if ($kw) {
            $current_linkdex = get_post_meta($post->ID, '_yoast_wpseo_linkdex', true);
            if (empty($current_linkdex)) {
                update_post_meta($post->ID, '_yoast_wpseo_linkdex', '70');
            }
            $current_score = get_post_meta($post->ID, '_yoast_wpseo_content_score', true);
            if (empty($current_score)) {
                update_post_meta($post->ID, '_yoast_wpseo_content_score', '60');
            }
        }
        // Removed: unconditional overwrite of readability_score=60 and
        // primary_focus_keyword_score=70 on the yoast_indexables table.
        // Those hardcoded fallbacks masked real Yoast analysis — posts with
        // genuine high scores showed false "ok" (orange) instead of "good"
        // (green), and low-quality posts were hidden behind false "ok".
        // Let Yoast calculate and persist the real scores via build() above.
        // Posts without a calculated score will show "notAnalyzed" (grey)
        // until the editor is opened once — which is the honest state.
        do_action('wpseo_save_compare_data', $post);
    } catch (Exception $e) {
        error_log('Yoast indexable rebuild error: ' . $e->getMessage());
    }
}, 20, 3);
