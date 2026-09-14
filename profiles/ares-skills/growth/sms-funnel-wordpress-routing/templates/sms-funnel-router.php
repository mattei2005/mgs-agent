<?php
/**
 * Plugin Name: MGS SMS Funnel Router
 * Description: Routes SMS clicks to sequential SMS Funnel lists by var_phone and step.
 * Version: 1.0.0
 * Author: MGS Digital Corp
 * Requires at least: 6.0
 * Requires PHP: 7.4
 */

if (!defined('ABSPATH')) {
    exit;
}

const MGS_SMSF_OPTION = 'mgs_sms_funnel_router_options';

function mgs_smsf_defaults() {
    return array(
        'enabled' => 0,
        'step_01_label' => 'Disparos 2',
        'step_01_webhook' => '',
        'step_02_label' => 'Disparos 3',
        'step_02_webhook' => '',
    );
}

function mgs_smsf_options() {
    $saved = get_option(MGS_SMSF_OPTION, array());
    return wp_parse_args(is_array($saved) ? $saved : array(), mgs_smsf_defaults());
}

function mgs_smsf_sanitize($input) {
    $input = is_array($input) ? $input : array();
    return array(
        'enabled' => empty($input['enabled']) ? 0 : 1,
        'step_01_label' => sanitize_text_field($input['step_01_label'] ?? 'Disparos 2'),
        'step_01_webhook' => esc_url_raw(trim($input['step_01_webhook'] ?? ''), array('https')),
        'step_02_label' => sanitize_text_field($input['step_02_label'] ?? 'Disparos 3'),
        'step_02_webhook' => esc_url_raw(trim($input['step_02_webhook'] ?? ''), array('https')),
    );
}

function mgs_smsf_register_settings() {
    register_setting('mgs_smsf', MGS_SMSF_OPTION, array(
        'type' => 'array',
        'sanitize_callback' => 'mgs_smsf_sanitize',
        'default' => mgs_smsf_defaults(),
    ));
}
add_action('admin_init', 'mgs_smsf_register_settings');

function mgs_smsf_add_menu() {
    add_menu_page(
        'MGS SMS Funnel',
        'MGS SMS Funnel',
        'manage_options',
        'mgs-sms-funnel-router',
        'mgs_smsf_render_page',
        'dashicons-email-alt',
        30.1
    );
}
add_action('admin_menu', 'mgs_smsf_add_menu');

function mgs_smsf_render_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    $options = mgs_smsf_options();
    ?>
    <div class="wrap">
        <h1>MGS SMS Funnel</h1>
        <p>Configure a lista de destino de cada clique.</p>
        <form method="post" action="options.php">
            <?php settings_fields('mgs_smsf'); ?>
            <table class="form-table" role="presentation">
                <tr><th>Status</th><td><label><input type="checkbox" name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[enabled]" value="1" <?php checked(1, (int) $options['enabled']); ?>> Ativar encaminhamento</label></td></tr>
                <?php foreach (array('01', '02') as $step) : $key = 'step_' . $step; ?>
                    <tr>
                        <th><label for="<?php echo esc_attr($key); ?>">Step <?php echo esc_html($step); ?></label></th>
                        <td>
                            <input type="text" class="regular-text" name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[<?php echo esc_attr($key); ?>_label]" value="<?php echo esc_attr($options[$key . '_label']); ?>">
                            <input id="<?php echo esc_attr($key); ?>" type="url" class="large-text code" autocomplete="off" placeholder="https://..." name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[<?php echo esc_attr($key); ?>_webhook]" value="<?php echo esc_attr($options[$key . '_webhook']); ?>">
                        </td>
                    </tr>
                <?php endforeach; ?>
            </table>
            <?php submit_button('Salvar configurações'); ?>
        </form>
    </div>
    <?php
}

function mgs_smsf_normalize_step($value) {
    $value = trim((string) $value);
    if ($value === '' || !ctype_digit($value)) {
        return '';
    }
    $number = (int) $value;
    return ($number >= 1 && $number <= 99) ? str_pad((string) $number, 2, '0', STR_PAD_LEFT) : '';
}

function mgs_smsf_handle_click() {
    if (is_admin() || wp_doing_ajax() || wp_doing_cron() || !isset($_GET['var_phone'], $_GET['step'])) {
        return;
    }

    $phone = preg_replace('/\D+/', '', wp_unslash($_GET['var_phone']));
    $step = mgs_smsf_normalize_step(wp_unslash($_GET['step']));
    if ($phone === '' || strlen($phone) < 8 || $step === '') {
        header('X-MGS-SMS-Router: invalid-input');
        return;
    }

    $options = mgs_smsf_options();
    if (empty($options['enabled'])) {
        header('X-MGS-SMS-Router: inactive');
        return;
    }

    $routes = array(
        '01' => $options['step_01_webhook'],
        '02' => $options['step_02_webhook'],
    );
    $webhook = $routes[$step] ?? '';
    if ($webhook === '') {
        header('X-MGS-SMS-Router: route-not-configured');
        return;
    }

    $response = wp_remote_post($webhook, array(
        'timeout' => 5,
        'redirection' => 0,
        'headers' => array('Content-Type' => 'application/json'),
        'body' => wp_json_encode(array('name' => 'user', 'phone' => $phone)),
        'data_format' => 'body',
    ));

    if (is_wp_error($response)) {
        header('X-MGS-SMS-Router: delivery-error');
        return;
    }
    $status = (int) wp_remote_retrieve_response_code($response);
    header('X-MGS-SMS-Router: ' . (($status >= 200 && $status < 300) ? 'delivered' : 'delivery-rejected'));
}
add_action('template_redirect', 'mgs_smsf_handle_click', 1);
