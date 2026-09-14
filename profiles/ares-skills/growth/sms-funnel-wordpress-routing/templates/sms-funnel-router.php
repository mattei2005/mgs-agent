<?php
/**
 * Plugin Name: MGS SMS Funnel Router
 * Description: Encaminha cliques de SMS por gestor e etapa usando utm_medium, var_phone e step.
 * Version: 1.1.0
 * Author: MGS Digital Corp
 * Requires at least: 6.0
 * Requires PHP: 7.4
 */

if (!defined('ABSPATH')) {
    exit;
}

const MGS_SMSF_OPTION = 'mgs_sms_funnel_router_options';
const MGS_SMSF_SCHEMA_VERSION = 2;

function mgs_smsf_group_keys() {
    return array('g001', 'g002', 'g003', 'g004', 'g005', 'g006');
}

function mgs_smsf_group_defaults($group) {
    return array(
        'enabled' => 0,
        'label' => strtoupper($group),
        'utm_medium' => $group . '-s',
        'step_01_label' => 'Disparos 2',
        'step_01_webhook' => '',
        'step_02_label' => 'Disparos 3',
        'step_02_webhook' => '',
    );
}

function mgs_smsf_defaults() {
    $groups = array();
    foreach (mgs_smsf_group_keys() as $group) {
        $groups[$group] = mgs_smsf_group_defaults($group);
    }
    return array('schema_version' => MGS_SMSF_SCHEMA_VERSION, 'enabled' => 0, 'groups' => $groups);
}

function mgs_smsf_normalize_saved_options($saved) {
    $defaults = mgs_smsf_defaults();
    if (!is_array($saved)) {
        return $defaults;
    }
    $normalized = $defaults;
    $normalized['enabled'] = empty($saved['enabled']) ? 0 : 1;
    if (isset($saved['groups']) && is_array($saved['groups'])) {
        foreach (mgs_smsf_group_keys() as $group) {
            $stored = isset($saved['groups'][$group]) && is_array($saved['groups'][$group]) ? $saved['groups'][$group] : array();
            $normalized['groups'][$group] = wp_parse_args($stored, mgs_smsf_group_defaults($group));
            $normalized['groups'][$group]['label'] = strtoupper($group);
            $normalized['groups'][$group]['utm_medium'] = $group . '-s';
            $normalized['groups'][$group]['enabled'] = empty($normalized['groups'][$group]['enabled']) ? 0 : 1;
        }
        return $normalized;
    }
    $normalized['groups']['g002']['enabled'] = $normalized['enabled'];
    $normalized['groups']['g002']['step_01_label'] = (string) ($saved['step_01_label'] ?? 'Disparos 2');
    $normalized['groups']['g002']['step_01_webhook'] = (string) ($saved['step_01_webhook'] ?? '');
    $normalized['groups']['g002']['step_02_label'] = (string) ($saved['step_02_label'] ?? 'Disparos 3');
    $normalized['groups']['g002']['step_02_webhook'] = (string) ($saved['step_02_webhook'] ?? '');
    return $normalized;
}

function mgs_smsf_get_options() {
    return mgs_smsf_normalize_saved_options(get_option(MGS_SMSF_OPTION, array()));
}

function mgs_smsf_migrate_options() {
    $saved = get_option(MGS_SMSF_OPTION, array());
    if (!is_array($saved) || !isset($saved['groups']) || !is_array($saved['groups'])) {
        update_option(MGS_SMSF_OPTION, mgs_smsf_normalize_saved_options($saved), false);
    }
}
add_action('plugins_loaded', 'mgs_smsf_migrate_options', 5);

function mgs_smsf_sanitize_options($input) {
    $input = is_array($input) ? $input : array();
    $options = mgs_smsf_get_options();
    $scope = sanitize_key($input['_scope'] ?? '');
    if ($scope === 'master') {
        $options['enabled'] = empty($input['enabled']) ? 0 : 1;
        return $options;
    }
    if (strpos($scope, 'group_') !== 0) {
        return $options;
    }
    $group = substr($scope, 6);
    if (!in_array($group, mgs_smsf_group_keys(), true)) {
        return $options;
    }
    $group_input = isset($input['groups'][$group]) && is_array($input['groups'][$group]) ? $input['groups'][$group] : array();
    $options['groups'][$group]['enabled'] = empty($group_input['enabled']) ? 0 : 1;
    $options['groups'][$group]['step_01_label'] = sanitize_text_field($group_input['step_01_label'] ?? 'Disparos 2');
    $options['groups'][$group]['step_01_webhook'] = esc_url_raw(trim($group_input['step_01_webhook'] ?? ''), array('https'));
    $options['groups'][$group]['step_02_label'] = sanitize_text_field($group_input['step_02_label'] ?? 'Disparos 3');
    $options['groups'][$group]['step_02_webhook'] = esc_url_raw(trim($group_input['step_02_webhook'] ?? ''), array('https'));
    $options['schema_version'] = MGS_SMSF_SCHEMA_VERSION;
    return $options;
}

