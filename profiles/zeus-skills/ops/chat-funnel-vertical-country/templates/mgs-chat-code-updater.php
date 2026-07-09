<?php
/**
 * Plugin Name: MGS Chat Funnels Code Updater
 * Description: One-shot updater for MGS Chat Funnels code/template files; preserves configs/*.json.
 * Version: 2026.07.08-template
 */
if (!defined('ABSPATH')) { exit; }

function mgs_cf_code_updater_apply() {
    $base = plugin_dir_path(__FILE__);
    $target = WP_PLUGIN_DIR . '/mgs-chat-funnels/';
    $files = array(
        'mgs-chat-funnels.php',
        'templates/ciro-index-template.html',
        // Add assets/*.js or assets/*.css only when the rollout scope requires it.
        // Never add configs/*.json for code-only rollout.
    );
    $result = array('ok' => true, 'updated' => array(), 'errors' => array());
    if (!is_dir($target)) {
        $result['ok'] = false;
        $result['errors'][] = 'target plugin directory not found: ' . $target;
        update_option('mgs_cf_code_updater_result', $result, false);
        return;
    }
    foreach ($files as $rel) {
        $src = $base . 'payload/' . $rel;
        $dst = $target . $rel;
        if (!is_file($src)) {
            $result['ok'] = false;
            $result['errors'][] = 'missing payload: ' . $rel;
            continue;
        }
        if (!is_dir(dirname($dst))) {
            wp_mkdir_p(dirname($dst));
        }
        if (!copy($src, $dst)) {
            $result['ok'] = false;
            $result['errors'][] = 'copy failed: ' . $rel;
            continue;
        }
        $result['updated'][$rel] = array(
            'md5' => md5_file($dst),
            'bytes' => filesize($dst),
        );
    }
    update_option('mgs_cf_code_updater_result', $result, false);
}
register_activation_hook(__FILE__, 'mgs_cf_code_updater_apply');

add_action('admin_notices', function () {
    if (!current_user_can('manage_options')) { return; }
    $r = get_option('mgs_cf_code_updater_result');
    if (!$r) { return; }
    $class = !empty($r['ok']) ? 'notice notice-success' : 'notice notice-error';
    echo '<div class="' . esc_attr($class) . '"><p><strong>MGS Chat Funnels Code Updater:</strong> ' . esc_html(wp_json_encode($r)) . '</p></div>';
});
