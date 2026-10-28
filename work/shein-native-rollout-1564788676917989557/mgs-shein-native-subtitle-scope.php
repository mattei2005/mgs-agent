<?php
/**
 * Plugin Name: MGS SHEIN Native Subtitle Scope
 * Description: Keeps the tested native subtitle format limited to the approved SHEIN REC.
 */
if (!defined('ABSPATH')) {
    exit;
}
add_filter('option_jbf_secondary_title_title_format', function ($value) {
    if (is_admin() || parse_url(home_url(), PHP_URL_HOST) !== 'yolokfx.com' || (int) get_the_ID() !== 9001) {
        return $value;
    }
    if (is_singular('post') && (int) get_queried_object_id() === 9001 && in_the_loop()) {
        return "%title%<span class='jbf-native-subtitle' style='display:block;color:#5f6670;font-size:18px;line-height:1.55;font-weight:400;letter-spacing:normal;margin-top:16px;'>%jbf_secondary_title%</span>";
    }
    // Keep the REC's existing plain title on cards/lists; do not expose its subtitle there.
    return '%title%';
}, 10, 1);

add_filter('option_jbf_secondary_title_auto_show', function ($value) {
    if (!is_admin() && parse_url(home_url(), PHP_URL_HOST) === 'yolokfx.com'
        && (int) get_the_ID() === 9001 && is_singular('post')
        && (int) get_queried_object_id() === 9001 && in_the_loop()) {
        return 'on';
    }
    return $value;
}, 10, 1);