function mgs_smsf_register_settings() {
    register_setting('mgs_sms_funnel_router', MGS_SMSF_OPTION, array(
        'type' => 'array',
        'sanitize_callback' => 'mgs_smsf_sanitize_options',
        'default' => mgs_smsf_defaults(),
    ));
}
add_action('admin_init', 'mgs_smsf_register_settings');

function mgs_smsf_add_settings_pages() {
    add_menu_page('MGS SMS Funnel', 'MGS SMS Funnel', 'manage_options', 'mgs-sms-funnel-router', 'mgs_smsf_render_overview_page', 'dashicons-email-alt', 30.1);
    add_submenu_page('mgs-sms-funnel-router', 'MGS SMS Funnel — Visão geral', 'Visão geral', 'manage_options', 'mgs-sms-funnel-router', 'mgs_smsf_render_overview_page');
    foreach (mgs_smsf_group_keys() as $group) {
        add_submenu_page('mgs-sms-funnel-router', 'MGS SMS Funnel — ' . strtoupper($group), strtoupper($group), 'manage_options', 'mgs-sms-funnel-router-' . $group, 'mgs_smsf_render_group_page');
    }
}
add_action('admin_menu', 'mgs_smsf_add_settings_pages');

function mgs_smsf_render_overview_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    $options = mgs_smsf_get_options();
    ?>
    <div class="wrap">
        <h1>MGS SMS Funnel</h1>
        <p>O roteamento usa obrigatoriamente <code>utm_medium + step</code> para separar G001–G006.</p>
        <form method="post" action="options.php">
            <?php settings_fields('mgs_sms_funnel_router'); ?>
            <input type="hidden" name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[_scope]" value="master">
            <table class="form-table" role="presentation"><tr><th scope="row">Status geral</th><td><label><input type="checkbox" name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[enabled]" value="1" <?php checked(1, (int) $options['enabled']); ?>> Ativar roteador no site</label></td></tr></table>
            <?php submit_button('Salvar status geral'); ?>
        </form>
        <h2>Gestores</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;max-width:1100px;">
            <?php foreach (mgs_smsf_group_keys() as $group) : $config = $options['groups'][$group]; $configured = $config['step_01_webhook'] !== '' && $config['step_02_webhook'] !== ''; ?>
                <div style="background:#fff;border:1px solid #dcdcde;border-left:4px solid <?php echo !empty($config['enabled']) ? '#00a32a' : '#8c8f94'; ?>;padding:14px;">
                    <h3 style="margin-top:0;"><?php echo esc_html(strtoupper($group)); ?></h3>
                    <p><code>utm_medium=<?php echo esc_html($config['utm_medium']); ?></code></p>
                    <p>Status: <strong><?php echo !empty($config['enabled']) ? 'Ativo' : 'Desativado'; ?></strong><br>Webhooks: <strong><?php echo $configured ? '2/2 configurados' : (($config['step_01_webhook'] !== '' || $config['step_02_webhook'] !== '') ? '1/2 configurado' : '0/2 configurados'); ?></strong></p>
                    <a class="button" href="<?php echo esc_url(admin_url('admin.php?page=mgs-sms-funnel-router-' . $group)); ?>">Abrir painel <?php echo esc_html(strtoupper($group)); ?></a>
                </div>
            <?php endforeach; ?>
        </div>
    </div>
    <?php
}

function mgs_smsf_current_group() {
    $page = sanitize_key($_GET['page'] ?? '');
    foreach (mgs_smsf_group_keys() as $group) {
        if ($page === 'mgs-sms-funnel-router-' . $group) {
            return $group;
        }
    }
    return '';
}

