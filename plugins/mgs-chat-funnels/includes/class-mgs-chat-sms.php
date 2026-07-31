<?php
/**
 * Captura de leads e integração SMS Funnel para o MGS Chat Funnels.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

final class MGS_Chat_SMS {
    const DB_VERSION = '1.0.0';
    const DB_OPTION  = 'mgs_chat_sms_db_version';
    const SMS_OPTION = 'mgs_cf_sms_managers';
    const REST_NS    = 'mgs-chat/v1';
    const MIN_FILL_MS = 3000;
    const BUSINESS_TIMEZONE = 'America/Sao_Paulo';

    public static function boot() {
        add_action( 'plugins_loaded', array( __CLASS__, 'maybe_upgrade' ) );
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest' ) );
        add_action( 'admin_post_mgs_cf_save_sms', array( __CLASS__, 'save_sms_settings' ) );
        add_action( 'admin_post_mgs_cf_export_leads', array( __CLASS__, 'export_leads' ) );
    }

    public static function maybe_upgrade() {
        if ( get_option( self::DB_OPTION ) !== self::DB_VERSION ) {
            self::install_schema();
        }
    }

    public static function install_schema() {
        global $wpdb;
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        $table = self::table_name();
        $charset = $wpdb->get_charset_collate();
        $sql = "CREATE TABLE {$table} (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            chat_id VARCHAR(190) NOT NULL,
            route VARCHAR(255) NULL,
            manager_code VARCHAR(32) NULL,
            name VARCHAR(200) NOT NULL,
            phone VARCHAR(32) NOT NULL,
            utm_source VARCHAR(190) NULL,
            utm_medium VARCHAR(190) NULL,
            utm_campaign VARCHAR(190) NULL,
            utm_term VARCHAR(190) NULL,
            utm_content VARCHAR(190) NULL,
            fbclid VARCHAR(255) NULL,
            gclid VARCHAR(255) NULL,
            extra_params LONGTEXT NULL,
            ip VARCHAR(64) NULL,
            user_agent TEXT NULL,
            sms_funnel_status VARCHAR(40) NULL,
            sms_funnel_response TEXT NULL,
            PRIMARY KEY (id),
            KEY idx_chat (chat_id),
            KEY idx_phone (phone),
            KEY idx_created (created_at),
            KEY idx_manager (manager_code)
        ) {$charset};";
        dbDelta( $sql );
        update_option( self::DB_OPTION, self::DB_VERSION, false );
    }

    private static function table_name() {
        global $wpdb;
        return $wpdb->prefix . 'mgs_chat_leads';
    }

    public static function business_timezone() {
        return new DateTimeZone( self::BUSINESS_TIMEZONE );
    }

    public static function local_date_bound_to_utc( $date, $next_day = false ) {
        $date = trim( (string) $date );
        if ( ! preg_match( '/^\d{4}-\d{2}-\d{2}$/', $date ) ) return '';
        $local = DateTimeImmutable::createFromFormat( '!Y-m-d', $date, self::business_timezone() );
        $errors = DateTimeImmutable::getLastErrors();
        if ( ! $local || ( is_array( $errors ) && ( $errors['warning_count'] || $errors['error_count'] ) ) ) return '';
        if ( $next_day ) $local = $local->modify( '+1 day' );
        return $local->setTimezone( new DateTimeZone( 'UTC' ) )->format( 'Y-m-d H:i:s' );
    }

    public static function format_created_at( $created_at, $format = 'd/m/Y, H:i' ) {
        try {
            $utc = new DateTimeImmutable( (string) $created_at, new DateTimeZone( 'UTC' ) );
            return wp_date( $format, $utc->getTimestamp(), self::business_timezone() );
        } catch ( Exception $e ) {
            return (string) $created_at;
        }
    }

    private static function local_date_sql( $column = 'created_at' ) {
        return "DATE(CONVERT_TZ({$column}, '+00:00', '-03:00'))";
    }

    private static function default_managers() {
        return array(
            'G001' => array( 'code' => 'G001', 'label' => 'G001 – Icaro',   'url' => '' ),
            'G002' => array( 'code' => 'G002', 'label' => 'G002 – Geizian', 'url' => '' ),
            'G003' => array( 'code' => 'G003', 'label' => 'G003 – Isliago', 'url' => '' ),
            'G004' => array( 'code' => 'G004', 'label' => 'G004 – Joe',     'url' => '' ),
            'G005' => array( 'code' => 'G005', 'label' => 'G005 – Kelly',   'url' => '' ),
            'G006' => array( 'code' => 'G006', 'label' => 'G006 – Nicolas', 'url' => '' ),
        );
    }

    public static function managers() {
        $defaults = self::default_managers();
        $saved = get_option( self::SMS_OPTION, array() );
        if ( ! is_array( $saved ) ) return $defaults;
        foreach ( $defaults as $code => $default ) {
            if ( empty( $saved[ $code ] ) || ! is_array( $saved[ $code ] ) ) continue;
            $label = sanitize_text_field( $saved[ $code ]['label'] ?? '' );
            $url = esc_url_raw( $saved[ $code ]['url'] ?? '' );
            $defaults[ $code ] = array(
                'code'  => $code,
                'label' => $label !== '' ? $label : $default['label'],
                'url'   => self::is_valid_sms_url( $url ) ? $url : '',
            );
        }
        return $defaults;
    }

    public static function manager_options() {
        $out = array();
        foreach ( self::managers() as $code => $manager ) {
            $suffix = $manager['url'] !== '' ? ' — URL configurada' : ' — sem URL';
            $out[ $code ] = $manager['label'] . $suffix;
        }
        return $out;
    }

    public static function manager_is_configured( $code ) {
        $code = strtoupper( sanitize_text_field( (string) $code ) );
        $managers = self::managers();
        return isset( $managers[ $code ] ) && self::is_valid_sms_url( $managers[ $code ]['url'] );
    }

    public static function is_valid_sms_url( $url ) {
        if ( ! is_string( $url ) || trim( $url ) === '' ) return false;
        $parts = wp_parse_url( trim( $url ) );
        if ( ! is_array( $parts ) ) return false;
        if ( 'https' !== strtolower( $parts['scheme'] ?? '' ) ) return false;
        if ( 'v2.smsfunnel.com.br' !== strtolower( $parts['host'] ?? '' ) ) return false;
        return (bool) preg_match( '#^/integrations/lists/[a-f0-9-]+/add-lead/?$#i', $parts['path'] ?? '' );
    }

    public static function save_sms_settings() {
        if ( ! current_user_can( 'manage_options' ) ) wp_die( 'forbidden' );
        check_admin_referer( 'mgs_cf_save_sms' );
        $labels = isset( $_POST['sms_labels'] ) && is_array( $_POST['sms_labels'] ) ? wp_unslash( $_POST['sms_labels'] ) : array();
        $urls = isset( $_POST['sms_urls'] ) && is_array( $_POST['sms_urls'] ) ? wp_unslash( $_POST['sms_urls'] ) : array();
        $saved = array();
        foreach ( self::default_managers() as $code => $default ) {
            $label = sanitize_text_field( $labels[ $code ] ?? $default['label'] );
            $url = esc_url_raw( $urls[ $code ] ?? '' );
            if ( $label === '' || ( $url !== '' && ! self::is_valid_sms_url( $url ) ) ) {
                wp_safe_redirect( admin_url( 'admin.php?page=mgs-chat-funnels-sms&sms_error=invalid&code=' . rawurlencode( $code ) ) );
                exit;
            }
            $saved[ $code ] = array( 'code' => $code, 'label' => $label, 'url' => $url );
        }
        $before = get_option( self::SMS_OPTION, array() );
        if ( $before !== $saved && ! update_option( self::SMS_OPTION, $saved, false ) ) {
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-chat-funnels-sms&sms_error=db' ) );
            exit;
        }
        $readback = get_option( self::SMS_OPTION, array() );
        if ( $readback !== $saved ) {
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-chat-funnels-sms&sms_error=readback' ) );
            exit;
        }
        wp_safe_redirect( admin_url( 'admin.php?page=mgs-chat-funnels-sms&saved=1' ) );
        exit;
    }

    public static function render_sms_settings_page() {
        if ( ! current_user_can( 'manage_options' ) ) wp_die( 'forbidden' );
        $managers = self::managers();
        echo '<div class="wrap mgs-cf-sms-settings"><h1>SMS Funnel</h1><p>Cadastre a URL <code>add-lead</code> de cada gestor. Cada chat SMS escolhe um único gestor, independentemente das UTMs.</p>';
        if ( ! empty( $_GET['saved'] ) ) echo '<div class="notice notice-success"><p>Configurações SMS salvas.</p></div>';
        if ( ! empty( $_GET['sms_error'] ) ) echo '<div class="notice notice-error"><p>Não foi possível salvar. Use uma URL HTTPS válida do SMS Funnel terminando em <code>/add-lead</code>, ou deixe o campo vazio.</p></div>';
        echo '<style>.mgs-cf-sms-settings{max-width:1280px}.mgs-cf-sms-grid{display:grid;gap:14px;margin:20px 0}.mgs-cf-sms-row{display:grid;grid-template-columns:100px 280px minmax(440px,1fr);gap:14px;align-items:end;background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:16px}.mgs-cf-sms-row label{display:block;font-weight:700;margin-bottom:6px}.mgs-cf-sms-code{font-size:18px;font-weight:800;color:#15803d;padding:12px 0}.mgs-cf-sms-row input{width:100%;min-height:46px;border:1px solid #d0d5dd;border-radius:10px;padding:10px 12px;font-size:15px}@media(max-width:960px){.mgs-cf-sms-row{grid-template-columns:1fr}}</style>';
        echo '<form method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">';
        wp_nonce_field( 'mgs_cf_save_sms' );
        echo '<input type="hidden" name="action" value="mgs_cf_save_sms"><div class="mgs-cf-sms-grid">';
        foreach ( $managers as $code => $manager ) {
            echo '<div class="mgs-cf-sms-row"><div><label>Gestor</label><div class="mgs-cf-sms-code">' . esc_html( $code ) . '</div></div>';
            echo '<div><label for="sms-label-' . esc_attr( $code ) . '">Nome/label</label><input id="sms-label-' . esc_attr( $code ) . '" name="sms_labels[' . esc_attr( $code ) . ']" required value="' . esc_attr( $manager['label'] ) . '"></div>';
            echo '<div><label for="sms-url-' . esc_attr( $code ) . '">URL add-lead</label><input id="sms-url-' . esc_attr( $code ) . '" type="url" name="sms_urls[' . esc_attr( $code ) . ']" value="' . esc_attr( $manager['url'] ) . '" placeholder="https://v2.smsfunnel.com.br/integrations/lists/.../add-lead"></div></div>';
        }
        echo '</div>'; submit_button( 'Salvar configurações SMS' ); echo '</form></div>';
    }

    public static function public_config( $config ) {
        if ( ! is_array( $config ) ) return $config;
        $enabled = ! empty( $config['sms_enabled'] );
        $config['sms_enabled'] = $enabled;
        if ( $enabled ) {
            $config['sms_rest_url'] = rest_url( self::REST_NS . '/lead' );
            $config['sms_name_label'] = sanitize_text_field( $config['sms_name_label'] ?? 'Nome' );
            $config['sms_phone_label'] = sanitize_text_field( $config['sms_phone_label'] ?? 'Telefone' );
            $config['sms_submit_label'] = sanitize_text_field( $config['sms_submit_label'] ?? 'TRANSFERIR PARA ESPECIALISTA →' );
            $config['sms_optional'] = ! empty( $config['sms_optional'] );
            $config['sms_skip_label'] = sanitize_text_field( $config['sms_skip_label'] ?? 'Pular, quero ver as ofertas' );
            $config['sms_consent_enabled'] = ! empty( $config['sms_consent_enabled'] );
            $config['sms_consent_default'] = ! empty( $config['sms_consent_default'] );
            $config['sms_consent_label'] = sanitize_text_field( $config['sms_consent_label'] ?? 'Aceito receber ofertas por SMS.' );
        }
        unset( $config['sms_manager_code'] );
        return $config;
    }

    public static function form_html( $config ) {
        if ( empty( $config['sms_enabled'] ) ) return '';
        $name_label = sanitize_text_field( $config['sms_name_label'] ?? 'Nome' );
        $phone_label = sanitize_text_field( $config['sms_phone_label'] ?? 'Telefone' );
        $consent = '';
        if ( ! empty( $config['sms_consent_enabled'] ) ) {
            $checked = ! empty( $config['sms_consent_default'] ) ? ' checked' : '';
            $consent_label = sanitize_text_field( $config['sms_consent_label'] ?? 'Aceito receber ofertas por SMS.' );
            $consent = '<label class="mgs-cf-sms-consent" for="mgs-cf-sms-consent">'
                . '<input id="mgs-cf-sms-consent" type="checkbox"' . $checked . '>'
                . '<span>' . esc_html( $consent_label ) . '</span></label>';
        }
        return '<div class="mgs-cf-sms-form" id="mgs-cf-sms-form">'
            . '<label for="mgs-cf-sms-name">' . esc_html( $name_label ) . '</label>'
            . '<input id="mgs-cf-sms-name" name="name" type="text" autocomplete="name" maxlength="200" placeholder="Digite seu nome" required>'
            . '<label for="mgs-cf-sms-phone">' . esc_html( $phone_label ) . '</label>'
            . '<input id="mgs-cf-sms-phone" name="phone" type="tel" inputmode="numeric" autocomplete="tel" maxlength="20" placeholder="(11) 99999-9999" required>'
            . $consent
            . '<input id="mgs-cf-sms-website" type="text" tabindex="-1" autocomplete="off" aria-hidden="true">'
            . '<p id="mgs-cf-sms-error" class="mgs-cf-sms-error" role="alert" aria-live="polite"></p>'
            . '</div>';
    }

    public static function skip_html( $config ) {
        if ( empty( $config['sms_enabled'] ) || empty( $config['sms_optional'] ) ) return '';
        $label = sanitize_text_field( $config['sms_skip_label'] ?? 'Pular, quero ver as ofertas' );
        return '<button id="mgs-cf-sms-skip" type="button">' . esc_html( $label ) . '</button>';
    }

    public static function template_js_config( $config ) {
        $public = self::public_config( $config );
        $data = array(
            'enabled' => ! empty( $public['sms_enabled'] ),
            'endpoint' => $public['sms_rest_url'] ?? '',
            'chatId' => $config['id'] ?? '',
            'route' => $config['route'] ?? '',
            'submitLabel' => $public['sms_submit_label'] ?? 'TRANSFERIR PARA ESPECIALISTA →',
            'optional' => ! empty( $public['sms_optional'] ),
            'consentEnabled' => ! empty( $public['sms_consent_enabled'] ),
        );
        return wp_json_encode( $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP );
    }

    public static function register_rest() {
        register_rest_route( self::REST_NS, '/lead', array(
            'methods' => 'POST',
            'permission_callback' => '__return_true',
            'callback' => array( __CLASS__, 'create_lead' ),
        ) );
    }

    private static function normalize_id( $id ) {
        $id = strtoupper( trim( (string) $id ) );
        $id = preg_replace( '/[^A-Z0-9_-]+/', '-', $id );
        return trim( $id, '-' );
    }

    private static function config_by_id( $id ) {
        $id = self::normalize_id( $id );
        if ( $id === '' ) return null;
        $file = dirname( __DIR__ ) . '/configs/' . strtolower( $id ) . '.json';
        if ( ! is_file( $file ) ) return null;
        $config = json_decode( (string) file_get_contents( $file ), true );
        return is_array( $config ) ? $config : null;
    }

    private static function clean_extra( $extra ) {
        $out = array();
        if ( ! is_array( $extra ) ) return $out;
        foreach ( $extra as $key => $value ) {
            $key = sanitize_key( $key );
            if ( $key === '' || is_array( $value ) || is_object( $value ) ) continue;
            $out[ $key ] = substr( sanitize_text_field( (string) $value ), 0, 500 );
        }
        return $out;
    }

    public static function create_lead( WP_REST_Request $request ) {
        global $wpdb;
        self::maybe_upgrade();
        $params = $request->get_json_params();
        if ( ! is_array( $params ) ) $params = $request->get_params();
        if ( trim( (string) ( $params['website'] ?? '' ) ) !== '' ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'spam' ), 400 );
        }
        $ts = (int) ( $params['ts'] ?? 0 );
        $now_ms = (int) round( microtime( true ) * 1000 );
        if ( $ts <= 0 || ( $now_ms - $ts ) < self::MIN_FILL_MS ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'submissão muito rápida' ), 400 );
        }
        if ( ( $now_ms - $ts ) > 21600000 ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'formulário expirado' ), 400 );
        }

        $chat_id = self::normalize_id( $params['chat_id'] ?? '' );
        $name = trim( wp_strip_all_tags( (string) ( $params['name'] ?? '' ) ) );
        $phone = preg_replace( '/\D/', '', (string) ( $params['phone'] ?? '' ) );
        if ( $chat_id === '' || strlen( $name ) < 2 || strlen( $phone ) < 10 ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'Nome ou telefone inválido.' ), 400 );
        }
        $config = self::config_by_id( $chat_id );
        if ( ! $config || empty( $config['sms_enabled'] ) ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'Chat SMS não encontrado.' ), 404 );
        }

        $manager_code = strtoupper( sanitize_text_field( $config['sms_manager_code'] ?? '' ) );
        $managers = self::managers();
        $sms_url = isset( $managers[ $manager_code ] ) ? $managers[ $manager_code ]['url'] : '';
        $extra = self::clean_extra( $params['extra'] ?? array() );
        $fields = array();
        foreach ( array( 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'fbclid', 'gclid' ) as $field ) {
            $fields[ $field ] = substr( sanitize_text_field( (string) ( $params[ $field ] ?? '' ) ), 0, 255 );
        }

        $table = self::table_name();
        $inserted = $wpdb->insert( $table, array(
            'chat_id' => $chat_id,
            'route' => substr( sanitize_text_field( (string) ( $config['route'] ?? '' ) ), 0, 255 ),
            'manager_code' => $manager_code,
            'name' => substr( $name, 0, 200 ),
            'phone' => substr( $phone, 0, 32 ),
            'utm_source' => $fields['utm_source'],
            'utm_medium' => $fields['utm_medium'],
            'utm_campaign' => $fields['utm_campaign'],
            'utm_term' => $fields['utm_term'],
            'utm_content' => $fields['utm_content'],
            'fbclid' => $fields['fbclid'],
            'gclid' => $fields['gclid'],
            'extra_params' => wp_json_encode( $extra ),
            'ip' => substr( sanitize_text_field( (string) ( $_SERVER['REMOTE_ADDR'] ?? '' ) ), 0, 64 ),
            'user_agent' => substr( sanitize_text_field( (string) ( $_SERVER['HTTP_USER_AGENT'] ?? '' ) ), 0, 500 ),
            'sms_funnel_status' => 'pending',
        ) );
        $lead_id = (int) $wpdb->insert_id;
        if ( false === $inserted || ! $lead_id ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'Erro ao gravar lead.' ), 500 );
        }

        if ( ! self::is_valid_sms_url( $sms_url ) ) {
            $wpdb->update( $table, array( 'sms_funnel_status' => 'skipped:no-url' ), array( 'id' => $lead_id ) );
            return new WP_REST_Response( array( 'ok' => false, 'lead_id' => $lead_id, 'error' => 'SMS Funnel não configurado para este chat.' ), 502 );
        }

        $response = wp_safe_remote_post( $sms_url, array(
            'timeout' => 10,
            'redirection' => 0,
            'headers' => array( 'Content-Type' => 'application/json', 'Accept' => 'application/json' ),
            'body' => wp_json_encode( array( 'name' => $name, 'phone' => $phone ) ),
        ) );
        $sms_status = 'error';
        $sms_body = '';
        if ( is_wp_error( $response ) ) {
            $sms_body = substr( $response->get_error_message(), 0, 500 );
        } else {
            $code = (int) wp_remote_retrieve_response_code( $response );
            $sms_body = substr( (string) wp_remote_retrieve_body( $response ), 0, 500 );
            $sms_status = ( $code >= 200 && $code < 300 ) ? 'ok:' . $manager_code : 'fail:' . $code;
        }
        $wpdb->update( $table, array( 'sms_funnel_status' => $sms_status, 'sms_funnel_response' => $sms_body ), array( 'id' => $lead_id ) );
        if ( 0 !== strpos( $sms_status, 'ok:' ) ) {
            return new WP_REST_Response( array( 'ok' => false, 'lead_id' => $lead_id, 'error' => 'Não foi possível enviar para o SMS Funnel. Tente novamente.' ), 502 );
        }
        return rest_ensure_response( array( 'ok' => true, 'lead_id' => $lead_id, 'sms_funnel' => $sms_status ) );
    }

    private static function report_filters() {
        return array(
            'chat_id' => self::normalize_id( $_GET['chat_id'] ?? '' ),
            'from' => sanitize_text_field( $_GET['from'] ?? '' ),
            'to' => sanitize_text_field( $_GET['to'] ?? '' ),
            'manager' => strtoupper( sanitize_text_field( $_GET['manager'] ?? '' ) ),
            'q' => sanitize_text_field( $_GET['q'] ?? '' ),
            'per_page' => max( 5, min( 250, (int) ( $_GET['per_page'] ?? 10 ) ) ),
            'paged' => max( 1, (int) ( $_GET['paged'] ?? 1 ) ),
        );
    }

    private static function report_where( $filters, &$params ) {
        global $wpdb;
        $where = ' WHERE 1=1 ';
        if ( $filters['chat_id'] ) { $where .= ' AND chat_id=%s '; $params[] = $filters['chat_id']; }
        if ( $filters['from'] ) {
            $from_utc = self::local_date_bound_to_utc( $filters['from'] );
            if ( $from_utc ) { $where .= ' AND created_at >= %s '; $params[] = $from_utc; }
        }
        if ( $filters['to'] ) {
            $to_utc = self::local_date_bound_to_utc( $filters['to'], true );
            if ( $to_utc ) { $where .= ' AND created_at < %s '; $params[] = $to_utc; }
        }
        if ( $filters['manager'] ) { $where .= ' AND manager_code=%s '; $params[] = $filters['manager']; }
        if ( $filters['q'] ) {
            $like = '%' . $wpdb->esc_like( $filters['q'] ) . '%';
            $where .= ' AND (name LIKE %s OR phone LIKE %s OR utm_campaign LIKE %s OR utm_medium LIKE %s) ';
            array_push( $params, $like, $like, $like, $like );
        }
        return $where;
    }

    private static function prepare_sql( $sql, $params ) {
        global $wpdb;
        return $params ? $wpdb->prepare( $sql, $params ) : $sql;
    }

    private static function filter_form( $filters, $page ) {
        echo '<form class="mgs-cf-lead-filters" method="get"><input type="hidden" name="page" value="' . esc_attr( $page ) . '">';
        echo '<label>Chat<input name="chat_id" value="' . esc_attr( $filters['chat_id'] ) . '" placeholder="CAR-BR-01-SMS"></label>';
        echo '<label>Data inicial<input type="date" name="from" value="' . esc_attr( $filters['from'] ) . '"></label>';
        echo '<label>Data final<input type="date" name="to" value="' . esc_attr( $filters['to'] ) . '"></label>';
        echo '<label>Gestor<select name="manager"><option value="">Todos</option>';
        foreach ( self::managers() as $code => $manager ) echo '<option value="' . esc_attr( $code ) . '" ' . selected( $filters['manager'], $code, false ) . '>' . esc_html( $manager['label'] ) . '</option>';
        echo '</select></label><label>Buscar<input name="q" value="' . esc_attr( $filters['q'] ) . '" placeholder="Nome, telefone, campanha"></label>';
        echo '<label>Por página<select name="per_page">'; foreach ( array( 5, 10, 25, 50, 100, 250 ) as $n ) echo '<option value="' . (int) $n . '" ' . selected( $filters['per_page'], $n, false ) . '>' . (int) $n . '</option>'; echo '</select></label>';
        echo '<div><button class="button button-primary">Filtrar</button></div></form>';
    }

    private static function report_css() {
        echo '<style>.mgs-cf-leads,.mgs-cf-sms-report{max-width:1480px}.mgs-cf-lead-filters{display:grid;grid-template-columns:repeat(7,minmax(120px,1fr));gap:12px;align-items:end;background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:16px;margin:16px 0}.mgs-cf-lead-filters label{font-weight:600}.mgs-cf-lead-filters input,.mgs-cf-lead-filters select{display:block;width:100%;min-height:40px;margin-top:5px}.mgs-cf-lead-card{background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:18px;margin:16px 0;overflow:auto}.mgs-cf-report-cards{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:14px;margin:16px 0}.mgs-cf-report-cards>div{background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:18px}.mgs-cf-report-cards strong{display:block;font-size:28px}.mgs-cf-report-cards span{color:#667085}.mgs-cf-lead-table{min-width:1050px}.mgs-cf-lead-table th,.mgs-cf-lead-table td{vertical-align:top;white-space:nowrap}.mgs-cf-pager{display:flex;gap:10px;align-items:center;justify-content:flex-end;margin:12px 0}@media(max-width:1180px){.mgs-cf-lead-filters{grid-template-columns:repeat(3,1fr)}}@media(max-width:782px){.mgs-cf-lead-filters,.mgs-cf-report-cards{grid-template-columns:1fr}}</style>';
    }

    private static function fetch_report_rows( $filters ) {
        global $wpdb;
        $params = array();
        $where = self::report_where( $filters, $params );
        $table = self::table_name();
        $total = (int) $wpdb->get_var( self::prepare_sql( "SELECT COUNT(*) FROM {$table} {$where}", $params ) );
        $pages = max( 1, (int) ceil( $total / $filters['per_page'] ) );
        $page = min( $filters['paged'], $pages );
        $offset = ( $page - 1 ) * $filters['per_page'];
        $sql = self::prepare_sql( "SELECT id,created_at,chat_id,manager_code,name,phone,utm_source,utm_medium,utm_campaign,sms_funnel_status FROM {$table} {$where} ORDER BY created_at DESC", $params );
        $rows = $wpdb->get_results( $sql . $wpdb->prepare( ' LIMIT %d OFFSET %d', $filters['per_page'], $offset ), ARRAY_A );
        return array( $rows, $total, $page, $pages, $where, $params );
    }

    private static function render_rows_table( $rows ) {
        echo '<table class="widefat striped mgs-cf-lead-table"><thead><tr><th>ID</th><th>Data</th><th>Chat</th><th>Gestor</th><th>Nome</th><th>Telefone</th><th>utm_source</th><th>utm_medium</th><th>Campanha</th><th>SMS</th></tr></thead><tbody>';
        foreach ( (array) $rows as $row ) {
            echo '<tr><td>' . (int) $row['id'] . '</td><td>' . esc_html( self::format_created_at( $row['created_at'] ) ) . '</td><td>' . esc_html( $row['chat_id'] ) . '</td><td>' . esc_html( $row['manager_code'] ) . '</td><td>' . esc_html( $row['name'] ) . '</td><td>' . esc_html( $row['phone'] ) . '</td><td>' . esc_html( $row['utm_source'] ) . '</td><td>' . esc_html( $row['utm_medium'] ) . '</td><td>' . esc_html( $row['utm_campaign'] ) . '</td><td>' . esc_html( $row['sms_funnel_status'] ) . '</td></tr>';
        }
        if ( empty( $rows ) ) echo '<tr><td colspan="10">Nenhum lead encontrado.</td></tr>';
        echo '</tbody></table>';
    }

    public static function render_leads_page() {
        if ( ! current_user_can( 'manage_options' ) ) wp_die( 'forbidden' );
        self::maybe_upgrade();
        $filters = self::report_filters();
        list( $rows, $total, $page, $pages ) = self::fetch_report_rows( $filters );
        $export_args = array_filter( array( 'action' => 'mgs_cf_export_leads', 'chat_id' => $filters['chat_id'], 'from' => $filters['from'], 'to' => $filters['to'], 'manager' => $filters['manager'], 'q' => $filters['q'] ) );
        $export_url = wp_nonce_url( add_query_arg( $export_args, admin_url( 'admin-post.php' ) ), 'mgs_cf_export_leads' );
        echo '<div class="wrap mgs-cf-leads"><h1>Leads SMS <a class="page-title-action" href="' . esc_url( $export_url ) . '">Exportar CSV</a></h1>';
        self::report_css(); self::filter_form( $filters, 'mgs-chat-funnels-leads' );
        echo '<div class="mgs-cf-lead-card"><h2>Leads (' . (int) $total . ')</h2>'; self::render_rows_table( $rows );
        self::pager( $filters, $page, $pages, 'mgs-chat-funnels-leads' ); echo '</div></div>';
    }

    public static function render_report_page() {
        if ( ! current_user_can( 'manage_options' ) ) wp_die( 'forbidden' );
        global $wpdb;
        self::maybe_upgrade();
        $filters = self::report_filters();
        list( $rows, $total, $page, $pages, $where, $params ) = self::fetch_report_rows( $filters );
        $table = self::table_name();
        $unique = (int) $wpdb->get_var( self::prepare_sql( "SELECT COUNT(DISTINCT phone) FROM {$table} {$where}", $params ) );
        $ok = (int) $wpdb->get_var( self::prepare_sql( "SELECT COUNT(*) FROM {$table} {$where} AND sms_funnel_status LIKE 'ok:%'", $params ) );
        $local_date_sql = self::local_date_sql();
        $days = (int) $wpdb->get_var( self::prepare_sql( "SELECT COUNT(DISTINCT {$local_date_sql}) FROM {$table} {$where}", $params ) );
        $avg = $days > 0 ? round( $total / $days, 1 ) : 0;
        echo '<div class="wrap mgs-cf-sms-report"><h1>Relatório SMS</h1><p>Captação dos chats <code>/chat-sms/</code>, entrega ao SMS Funnel e atribuição de campanha.</p>';
        self::report_css(); self::filter_form( $filters, 'mgs-chat-funnels-reports' );
        echo '<div class="mgs-cf-report-cards"><div><strong>' . (int) $total . '</strong><span>Total de leads</span></div><div><strong>' . (int) $unique . '</strong><span>Telefones únicos</span></div><div><strong>' . esc_html( $avg ) . '</strong><span>Média por dia ativo</span></div><div><strong>' . (int) $ok . '</strong><span>Envios SMS OK</span></div></div>';
        echo '<div class="mgs-cf-lead-card"><h2>Leads recentes</h2>'; self::render_rows_table( $rows ); self::pager( $filters, $page, $pages, 'mgs-chat-funnels-reports' ); echo '</div></div>';
    }

    private static function pager( $filters, $page, $pages, $admin_page ) {
        $base = array_filter( array( 'page' => $admin_page, 'chat_id' => $filters['chat_id'], 'from' => $filters['from'], 'to' => $filters['to'], 'manager' => $filters['manager'], 'q' => $filters['q'], 'per_page' => $filters['per_page'] ) );
        echo '<div class="mgs-cf-pager">';
        if ( $page > 1 ) echo '<a class="button" href="' . esc_url( add_query_arg( array_merge( $base, array( 'paged' => $page - 1 ) ), admin_url( 'admin.php' ) ) ) . '">Anterior</a>';
        echo '<span>Página ' . (int) $page . ' de ' . (int) $pages . '</span>';
        if ( $page < $pages ) echo '<a class="button" href="' . esc_url( add_query_arg( array_merge( $base, array( 'paged' => $page + 1 ) ), admin_url( 'admin.php' ) ) ) . '">Próxima</a>';
        echo '</div>';
    }

    public static function export_leads() {
        if ( ! current_user_can( 'manage_options' ) ) wp_die( 'forbidden' );
        check_admin_referer( 'mgs_cf_export_leads' );
        global $wpdb;
        $filters = self::report_filters();
        $params = array();
        $where = self::report_where( $filters, $params );
        $table = self::table_name();
        $rows = $wpdb->get_results( self::prepare_sql( "SELECT id,created_at,chat_id,route,manager_code,name,phone,utm_source,utm_medium,utm_campaign,utm_term,utm_content,fbclid,gclid,sms_funnel_status FROM {$table} {$where} ORDER BY created_at DESC", $params ), ARRAY_A );
        nocache_headers();
        header( 'Content-Type: text/csv; charset=utf-8' );
        header( 'Content-Disposition: attachment; filename=mgs-chat-leads-' . wp_date( 'Ymd-His', null, self::business_timezone() ) . '.csv' );
        $out = fopen( 'php://output', 'w' );
        fputcsv( $out, array( 'id','created_at','chat_id','route','manager_code','name','phone','utm_source','utm_medium','utm_campaign','utm_term','utm_content','fbclid','gclid','sms_funnel_status' ) );
        foreach ( (array) $rows as $row ) {
            $row['created_at'] = self::format_created_at( $row['created_at'], 'Y-m-d H:i:s' );
            fputcsv( $out, $row );
        }
        fclose( $out );
        exit;
    }
}
