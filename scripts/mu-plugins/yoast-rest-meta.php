<?php
/**
 * MU Plugin: Yoast REST Meta + Indexable Refresh
 * File: wp-content/mu-plugins/yoast-rest-meta.php
 *
 * Expõe via REST apenas os INPUTS do usuário (title, metadesc, focuskw, _hide_from_home).
 * Os scores (_yoast_wpseo_linkdex e _yoast_wpseo_content_score) NÃO são expostos,
 * pois são OUTPUTS calculados pelo próprio Yoast — deixar eles graváveis via REST
 * causa valores stale que fazem o editor piscar (vermelho → laranja) no load.
 *
 * O build() do indexable só roda no CREATE ($creating === true). Em updates
 * subsequentes (quando o JS do Yoast salva um novo score), o build não roda
 * e portanto não sobrescreve o score real calculado pelo frontend do Yoast.
 */
add_action('init', function () {
    $meta_keys = [
        '_yoast_wpseo_title',
        '_yoast_wpseo_metadesc',
        '_yoast_wpseo_focuskw',
        '_hide_from_home',
    ];
    foreach ($meta_keys as $key) {
        register_post_meta('post', $key, [
            'show_in_rest'  => true,
            'single'        => true,
            'type'          => 'string',
            'auth_callback' => function () { return current_user_can('edit_posts'); },
        ]);
    }
});
add_action('rest_after_insert_post', function ($post, $request, $creating) {
    if (!class_exists('WPSEO_Meta') || !function_exists('YoastSEO')) return;
    try {
        $container         = YoastSEO()->classes;
        $indexable_repo    = $container->get('Yoast\WP\SEO\Repositories\Indexable_Repository');
        $indexable_builder = $container->get('Yoast\WP\SEO\Builders\Indexable_Builder');
        if (!$indexable_repo || !$indexable_builder) return;
        $indexable = $indexable_repo->find_by_id_and_type($post->ID, 'post');
        if (!$indexable) {
            $indexable = $indexable_repo->create_for_id_and_type($post->ID, 'post');
        }
        if ($creating) {
            $indexable = $indexable_builder->build($indexable);
        }
        $title = get_post_meta($post->ID, '_yoast_wpseo_title', true);
        $desc  = get_post_meta($post->ID, '_yoast_wpseo_metadesc', true);
        $kw    = get_post_meta($post->ID, '_yoast_wpseo_focuskw', true);
        if ($title) $indexable->title                 = $title;
        if ($desc)  $indexable->description           = $desc;
        if ($kw)    $indexable->primary_focus_keyword = $kw;
        if (empty($indexable->link_count)) {
            $indexable->link_count = 0;
        }
        $indexable->save();
    } catch (Exception $e) {
        error_log('Yoast indexable rebuild error: ' . $e->getMessage());
    }
}, 20, 3);