function mgs_smsf_render_group_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    $group = mgs_smsf_current_group();
    if ($group === '') {
        return;
    }
    $options = mgs_smsf_get_options();
    $config = $options['groups'][$group];
    $field_base = MGS_SMSF_OPTION . '[groups][' . $group . ']';
    ?>
    <div class="wrap">
        <h1>MGS SMS Funnel — <?php echo esc_html(strtoupper($group)); ?></h1>
        <p>Este painel atende somente links com <code>utm_medium=<?php echo esc_html($config['utm_medium']); ?></code>.</p>
        <?php if (empty($options['enabled'])) : ?><div class="notice notice-warning"><p>O roteador geral está desativado. Ative-o na Visão geral após conferir as rotas.</p></div><?php endif; ?>
        <form method="post" action="options.php">
            <?php settings_fields('mgs_sms_funnel_router'); ?>
            <input type="hidden" name="<?php echo esc_attr(MGS_SMSF_OPTION); ?>[_scope]" value="group_<?php echo esc_attr($group); ?>">
            <table class="form-table" role="presentation">
                <tr><th scope="row">Status <?php echo esc_html(strtoupper($group)); ?></th><td><label><input type="checkbox" name="<?php echo esc_attr($field_base); ?>[enabled]" value="1" <?php checked(1, (int) $config['enabled']); ?>> Ativar encaminhamento deste gestor</label><p class="description">Só ative após preencher e conferir os dois webhooks deste gestor.</p></td></tr>
                <?php foreach (array('01' => 'Disparos 2', '02' => 'Disparos 3') as $step => $default_label) : $key = 'step_' . $step; ?>
                    <tr><th scope="row"><label for="mgs-smsf-<?php echo esc_attr($group . '-' . $step); ?>">Step <?php echo esc_html($step); ?></label></th><td>
                        <input type="text" class="regular-text" name="<?php echo esc_attr($field_base); ?>[<?php echo esc_attr($key); ?>_label]" value="<?php echo esc_attr($config[$key . '_label']); ?>">
                        <p class="description">Nome da lista de destino. Padrão: <?php echo esc_html($default_label); ?>.</p>
                        <input id="mgs-smsf-<?php echo esc_attr($group . '-' . $step); ?>" type="url" class="large-text code" name="<?php echo esc_attr($field_base); ?>[<?php echo esc_attr($key); ?>_webhook]" value="<?php echo esc_attr($config[$key . '_webhook']); ?>" placeholder="https://..." autocomplete="off">
                        <p class="description">Cole a URL de integração da lista <?php echo esc_html($default_label); ?> do <?php echo esc_html(strtoupper($group)); ?>.</p>
                    </td></tr>
                <?php endforeach; ?>
            </table>
            <?php submit_button('Salvar ' . strtoupper($group)); ?>
        </form>
        <hr><h2>Como usar nos links</h2>
        <p><code>utm_medium=<?php echo esc_html($config['utm_medium']); ?>&amp;step=01</code> encaminha para <strong><?php echo esc_html($config['step_01_label']); ?></strong>.</p>
        <p><code>utm_medium=<?php echo esc_html($config['utm_medium']); ?>&amp;step=02</code> encaminha para <strong><?php echo esc_html($config['step_02_label']); ?></strong>.</p>
        <p><code>step=03</code> permanece sem ação até ser configurada uma futura Lista 4.</p>
        <p>Na SMS Funnel, mantenha habilitada a opção <strong>Enviar número do lead na URL</strong>. O plugin recebe <code>var_phone</code> automaticamente.</p>
    </div>
    <?php
}

function mgs_smsf_plugin_action_links($links) {
    array_unshift($links, sprintf('<a href="%s">Configurar</a>', esc_url(admin_url('admin.php?page=mgs-sms-funnel-router'))));
    return $links;
}
add_filter('plugin_action_links_' . plugin_basename(__FILE__), 'mgs_smsf_plugin_action_links');

function mgs_smsf_normalize_step($raw_step) {
    $raw_step = trim((string) $raw_step);
    if ($raw_step === '' || !ctype_digit($raw_step)) {
        return '';
    }
    $number = (int) $raw_step;
    return ($number >= 1 && $number <= 99) ? str_pad((string) $number, 2, '0', STR_PAD_LEFT) : '';
}

function mgs_smsf_normalize_medium($raw_medium) {
    $medium = strtolower(trim((string) $raw_medium));
    if (!preg_match('/^g00[1-6]-s$/', $medium)) {
        return '';
    }
    return substr($medium, 0, 4);
}

function mgs_smsf_handle_click() {
    if (is_admin() || wp_doing_ajax() || wp_doing_cron() || !isset($_GET['var_phone'], $_GET['step'])) {
        return;
    }
    $phone = preg_replace('/\D+/', '', wp_unslash($_GET['var_phone']));
    $step = mgs_smsf_normalize_step(wp_unslash($_GET['step']));
    $group = mgs_smsf_normalize_medium(wp_unslash($_GET['utm_medium'] ?? ''));
    if ($phone === '' || strlen($phone) < 8 || $step === '') {
        header('X-MGS-SMS-Router: invalid-input');
        return;
    }
    if ($group === '') {
        header('X-MGS-SMS-Router: invalid-medium');
        return;
    }
    $options = mgs_smsf_get_options();
    if (empty($options['enabled'])) {
        header('X-MGS-SMS-Router: inactive');
        return;
    }
    $group_options = $options['groups'][$group] ?? array();
    if (empty($group_options['enabled'])) {
        header('X-MGS-SMS-Router: group-inactive');
        return;
    }
    $routes = array('01' => (string) ($group_options['step_01_webhook'] ?? ''), '02' => (string) ($group_options['step_02_webhook'] ?? ''));
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
        error_log('MGS SMS Funnel Router: falha ao enviar webhook de ' . strtoupper($group) . ' step ' . $step . '.');
        return;
    }
    $status_code = (int) wp_remote_retrieve_response_code($response);
    if ($status_code < 200 || $status_code >= 300) {
        header('X-MGS-SMS-Router: delivery-rejected');
        error_log('MGS SMS Funnel Router: webhook de ' . strtoupper($group) . ' step ' . $step . ' respondeu HTTP ' . $status_code . '.');
        return;
    }
    header('X-MGS-SMS-Router: delivered');
}
add_action('template_redirect', 'mgs_smsf_handle_click', 1);
