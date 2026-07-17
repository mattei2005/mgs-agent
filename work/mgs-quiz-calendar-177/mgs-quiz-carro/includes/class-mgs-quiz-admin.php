<?php
/**
 * Admin do MGS Quiz:
 * - lista de quizzes
 * - edição de quiz
 * - relatório visual por quiz
 * - leads + export CSV
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

class MGS_Quiz_Admin {

    const BUSINESS_TIMEZONE = 'America/Sao_Paulo';

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

    private static function sms_default_presets() {
        return array(
            'G001' => array( 'gestor_code' => 'G001', 'label' => 'G001 – Icaro',   'url' => 'https://v2.smsfunnel.com.br/integrations/lists/019ef608-21bf-70db-9ae2-26980d501d61/add-lead' ),
            'G002' => array( 'gestor_code' => 'G002', 'label' => 'G002 – Geizian', 'url' => 'https://v2.smsfunnel.com.br/integrations/lists/019e4820-49be-734a-920a-9a15633f1cfd/add-lead' ),
            'G003' => array( 'gestor_code' => 'G003', 'label' => 'G003 – Isliago', 'url' => 'https://v2.smsfunnel.com.br/integrations/lists/019ef5da-5176-723c-8de4-261e4777dba3/add-lead' ),
            'G004' => array( 'gestor_code' => 'G004', 'label' => 'G004 – Joe',     'url' => 'https://v2.smsfunnel.com.br/integrations/lists/019ef608-5249-705a-9bda-df396a2f15d7/add-lead' ),
            'G005' => array( 'gestor_code' => 'G005', 'label' => 'G005 – Kelly',   'url' => 'https://v2.smsfunnel.com.br/integrations/lists/019ef21e-3714-72e8-928c-6c731604631f/add-lead' ),
            'G006' => array( 'gestor_code' => 'G006', 'label' => 'G006 – Nicolas', 'url' => 'https://v2.smsfunnel.com.br/integrations/lists/019ef608-7084-7075-b0d0-b0764085bbfc/add-lead' ),
        );
    }

    private static function is_valid_sms_url( $url ) {
        $parts = wp_parse_url( $url );
        if ( ! is_array( $parts ) ) return false;
        if ( 'https' !== strtolower( $parts['scheme'] ?? '' ) ) return false;
        if ( 'v2.smsfunnel.com.br' !== strtolower( $parts['host'] ?? '' ) ) return false;
        return (bool) preg_match( '#^/integrations/lists/[a-f0-9-]+/add-lead/?$#i', $parts['path'] ?? '' );
    }

    private static function rollback_sms_transaction( $message ) {
        global $wpdb;
        $wpdb->query( 'ROLLBACK' );
        wp_cache_delete( 'mgs_quiz_sms_presets', 'options' );
        wp_cache_delete( 'alloptions', 'options' );
        error_log( 'MGS Quiz SMS settings failed: ' . $message . ( $wpdb->last_error ? ' | ' . $wpdb->last_error : '' ) );
        wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz-sms&sms_error=db' ) );
        exit;
    }

    private static function sms_presets() {
        $defaults = self::sms_default_presets();
        $saved = get_option( 'mgs_quiz_sms_presets', array() );
        if ( ! is_array( $saved ) ) return $defaults;

        foreach ( $defaults as $code => $preset ) {
            if ( empty( $saved[ $code ] ) || ! is_array( $saved[ $code ] ) ) continue;
            $label = sanitize_text_field( $saved[ $code ]['label'] ?? '' );
            $url = esc_url_raw( $saved[ $code ]['url'] ?? '' );
            if ( $label && self::is_valid_sms_url( $url ) ) {
                $defaults[ $code ] = array( 'gestor_code' => $code, 'label' => $label, 'url' => $url );
            }
        }
        return $defaults;
    }

    public static function register_menu() {
        add_menu_page( 'MGS Quiz', 'MGS Quiz', 'manage_options', 'mgs-quiz',
            array( __CLASS__, 'render_list' ), 'dashicons-clipboard', 30 );
        add_submenu_page( 'mgs-quiz', 'Quizzes',   'Quizzes',   'manage_options', 'mgs-quiz',        array( __CLASS__, 'render_list' ) );
        add_submenu_page( 'mgs-quiz', 'Leads',     'Leads',     'manage_options', 'mgs-quiz-leads',  array( __CLASS__, 'render_leads' ) );
        add_submenu_page( 'mgs-quiz', 'Relatório', 'Relatório', 'manage_options', 'mgs-quiz-report', array( __CLASS__, 'render_report' ) );
        add_submenu_page( 'mgs-quiz', 'SMS Funnel','SMS',       'manage_options', 'mgs-quiz-sms',    array( __CLASS__, 'render_sms_settings' ) );
        add_submenu_page( 'mgs-quiz', 'Novo Quiz', 'Novo Quiz', 'manage_options', 'mgs-quiz-new',    array( __CLASS__, 'render_edit' ) );
    }

    private static function handle_sms_presets_save( $t ) {
        global $wpdb;
        $defaults = self::sms_default_presets();
        $labels = isset( $_POST['sms_labels'] ) && is_array( $_POST['sms_labels'] ) ? wp_unslash( $_POST['sms_labels'] ) : array();
        $urls = isset( $_POST['sms_urls'] ) && is_array( $_POST['sms_urls'] ) ? wp_unslash( $_POST['sms_urls'] ) : array();
        $presets = array();

        foreach ( $defaults as $code => $default ) {
            $label = sanitize_text_field( $labels[ $code ] ?? '' );
            $url = esc_url_raw( $urls[ $code ] ?? '' );
            if ( ! $label || ! self::is_valid_sms_url( $url ) ) {
                wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz-sms&sms_error=invalid&code=' . urlencode( $code ) ) );
                exit;
            }
            $presets[ $code ] = array( 'gestor_code' => $code, 'label' => $label, 'url' => $url );
        }

        $updated_quizzes = 0;
        $engines = $wpdb->get_results( $wpdb->prepare(
            "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (%s, %s)",
            $t,
            $wpdb->options
        ), ARRAY_A );
        if ( 2 !== count( (array) $engines ) || array_filter( $engines, function( $row ) { return 'InnoDB' !== ( $row['ENGINE'] ?? '' ); } ) ) {
            error_log( 'MGS Quiz SMS settings blocked: transactional tables required.' );
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz-sms&sms_error=engine' ) );
            exit;
        }

        if ( false === $wpdb->query( 'START TRANSACTION' ) ) {
            self::rollback_sms_transaction( 'could not start transaction' );
        }
        $rows = $wpdb->get_results( "SELECT id, sms_funnel_urls FROM {$t} FOR UPDATE", ARRAY_A );
        if ( null === $rows || $wpdb->last_error ) {
            self::rollback_sms_transaction( 'could not lock quiz rows' );
        }
        $old_presets = get_option( 'mgs_quiz_sms_presets', array() );
        if ( $old_presets !== $presets && ! update_option( 'mgs_quiz_sms_presets', $presets, false ) ) {
            self::rollback_sms_transaction( 'could not update central option' );
        }

        foreach ( (array) $rows as $row ) {
            $sms_rows = json_decode( (string) $row['sms_funnel_urls'], true );
            if ( ! is_array( $sms_rows ) ) continue;
            $changed = false;
            foreach ( $sms_rows as &$sms_row ) {
                if ( ! is_array( $sms_row ) ) {
                    self::rollback_sms_transaction( 'invalid sms row in quiz ' . $row['id'] );
                }
                $code = strtoupper( sanitize_text_field( $sms_row['gestor_code'] ?? '' ) );
                if ( ! isset( $presets[ $code ] ) ) continue;
                if ( ( $sms_row['label'] ?? '' ) !== $presets[ $code ]['label'] || ( $sms_row['url'] ?? '' ) !== $presets[ $code ]['url'] ) {
                    $sms_row['label'] = $presets[ $code ]['label'];
                    $sms_row['url'] = $presets[ $code ]['url'];
                    $changed = true;
                }
            }
            unset( $sms_row );
            if ( $changed ) {
                $result = $wpdb->update( $t, array( 'sms_funnel_urls' => wp_json_encode( $sms_rows ), 'updated_at' => current_time( 'mysql' ) ), array( 'id' => $row['id'] ) );
                if ( false === $result ) {
                    self::rollback_sms_transaction( 'could not propagate quiz ' . $row['id'] );
                }
                $updated_quizzes++;
            }
        }
        if ( false === $wpdb->query( 'COMMIT' ) ) {
            self::rollback_sms_transaction( 'commit failed' );
        }
        wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz-sms&saved=1&updated=' . $updated_quizzes ) );
        exit;
    }

    public static function handle_post() {
        if ( empty( $_POST['mgs_quiz_action'] ) ) return;
        if ( ! current_user_can( 'manage_options' ) ) wp_die( 'forbidden' );
        check_admin_referer( 'mgs_quiz_save' );

        global $wpdb;
        $t = $wpdb->prefix . 'mgs_quiz_config';

        $action = sanitize_text_field( $_POST['mgs_quiz_action'] );
        if ( 'save_sms_presets' === $action ) {
            self::handle_sms_presets_save( $t );
            return;
        }
        if ( 'duplicate' === $action ) {
            self::handle_duplicate( $t );
            return;
        }

        $id = sanitize_text_field( $_POST['id'] ?? '' );
        if ( ! $id ) $id = wp_generate_uuid4();

        $opts_raw = (string) ( $_POST['options'] ?? '' );
        $options  = array_values( array_filter( array_map( 'trim', explode( "\n", $opts_raw ) ) ) );

        $sms_urls = array();
        $sms_preset_code = strtoupper( sanitize_text_field( $_POST['sms_preset_code'] ?? '' ) );
        $sms_presets = self::sms_presets();
        if ( ! $sms_preset_code || ! isset( $sms_presets[ $sms_preset_code ] ) ) {
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz-new&id=' . urlencode( $id ) . '&sms_error=invalid' ) );
            exit;
        }
        if ( $sms_preset_code && isset( $sms_presets[ $sms_preset_code ] ) ) {
            $preset = $sms_presets[ $sms_preset_code ];
            $sms_urls[] = array(
                'url'         => $preset['url'],
                'label'       => $preset['label'],
                'gestor_code' => $preset['gestor_code'],
                'active'      => 1,
                'default'     => 1,
            );
        } elseif ( ! empty( $_POST['sms_gestor_codes'] ) && is_array( $_POST['sms_gestor_codes'] ) ) {
            $codes  = array_values( wp_unslash( $_POST['sms_gestor_codes'] ) );
            $labels = isset( $_POST['sms_labels'] ) && is_array( $_POST['sms_labels'] ) ? array_values( wp_unslash( $_POST['sms_labels'] ) ) : array();
            $urls   = isset( $_POST['sms_urls'] ) && is_array( $_POST['sms_urls'] ) ? array_values( wp_unslash( $_POST['sms_urls'] ) ) : array();
            $active = isset( $_POST['sms_active'] ) && is_array( $_POST['sms_active'] ) ? array_map( 'sanitize_text_field', wp_unslash( $_POST['sms_active'] ) ) : array();
            $default_idx = isset( $_POST['sms_default_idx'] ) ? (string) sanitize_text_field( wp_unslash( $_POST['sms_default_idx'] ) ) : '';
            foreach ( $codes as $idx => $code ) {
                $url = esc_url_raw( $urls[ $idx ] ?? '' );
                if ( ! $url ) continue;
                $clean_code = strtoupper( sanitize_text_field( $code ) );
                $sms_urls[] = array(
                    'url'         => $url,
                    'label'       => sanitize_text_field( $labels[ $idx ] ?? $clean_code ),
                    'gestor_code' => $clean_code,
                    'active'      => empty( $_POST['sms_active'] ) ? 1 : ( in_array( (string) $idx, $active, true ) ? 1 : 0 ),
                    'default'     => ( (string) $idx === $default_idx ) ? 1 : 0,
                );
            }
        } elseif ( ! empty( $_POST['sms_funnel_urls_json'] ) ) {
            $d = json_decode( wp_unslash( $_POST['sms_funnel_urls_json'] ), true );
            if ( is_array( $d ) ) $sms_urls = $d;
        }
        $redirect_variants = array();
        $redirect_primary_url = esc_url_raw( $_POST['redirect_url'] ?? '' );
        $redirect_primary_weight = (int) ( $_POST['redirect_url_weight'] ?? 100 );
        if ( ! empty( $_POST['redirect_urls'] ) && is_array( $_POST['redirect_urls'] ) ) {
            $urls    = array_values( array_map( 'esc_url_raw', wp_unslash( $_POST['redirect_urls'] ) ) );
            $weights = isset( $_POST['redirect_weights'] ) && is_array( $_POST['redirect_weights'] ) ? array_values( wp_unslash( $_POST['redirect_weights'] ) ) : array();
            $rows    = array();
            foreach ( $urls as $idx => $url ) {
                if ( ! $url ) continue;
                $rows[] = array( 'url' => $url, 'weight' => max( 0, (int) ( $weights[ $idx ] ?? 0 ) ) );
            }
            if ( ! empty( $rows ) ) {
                $redirect_primary_url = $rows[0]['url'];
                $redirect_primary_weight = $rows[0]['weight'];
                $redirect_variants = array_slice( $rows, 1 );
            }
        } elseif ( ! empty( $_POST['redirect_variants_json'] ) ) {
            $d = json_decode( wp_unslash( $_POST['redirect_variants_json'] ), true );
            if ( is_array( $d ) ) $redirect_variants = $d;
        }

        $data = array(
            'id'                  => $id,
            'slug'                => sanitize_title( $_POST['slug'] ?? '' ),
            'name'                => sanitize_text_field( $_POST['name'] ?? '' ),
            'layout_template'     => sanitize_key( $_POST['layout_template'] ?? '' ),
            'title'               => wp_kses_post( $_POST['title'] ?? '' ),
            'subtitle'            => wp_kses_post( $_POST['subtitle'] ?? '' ),
            'question'            => wp_kses_post( $_POST['question'] ?? '' ),
            'options'             => wp_json_encode( $options ),
            'form_title'          => sanitize_text_field( $_POST['form_title'] ?? '' ),
            'form_name_label'     => sanitize_text_field( $_POST['form_name_label'] ?? '' ),
            'form_phone_label'    => sanitize_text_field( $_POST['form_phone_label'] ?? '' ),
            'form_phone_mask'     => sanitize_text_field( $_POST['form_phone_mask'] ?? '' ),
            'form_submit_label'   => sanitize_text_field( $_POST['form_submit_label'] ?? '' ),
            'success_title'       => sanitize_text_field( $_POST['success_title'] ?? '' ),
            'success_message'     => wp_kses_post( $_POST['success_message'] ?? '' ),
            'primary_color'       => sanitize_hex_color( $_POST['primary_color'] ?? '#1e8323' ),
            'redirect_url'        => $redirect_primary_url,
            'redirect_delay_ms'   => (int) ( $_POST['redirect_delay_ms'] ?? 1800 ),
            'redirect_variants'   => wp_json_encode( $redirect_variants ),
            'redirect_url_weight' => $redirect_primary_weight,
            'meta_pixel_id'       => sanitize_text_field( $_POST['meta_pixel_id'] ?? '' ),
            'gtm_id'              => sanitize_text_field( $_POST['gtm_id'] ?? '' ),
            'logo_url'            => esc_url_raw( $_POST['logo_url'] ?? '' ),
            'car_image_url'       => esc_url_raw( $_POST['car_image_url'] ?? '' ),
            'flag_image_url'      => esc_url_raw( $_POST['flag_image_url'] ?? '' ),
            'footer_html'         => wp_kses_post( $_POST['footer_html'] ?? '' ),
            'privacy_url'         => esc_url_raw( $_POST['privacy_url'] ?? '' ),
            'terms_url'           => esc_url_raw( $_POST['terms_url'] ?? '' ),
            'seo_title'           => sanitize_text_field( $_POST['seo_title'] ?? '' ),
            'seo_description'     => sanitize_textarea_field( $_POST['seo_description'] ?? '' ),
            'sms_funnel_url'      => esc_url_raw( $_POST['sms_funnel_url'] ?? '' ),
            'sms_funnel_urls'     => wp_json_encode( $sms_urls ),
            'require_sms_success' => ! empty( $_POST['require_sms_success'] ) ? 1 : 0,
            'updated_at'          => current_time( 'mysql' ),
        );

        $exists = $wpdb->get_var( $wpdb->prepare( "SELECT id FROM {$t} WHERE id = %s", $id ) );
        if ( $exists ) {
            $wpdb->update( $t, $data, array( 'id' => $id ) );
        } else {
            $wpdb->insert( $t, $data );
        }
        wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz-new&id=' . urlencode( $id ) . '&saved=1' ) );
        exit;
    }

    private static function handle_duplicate( $t ) {
        global $wpdb;

        $source_id = sanitize_text_field( $_POST['source_id'] ?? '' );
        $new_name  = sanitize_text_field( $_POST['new_name'] ?? '' );
        $new_slug  = sanitize_title( $_POST['new_slug'] ?? '' );

        if ( ! $source_id || ! $new_name || ! $new_slug ) {
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz&duplicate_error=missing' ) );
            exit;
        }

        $source = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$t} WHERE id = %s", $source_id ), ARRAY_A );
        if ( ! $source ) {
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz&duplicate_error=source' ) );
            exit;
        }

        $exists = $wpdb->get_var( $wpdb->prepare( "SELECT id FROM {$t} WHERE slug = %s", $new_slug ) );
        if ( $exists ) {
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz&duplicate_error=slug' ) );
            exit;
        }

        unset( $source['id'] );
        $source['id'] = wp_generate_uuid4();
        $source['name'] = $new_name;
        $source['slug'] = $new_slug;
        $source['sms_funnel_url'] = '';
        $source['sms_funnel_urls'] = wp_json_encode( array() );
        $source['updated_at'] = current_time( 'mysql' );

        $inserted = $wpdb->insert( $t, $source );
        if ( false === $inserted ) {
            error_log( 'MGS Quiz duplicate failed: ' . $wpdb->last_error );
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz&duplicate_error=db' ) );
            exit;
        }
        wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz-new&id=' . urlencode( $source['id'] ) . '&duplicated=1' ) );
        exit;
    }

    public static function render_list() {
        global $wpdb;
        $cfg_t   = $wpdb->prefix . 'mgs_quiz_config';
        $leads_t = $wpdb->prefix . 'mgs_quiz_leads';
        $rows = $wpdb->get_results( "SELECT c.id, c.slug, c.name, c.primary_color, c.sms_funnel_urls, c.updated_at, COUNT(l.id) AS leads_count FROM {$cfg_t} c LEFT JOIN {$leads_t} l ON l.quiz_slug = c.slug GROUP BY c.id, c.slug, c.name, c.primary_color, c.sms_funnel_urls, c.updated_at ORDER BY c.name ASC, c.slug ASC", ARRAY_A );

        echo '<div class="wrap"><h1>Quiz Carro <a href="'.esc_url( admin_url( 'admin.php?page=mgs-quiz-new' ) ).'" class="page-title-action">Criar novo quiz</a></h1>';
        if ( ! empty( $_GET['imported'] ) ) {
            $ins = (int) ( $_GET['ins'] ?? 0 ); $upd = (int) ( $_GET['upd'] ?? 0 ); $skp = (int) ( $_GET['skp'] ?? 0 );
            echo '<div class="notice notice-success"><p>Importação concluída: '.$ins.' inseridos, '.$upd.' atualizados, '.$skp.' ignorados.</p></div>';
        }
        if ( ! empty( $_GET['saved'] ) ) echo '<div class="notice notice-success"><p>Quiz salvo.</p></div>';
        if ( ! empty( $_GET['duplicate_error'] ) ) echo '<div class="notice notice-error"><p>Não foi possível duplicar. Verifique se nome/slug foram preenchidos e se o slug ainda não existe.</p></div>';

        echo '<details class="mgsq-import"><summary>Importação técnica de configs CSV</summary>';
        echo '<p>Uso interno para migração/restauração de <code>quiz_config.csv</code>. Para criar uma nova quiz, use <strong>Duplicar</strong>.</p>';
        echo '<form method="post" enctype="multipart/form-data" action="'.esc_url( admin_url( 'admin-post.php' ) ).'">';
        wp_nonce_field( 'mgs_quiz_import_config' );
        echo '<input type="hidden" name="action" value="mgs_quiz_import_config">';
        echo '<input type="file" name="csv" accept=".csv,text/csv" required> <button class="button">Importar configs</button></form></details>';

        echo '<style>.mgsq-import{background:#fff;border:1px solid #dcdcde;border-radius:12px;padding:12px 16px;margin:16px 0;max-width:780px}.mgsq-import summary{font-weight:700;cursor:pointer}.mgsq-grid{display:grid;gap:14px;margin-top:18px}.mgsq-card{background:#fff;border:1px solid #dcdcde;border-radius:12px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.04);display:flex;justify-content:space-between;gap:18px}.mgsq-card h2{margin:0 0 6px;font-size:18px}.mgsq-pill{display:inline-block;background:#e7f7ed;color:#16723a;border-radius:999px;padding:3px 9px;font-size:12px;margin-left:8px}.mgsq-url{color:#15803d}.mgsq-sms{color:#555;font-size:12px;margin-top:8px;max-width:780px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.mgsq-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end}.mgsq-modal{display:none;position:fixed;inset:0;background:rgba(15,23,42,.38);z-index:99999;align-items:center;justify-content:center}.mgsq-modal.is-open{display:flex}.mgsq-modal-card{background:#fff;border-radius:18px;box-shadow:0 24px 80px rgba(15,23,42,.25);padding:24px;width:min(520px,92vw)}.mgsq-modal-card h2{font-size:24px;margin-top:0}.mgsq-modal-card label{display:block;font-weight:700;margin-top:14px}.mgsq-modal-card input{width:100%;font-size:16px;padding:12px;border:1px solid #d0d5dd;border-radius:10px;margin-top:6px}.mgsq-modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}.mgsq-danger{color:#b42318}</style>';
        echo '<div class="mgsq-grid">';
        if ( empty( $rows ) ) {
            echo '<div class="mgsq-card"><em>Nenhum quiz cadastrado.</em></div>';
        }
        foreach ( (array) $rows as $r ) {
            $edit   = admin_url( 'admin.php?page=mgs-quiz-new&id=' . urlencode( $r['id'] ) );
            $report = admin_url( 'admin.php?page=mgs-quiz-report&slug=' . urlencode( $r['slug'] ) );
            $public = home_url( '/' . $r['slug'] . '/' );
            $sms_label = '';
            $sms = json_decode( $r['sms_funnel_urls'], true );
            if ( is_array( $sms ) ) {
                $selected_sms = null;
                foreach ( $sms as $sms_row ) {
                    $is_active = ! isset( $sms_row['active'] ) || (int) $sms_row['active'];
                    if ( $is_active && ! empty( $sms_row['default'] ) && ! empty( $sms_row['url'] ) ) {
                        $selected_sms = $sms_row;
                        break;
                    }
                }
                if ( ! $selected_sms ) {
                    foreach ( $sms as $sms_row ) {
                        $is_active = ! isset( $sms_row['active'] ) || (int) $sms_row['active'];
                        if ( $is_active && ! empty( $sms_row['url'] ) ) {
                            $selected_sms = $sms_row;
                            break;
                        }
                    }
                }
                if ( $selected_sms ) {
                    $sms_label = ( $selected_sms['gestor_code'] ?? '' ) . ' - ' . $selected_sms['url'];
                }
            }
            echo '<div class="mgsq-card"><div>';
            echo '<h2>'.esc_html( $r['name'] ?: $r['slug'] ).'<span class="mgsq-pill">'.(int)$r['leads_count'].' leads</span></h2>';
            echo '<div><a class="mgsq-url" target="_blank" href="'.esc_url( $public ).'">'.esc_html( $public ).'</a></div>';
            if ( $sms_label ) echo '<div class="mgsq-sms">🔗 '.esc_html( $sms_label ).'</div>';
            echo '</div><div class="mgsq-actions">';
            echo '<a class="button button-primary" href="'.esc_url( $report ).'">Relatório</a>';
            echo '<a class="button" href="'.esc_url( $edit ).'">Editar</a>';
            echo '<button type="button" class="button mgsq-duplicate" data-id="'.esc_attr( $r['id'] ).'" data-name="'.esc_attr( $r['name'] ?: $r['slug'] ).'" data-slug="'.esc_attr( $r['slug'] ).'">Duplicar</button>';
            echo '<a class="button" target="_blank" href="'.esc_url( $public ).'">Abrir</a>';
            echo '</div></div>';
        }
        echo '</div>';
        ?>
        <div class="mgsq-modal" id="mgsqDuplicateModal" aria-hidden="true">
          <div class="mgsq-modal-card">
            <h2>Duplicar quiz</h2>
            <p>Cria uma nova quiz com a mesma configuração visual, perguntas e redirecionamento. Leads/histórico não são copiados. Preencha o novo nome e a nova slug.</p>
            <form method="post">
              <?php wp_nonce_field( 'mgs_quiz_save' ); ?>
              <input type="hidden" name="mgs_quiz_action" value="duplicate">
              <input type="hidden" name="source_id" id="mgsqDuplicateSource" value="">
              <label>Nome da nova quiz</label>
              <input name="new_name" id="mgsqDuplicateName" required placeholder="Creditoparaveiculo-quiz-br-car-br-g007">
              <label>Slug / pasta da URL</label>
              <input name="new_slug" id="mgsqDuplicateSlug" required placeholder="quiz-car-parcelas-g007">
              <div class="mgsq-modal-actions">
                <button type="button" class="button" id="mgsqDuplicateCancel">Cancelar</button>
                <button class="button button-primary">Criar duplicata</button>
              </div>
            </form>
          </div>
        </div>
        <script>
        (function(){
          var modal=document.getElementById('mgsqDuplicateModal');
          var source=document.getElementById('mgsqDuplicateSource');
          var name=document.getElementById('mgsqDuplicateName');
          var slug=document.getElementById('mgsqDuplicateSlug');
          function open(btn){
            source.value=btn.getAttribute('data-id') || '';
            name.value=(btn.getAttribute('data-name') || '') + ' - cópia';
            slug.value=(btn.getAttribute('data-slug') || '') + '-copy';
            modal.classList.add('is-open');
            modal.setAttribute('aria-hidden','false');
            name.focus(); name.select();
          }
          document.querySelectorAll('.mgsq-duplicate').forEach(function(btn){ btn.addEventListener('click', function(){ open(btn); }); });
          document.getElementById('mgsqDuplicateCancel').addEventListener('click', function(){ modal.classList.remove('is-open'); modal.setAttribute('aria-hidden','true'); });
          modal.addEventListener('click', function(e){ if(e.target===modal){ modal.classList.remove('is-open'); modal.setAttribute('aria-hidden','true'); } });
        })();
        </script>
        <?php
        echo '</div>';
    }

    private static function report_filters() {
        $slug = isset( $_GET['slug'] ) ? sanitize_title( $_GET['slug'] ) : '';
        $yesterday = ( new DateTimeImmutable( 'now', self::business_timezone() ) )->modify( '-1 day' )->format( 'Y-m-d' );
        $from = isset( $_GET['from'] ) ? sanitize_text_field( $_GET['from'] ) : $yesterday;
        $to   = isset( $_GET['to'] )   ? sanitize_text_field( $_GET['to'] )   : $yesterday;
        $gestor = isset( $_GET['gestor'] ) ? sanitize_text_field( $_GET['gestor'] ) : '';
        $parcela = isset( $_GET['parcela'] ) ? sanitize_text_field( $_GET['parcela'] ) : '';
        $q = isset( $_GET['q'] ) ? sanitize_text_field( $_GET['q'] ) : '';
        $days_per_page = isset( $_GET['days_per_page'] ) ? sanitize_text_field( $_GET['days_per_page'] ) : '5';
        if ( 'all' !== $days_per_page ) { $days_per_page = max( 5, min( 90, (int) $days_per_page ) ); }
        $days_page = max( 1, (int) ( $_GET['days_page'] ?? 1 ) );
        $leads_per_page = max( 5, min( 500, (int) ( $_GET['leads_per_page'] ?? 5 ) ) );
        $leads_page = max( 1, (int) ( $_GET['leads_page'] ?? 1 ) );
        return compact( 'slug', 'from', 'to', 'gestor', 'parcela', 'q', 'days_per_page', 'days_page', 'leads_per_page', 'leads_page' );
    }

    private static function report_where( $filters, &$params ) {
        $where = ' WHERE 1=1 ';
        if ( $filters['slug'] ) { $where .= ' AND quiz_slug = %s '; $params[] = $filters['slug']; }
        if ( $filters['from'] ) {
            $from_utc = self::local_date_bound_to_utc( $filters['from'] );
            if ( $from_utc ) { $where .= ' AND created_at >= %s '; $params[] = $from_utc; }
        }
        if ( $filters['to'] ) {
            $to_utc = self::local_date_bound_to_utc( $filters['to'], true );
            if ( $to_utc ) { $where .= ' AND created_at < %s '; $params[] = $to_utc; }
        }
        if ( $filters['gestor'] ) { $where .= ' AND UPPER(utm_medium) = %s '; $params[] = strtoupper( $filters['gestor'] ); }
        if ( $filters['parcela'] ) { $where .= ' AND parcela = %s '; $params[] = $filters['parcela']; }
        if ( $filters['q'] ) {
            $like = '%' . $GLOBALS['wpdb']->esc_like( $filters['q'] ) . '%';
            $where .= ' AND (name LIKE %s OR phone LIKE %s OR utm_campaign LIKE %s) ';
            $params[] = $like; $params[] = $like; $params[] = $like;
        }
        return $where;
    }

    private static function days_chart_data( $filters ) {
        global $wpdb;
        $lead_t = $wpdb->prefix . 'mgs_quiz_leads';
        $params = array();
        $where = self::report_where( $filters, $params );
        $local_date_sql = self::local_date_sql();
        $sql = "SELECT {$local_date_sql} d, COUNT(*) c FROM {$lead_t} {$where} GROUP BY {$local_date_sql} ORDER BY d DESC";
        $rows_all = $params ? $wpdb->get_results( $wpdb->prepare( $sql, $params ), ARRAY_A ) : $wpdb->get_results( $sql, ARRAY_A );
        $total_days = count( $rows_all );
        $days_pp = $filters['days_per_page'];
        if ( 'all' === $days_pp ) {
            $rows = array_reverse( $rows_all );
            $pages = 1;
            $page = 1;
        } else {
            $days_pp = (int) $days_pp;
            $pages = max( 1, (int) ceil( $total_days / $days_pp ) );
            $page = min( max( 1, (int) $filters['days_page'] ), $pages );
            $rows = array_reverse( array_slice( $rows_all, ( $page - 1 ) * $days_pp, $days_pp ) );
        }
        return array( $rows, $page, $pages, $total_days );
    }

    private static function render_days_chart_inner( $rows, $page, $pages, $total_days ) {
        ob_start();
        $max = max( 1, ...array_map( 'intval', wp_list_pluck( $rows, 'c' ) ?: array(1) ) );
        foreach ( $rows as $r ) {
            $w = round( 100 * (int)$r['c'] / $max );
            echo '<div class="bar-row"><div class="bar-label">'.esc_html( date_i18n( 'm-d', strtotime( $r['d'] ) ) ).'</div><div class="bar-bg"><div class="bar-fill" style="width:'.$w.'%"></div></div><b>'.(int)$r['c'].'</b></div>';
        }
        echo '<div class="mgsq-chart-pager" data-page="'.(int)$page.'" data-pages="'.(int)$pages.'">';
        echo '<span class="mgsq-items">'.(int)$total_days.' dias</span>';
        echo '<button type="button" class="button mgsq-chart-nav" data-page="1" '.disabled( $page <= 1, true, false ).'>«</button>';
        echo '<button type="button" class="button mgsq-chart-nav" data-page="'.max( 1, $page - 1 ).'" '.disabled( $page <= 1, true, false ).'>‹</button>';
        echo '<input class="mgsq-chart-page-input" type="number" min="1" max="'.(int)$pages.'" value="'.(int)$page.'">';
        echo '<span>of '.(int)$pages.'</span>';
        echo '<button type="button" class="button mgsq-chart-nav" data-page="'.min( $pages, $page + 1 ).'" '.disabled( $page >= $pages, true, false ).'>›</button>';
        echo '<button type="button" class="button mgsq-chart-nav" data-page="'.(int)$pages.'" '.disabled( $page >= $pages, true, false ).'>»</button>';
        echo '</div>';
        return ob_get_clean();
    }

    public static function ajax_chart_days() {
        if ( ! current_user_can( 'manage_options' ) ) wp_send_json_error( array( 'message' => 'forbidden' ), 403 );
        check_ajax_referer( 'mgs_quiz_chart_days', 'nonce' );
        $filters = self::report_filters();
        list( $rows, $page, $pages, $total_days ) = self::days_chart_data( $filters );
        wp_send_json_success( array(
            'html' => self::render_days_chart_inner( $rows, $page, $pages, $total_days ),
            'page' => $page,
            'pages' => $pages,
            'total_days' => $total_days,
        ) );
    }

    private static function leads_table_data( $filters ) {
        global $wpdb;
        $lead_t = $wpdb->prefix . 'mgs_quiz_leads';
        $params = array();
        $where = self::report_where( $filters, $params );
        $prep = function( $sql ) use ( $wpdb, $params ) { return $params ? $wpdb->prepare( $sql, $params ) : $sql; };
        $total = (int) $wpdb->get_var( $prep( "SELECT COUNT(*) FROM {$lead_t} {$where}" ) );
        $per_page = max( 5, min( 500, (int) $filters['leads_per_page'] ) );
        $pages = max( 1, (int) ceil( $total / $per_page ) );
        $page = min( max( 1, (int) $filters['leads_page'] ), $pages );
        $offset = ( $page - 1 ) * $per_page;
        $sql = $prep( "SELECT created_at, name, phone, parcela, utm_medium, utm_campaign, sms_funnel_status FROM {$lead_t} {$where} ORDER BY created_at DESC" ) . $wpdb->prepare( " LIMIT %d OFFSET %d", $per_page, $offset );
        $rows = $wpdb->get_results( $sql, ARRAY_A );
        return array( $rows, $total, $page, $pages, $per_page );
    }

    private static function render_report_leads_inner( $leads, $total, $page, $pages ) {
        ob_start();
        echo '<div class="mgsq-table-wrap"><table class="widefat striped mgsq-table"><thead><tr><th class="col-date">Data</th><th class="col-name">Nome</th><th class="col-phone">Telefone</th><th class="col-parcela">Parcela</th><th class="col-gestor">Gestor</th><th class="col-campanha">Campanha</th><th class="col-sms">SMS</th></tr></thead><tbody>';
        foreach ( $leads as $l ) {
            echo '<tr><td class="col-date">'.esc_html( self::format_created_at( $l['created_at'] ) ).'</td><td class="col-name">'.esc_html($l['name']).'</td><td class="col-phone">'.esc_html($l['phone']).'</td><td class="col-parcela">'.esc_html($l['parcela']).'</td><td class="col-gestor">'.esc_html(strtoupper($l['utm_medium'])).'</td><td class="col-campanha">'.esc_html($l['utm_campaign']).'</td><td class="col-sms">'.esc_html($l['sms_funnel_status']).'</td></tr>';
        }
        echo '</tbody></table></div>';
        echo '<div class="mgsq-leads-pager" data-page="'.(int)$page.'" data-pages="'.(int)$pages.'">';
        echo '<span class="mgsq-items">'.(int)$total.' items</span>';
        echo '<button type="button" class="button mgsq-leads-nav" data-page="1" '.disabled( $page <= 1, true, false ).'>«</button>';
        echo '<button type="button" class="button mgsq-leads-nav" data-page="'.max( 1, $page - 1 ).'" '.disabled( $page <= 1, true, false ).'>‹</button>';
        echo '<input class="mgsq-leads-page-input" type="number" min="1" max="'.(int)$pages.'" value="'.(int)$page.'">';
        echo '<span>of '.(int)$pages.'</span>';
        echo '<button type="button" class="button mgsq-leads-nav" data-page="'.min( $pages, $page + 1 ).'" '.disabled( $page >= $pages, true, false ).'>›</button>';
        echo '<button type="button" class="button mgsq-leads-nav" data-page="'.(int)$pages.'" '.disabled( $page >= $pages, true, false ).'>»</button>';
        echo '<span class="mgsq-showing">mostrando '.(int)count($leads).' de '.(int)$total.'</span>';
        echo '</div>';
        return ob_get_clean();
    }

    public static function ajax_report_leads() {
        if ( ! current_user_can( 'manage_options' ) ) wp_send_json_error( array( 'message' => 'forbidden' ), 403 );
        check_ajax_referer( 'mgs_quiz_report_leads', 'nonce' );
        $filters = self::report_filters();
        list( $leads, $total, $page, $pages, $per_page ) = self::leads_table_data( $filters );
        wp_send_json_success( array(
            'html' => self::render_report_leads_inner( $leads, $total, $page, $pages ),
            'page' => $page,
            'pages' => $pages,
            'total' => $total,
            'per_page' => $per_page,
        ) );
    }

    public static function render_report() {
        global $wpdb;
        $filters = self::report_filters();
        $cfg_t = $wpdb->prefix . 'mgs_quiz_config';
        $lead_t = $wpdb->prefix . 'mgs_quiz_leads';
        $revenue_t = $wpdb->prefix . 'mgs_quiz_sms_revenue';
        $cfg = $filters['slug'] ? $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$cfg_t} WHERE slug = %s", $filters['slug'] ), ARRAY_A ) : null;

        $params = array();
        $where = self::report_where( $filters, $params );
        $prep = function( $sql ) use ( $wpdb, $params ) { return $params ? $wpdb->prepare( $sql, $params ) : $sql; };

        $total = (int) $wpdb->get_var( $prep( "SELECT COUNT(*) FROM {$lead_t} {$where}" ) );
        $unique = (int) $wpdb->get_var( $prep( "SELECT COUNT(DISTINCT phone) FROM {$lead_t} {$where}" ) );
        $period_days = max( 1, (int) floor( ( strtotime( $filters['to'] ) - strtotime( $filters['from'] ) ) / DAY_IN_SECONDS ) + 1 );
        $avg = $period_days ? round( $total / $period_days, 1 ) : $total;

        list( $by_day, $days_page, $days_pages, $days_total ) = self::days_chart_data( $filters );
        $by_gestor = $wpdb->get_results( $prep( "SELECT UPPER(COALESCE(NULLIF(utm_medium,''),'SEM UTM')) k, COUNT(*) c FROM {$lead_t} {$where} GROUP BY k ORDER BY c DESC" ), ARRAY_A );
        $by_parcela = $wpdb->get_results( $prep( "SELECT COALESCE(NULLIF(parcela,''),'Sem parcela') k, COUNT(*) c FROM {$lead_t} {$where} GROUP BY k ORDER BY c DESC" ), ARRAY_A );
        $by_quiz_cost = $wpdb->get_results( $prep( "SELECT COALESCE(NULLIF(quiz_slug,''),'sem-quiz') k, COUNT(*) c FROM {$lead_t} {$where} GROUP BY k ORDER BY c DESC" ), ARRAY_A );
        $quiz_names = array();
        foreach ( $wpdb->get_results( "SELECT slug, name FROM {$cfg_t}", ARRAY_A ) as $quiz_row ) {
            $quiz_names[ $quiz_row['slug'] ] = $quiz_row['name'];
        }
        $sms_unit_cost_centavos = 8;
        $sms_total_cost_centavos = $total * $sms_unit_cost_centavos;
        $revenue_args = array( 'digital-trust_creditoparaveiculo', 'creditoparaveiculo' );
        $revenue_where = ' WHERE publisher = %s AND domain = %s ';
        if ( $filters['from'] ) { $revenue_where .= ' AND revenue_date >= %s '; $revenue_args[] = $filters['from']; }
        if ( $filters['to'] ) { $revenue_where .= ' AND revenue_date <= %s '; $revenue_args[] = $filters['to']; }
        $sms_revenue = $wpdb->get_row( $wpdb->prepare(
            "SELECT COALESCE(SUM(net_revenue_cents),0) display_revenue_cents, COUNT(DISTINCT revenue_date) revenue_days, MIN(revenue_date) first_date, MAX(revenue_date) last_date, MAX(synced_at) synced_at FROM {$revenue_t} {$revenue_where}",
            $revenue_args
        ), ARRAY_A );
        $sms_revenue_has_data = ! empty( $sms_revenue['revenue_days'] );
        $sms_roi_scope_filtered = ! empty( $filters['slug'] ) || ! empty( $filters['gestor'] ) || ! empty( $filters['parcela'] ) || ! empty( $filters['q'] );
        $sms_roi_available = $sms_revenue_has_data && $sms_total_cost_centavos > 0 && ! $sms_roi_scope_filtered;
        $sms_profit_centavos = $sms_roi_available ? ( (int) $sms_revenue['display_revenue_cents'] - $sms_total_cost_centavos ) : 0;
        $sms_roi_percent = $sms_roi_available ? round( ( $sms_profit_centavos / $sms_total_cost_centavos ) * 100, 2 ) : 0;
        $sms_revenue_coverage = $sms_revenue_has_data
            ? number_format_i18n( (int) $sms_revenue['revenue_days'] ) . ' dia(s), ' . date_i18n( 'd/m/Y', strtotime( $sms_revenue['first_date'] ) ) . ' a ' . date_i18n( 'd/m/Y', strtotime( $sms_revenue['last_date'] ) )
            : 'Nenhuma receita importada neste período.';
        if ( $sms_roi_available ) {
            $sms_roi_value = number_format( $sms_roi_percent, 2, ',', '.' ) . '%';
            $sms_roi_note = 'Lucro estimado: R$ ' . number_format( $sms_profit_centavos / 100, 2, ',', '.' ) . '. Fórmula: (receita líquida − custo estimado) ÷ custo estimado.';
        } elseif ( $sms_roi_scope_filtered ) {
            $sms_roi_value = 'Não comparável';
            $sms_roi_note = 'A receita SB é total do domínio; remova filtros de quiz, gestor, parcela e busca para calcular o ROI.';
        } else {
            $sms_roi_value = 'Sem base';
            $sms_roi_note = 'É necessário ter receita SB e custo estimado maiores que zero no período.';
        }

        list( $leads, $leads_total, $leads_page, $leads_pages, $leads_pp ) = self::leads_table_data( $filters );
        $filters['leads_page'] = $leads_page;

        $gestores = $wpdb->get_col( $filters['slug'] ? $wpdb->prepare( "SELECT DISTINCT UPPER(utm_medium) FROM {$lead_t} WHERE quiz_slug=%s AND utm_medium<>'' ORDER BY 1", $filters['slug'] ) : "SELECT DISTINCT UPPER(utm_medium) FROM {$lead_t} WHERE utm_medium<>'' ORDER BY 1" );
        $parcelas = $wpdb->get_col( $filters['slug'] ? $wpdb->prepare( "SELECT DISTINCT parcela FROM {$lead_t} WHERE quiz_slug=%s AND parcela<>'' ORDER BY 1", $filters['slug'] ) : "SELECT DISTINCT parcela FROM {$lead_t} WHERE parcela<>'' ORDER BY 1" );
        $export_url = wp_nonce_url( admin_url( 'admin-post.php?action=mgs_quiz_export_leads&slug=' . urlencode( $filters['slug'] ) . '&from=' . urlencode( $filters['from'] ) . '&to=' . urlencode( $filters['to'] ) ), 'mgs_quiz_export' );
        $base_args = array_filter( array(
            'page' => 'mgs-quiz-report', 'slug' => $filters['slug'], 'from' => $filters['from'], 'to' => $filters['to'],
            'gestor' => $filters['gestor'], 'parcela' => $filters['parcela'], 'q' => $filters['q'],
            'days_per_page' => $filters['days_per_page'], 'leads_per_page' => $filters['leads_per_page'],
        ), function( $v ) { return $v !== '' && $v !== null; } );

        echo '<div class="wrap mgsq-report"><style>.mgsq-report{max-width:none;margin:10px 20px 0 2px}.mgsq-report *{box-sizing:border-box}.mgsq-report .hero{display:flex;align-items:center;gap:12px;margin:14px 0}.mgsq-report .icon{background:#e7f7ed;color:#16723a;border-radius:14px;padding:12px;font-size:24px}.mgsq-report .filters,.mgsq-report .card{background:#fff;border:1px solid #dcdcde;border-radius:16px;padding:20px;margin:18px 0;box-shadow:0 1px 8px rgba(16,24,40,.05);width:100%;max-width:none!important;min-width:0}.mgsq-report .filters{display:grid;grid-template-columns:repeat(7,minmax(120px,1fr));gap:12px;align-items:end}.mgsq-report label{font-weight:600;display:block;margin-bottom:4px}.mgsq-report input,.mgsq-report select{width:100%;max-width:none;min-height:38px}.mgsq-stats{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:16px;width:100%}.mgsq-stat{background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:16px}.mgsq-stat b{display:block;font-size:28px;margin-top:6px}.mgsq-stat small{display:block;color:#667085;line-height:1.35;margin-top:8px}.mgsq-flex{display:grid;grid-template-columns:1fr;gap:18px;align-items:start;width:100%;clear:both}.bar-row{display:flex;align-items:center;gap:8px;margin:8px 0}.bar-label{width:120px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bar-bg{height:12px;background:#edf2f7;border-radius:999px;flex:1}.bar-fill{height:12px;background:#16a34a;border-radius:999px}.mgsq-pills{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;width:100%}.mgsq-pills span{border:1px solid #dcdcde;border-radius:999px;padding:10px 14px;background:#fff;display:flex;justify-content:space-between;gap:10px;white-space:nowrap}.mgsq-toolbar{display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:10px}.mgsq-pager,.mgsq-chart-pager,.mgsq-leads-pager{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.mgsq-chart-pager,.mgsq-leads-pager{border-top:1px solid #eef2f7;margin-top:14px;padding-top:14px}.mgsq-chart-pager .button,.mgsq-leads-pager .button{min-width:36px;text-align:center}.mgsq-chart-page-input,.mgsq-leads-page-input{width:58px!important;min-height:34px!important;text-align:center}.mgsq-chart-controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;align-items:end;margin:10px 0 16px;width:100%}.mgsq-chart-loading{opacity:.45;pointer-events:none}.mgsq-chart-controls .button{width:100%;min-height:38px}.mgsq-items{font-weight:600;margin-right:8px}.mgsq-table-wrap{overflow-x:auto;width:100%;max-width:100%;padding-bottom:6px}.mgsq-table{table-layout:fixed;min-width:1500px;width:100%}.mgsq-table th,.mgsq-table td{vertical-align:top;word-break:normal;overflow-wrap:normal;white-space:normal;line-height:1.35}.mgsq-table .col-date{width:145px}.mgsq-table .col-name{width:240px}.mgsq-table .col-phone{width:135px;white-space:nowrap}.mgsq-table .col-parcela{width:210px}.mgsq-table .col-gestor{width:105px;white-space:nowrap}.mgsq-table .col-campanha{width:280px}.mgsq-table .col-sms{width:105px;white-space:nowrap}.mgsq-leads-card{width:100%}.mgsq-showing{color:#667085;margin-left:8px}@media(max-width:1280px){.mgsq-flex{grid-template-columns:1fr}.mgsq-report .filters{grid-template-columns:repeat(2,minmax(180px,1fr))}.mgsq-stats{grid-template-columns:repeat(2,minmax(180px,1fr))}.mgsq-chart-controls{grid-template-columns:repeat(2,minmax(160px,1fr))}}@media(max-width:782px){.mgsq-report{margin:10px 10px 0 0}.mgsq-report .filters,.mgsq-flex,.mgsq-stats,.mgsq-chart-controls{grid-template-columns:1fr}.mgsq-report .card{padding:14px}.mgsq-table{min-width:980px}}</style>';
        echo '<a href="'.esc_url( admin_url( 'admin.php?page=mgs-quiz' ) ).'">← Voltar</a>';
        echo '<div class="hero"><div class="icon">📊</div><div><h1>Relatório · '.esc_html( $cfg['name'] ?? ( $filters['slug'] ?: 'Todos os quizzes' ) ).'</h1><p>'.esc_html( $filters['slug'] ? '/' . $filters['slug'] . '/' : 'Todos' ).' · análise das leads capturadas</p></div></div>';
        echo '<p><a class="button button-primary" href="'.esc_url( $export_url ).'">Exportar CSV</a></p>';
        echo '<style>
        .mgsq-report .filters{position:relative;grid-template-columns:repeat(7,minmax(120px,1fr))}
        .mgsq-range-field{grid-column:span 2;position:relative}.mgsq-range-trigger{width:100%;min-height:38px;display:flex;align-items:center;justify-content:space-between;gap:12px;border:1px solid #8c8f94;border-radius:4px;background:#fff;padding:7px 10px;cursor:pointer;text-align:left}.mgsq-range-trigger:hover,.mgsq-range-trigger:focus{border-color:#2271b1;box-shadow:0 0 0 1px #2271b1;outline:0}.mgsq-range-trigger .dashicons{color:#646970}
        .mgsq-date-popover{position:absolute;z-index:1001;top:calc(100% + 8px);left:0;width:min(820px,calc(100vw - 64px));display:none;background:#fff;border:1px solid #d0d5dd;border-radius:14px;box-shadow:0 18px 48px rgba(16,24,40,.18);overflow:hidden}.mgsq-date-popover.is-open{display:grid;grid-template-columns:180px 1fr}.mgsq-date-shortcuts{padding:14px;border-right:1px solid #e4e7ec;background:#f8fafc;display:flex;flex-direction:column;gap:4px}.mgsq-date-shortcut{border:0;background:transparent;border-radius:8px;padding:9px 10px;text-align:left;cursor:pointer;color:#344054}.mgsq-date-shortcut:hover,.mgsq-date-shortcut.is-active{background:#e7f7ed;color:#16723a;font-weight:700}.mgsq-date-main{min-width:0}.mgsq-calendars{display:grid;grid-template-columns:1fr 1fr}.mgsq-calendar-panel{padding:14px 16px}.mgsq-calendar-panel+ .mgsq-calendar-panel{border-left:1px solid #e4e7ec}.mgsq-calendar-head{height:36px;display:grid;grid-template-columns:36px 1fr 36px;align-items:center;text-align:center;font-weight:700}.mgsq-calendar-head button{width:32px;height:32px;border:0;border-radius:8px;background:transparent;cursor:pointer;font-size:20px;line-height:1}.mgsq-calendar-head button:hover{background:#f0f0f1}.mgsq-mobile-next{display:none}.mgsq-weekdays,.mgsq-days{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}.mgsq-weekdays span{padding:7px 0;text-align:center;color:#667085;font-size:11px;font-weight:700;text-transform:uppercase}.mgsq-day,.mgsq-day-empty{aspect-ratio:1;min-height:32px}.mgsq-day{border:0;background:transparent;border-radius:8px;cursor:pointer;color:#1d2939}.mgsq-day:hover{background:#edf2f7}.mgsq-day.is-range{background:#e7f7ed;border-radius:0}.mgsq-day.is-start,.mgsq-day.is-end{background:#16723a;color:#fff;border-radius:8px}.mgsq-day.is-today{box-shadow:inset 0 0 0 1px #16723a}.mgsq-date-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;border-top:1px solid #e4e7ec;padding:12px 16px}.mgsq-date-summary{font-weight:600;color:#344054}.mgsq-date-actions{display:flex;gap:8px}.mgsq-date-actions .button{min-width:82px}.mgsq-date-error{display:none;color:#b42318;font-size:12px;padding:0 16px 10px}.mgsq-date-error.is-visible{display:block}
        @media(max-width:1180px){.mgsq-report .filters{grid-template-columns:repeat(4,minmax(150px,1fr))}}
        @media(max-width:782px){.mgsq-report .filters{grid-template-columns:1fr}.mgsq-range-field{grid-column:span 1}.mgsq-date-popover{position:fixed;left:12px;right:12px;top:56px;width:auto;max-height:calc(100vh - 72px);overflow:auto}.mgsq-date-popover.is-open{display:block}.mgsq-date-shortcuts{border-right:0;border-bottom:1px solid #e4e7ec;display:grid;grid-template-columns:1fr 1fr}.mgsq-calendars{grid-template-columns:1fr}.mgsq-calendar-panel:nth-child(2){display:none}.mgsq-calendar-panel+ .mgsq-calendar-panel{border-left:0}.mgsq-mobile-next{display:inline-block}.mgsq-date-footer{align-items:flex-start;flex-direction:column}.mgsq-date-actions{width:100%}.mgsq-date-actions .button{flex:1}}
        </style>';
        echo '<form class="filters" method="get" id="mgsqReportFilters"><input type="hidden" name="page" value="mgs-quiz-report"><input type="hidden" name="slug" value="'.esc_attr( $filters['slug'] ).'">';
        echo '<div class="mgsq-range-field"><label>Período</label><button type="button" class="mgsq-range-trigger" id="mgsqDateRangeTrigger" aria-haspopup="dialog" aria-expanded="false"><span id="mgsqDateRangeLabel"></span><span class="dashicons dashicons-calendar-alt" aria-hidden="true"></span></button><input type="hidden" name="from" id="mgsqDateFrom" value="'.esc_attr( $filters['from'] ).'"><input type="hidden" name="to" id="mgsqDateTo" value="'.esc_attr( $filters['to'] ).'">';
        echo '<div class="mgsq-date-popover" id="mgsqDatePopover" role="dialog" aria-label="Selecionar período"><div class="mgsq-date-shortcuts"><button type="button" class="mgsq-date-shortcut" data-preset="today">Hoje</button><button type="button" class="mgsq-date-shortcut" data-preset="yesterday">Ontem</button><button type="button" class="mgsq-date-shortcut" data-preset="last7">Últimos 7 dias</button><button type="button" class="mgsq-date-shortcut" data-preset="last30">Últimos 30 dias</button><button type="button" class="mgsq-date-shortcut" data-preset="thisMonth">Este mês</button><button type="button" class="mgsq-date-shortcut" data-preset="lastMonth">Mês anterior</button><button type="button" class="mgsq-date-shortcut" data-preset="custom">Personalizado</button></div>';
        echo '<div class="mgsq-date-main"><div class="mgsq-calendars"><div class="mgsq-calendar-panel" data-calendar-index="0"><div class="mgsq-calendar-head"><button type="button" data-shift="-1" aria-label="Mês anterior">‹</button><span class="mgsq-month-title"></span><button type="button" class="mgsq-mobile-next" data-shift="1" aria-label="Próximo mês">›</button></div><div class="mgsq-weekdays"><span>Dom</span><span>Seg</span><span>Ter</span><span>Qua</span><span>Qui</span><span>Sex</span><span>Sáb</span></div><div class="mgsq-days"></div></div><div class="mgsq-calendar-panel" data-calendar-index="1"><div class="mgsq-calendar-head"><span></span><span class="mgsq-month-title"></span><button type="button" data-shift="1" aria-label="Próximo mês">›</button></div><div class="mgsq-weekdays"><span>Dom</span><span>Seg</span><span>Ter</span><span>Qua</span><span>Qui</span><span>Sex</span><span>Sáb</span></div><div class="mgsq-days"></div></div></div><div class="mgsq-date-error" id="mgsqDateError">Selecione a data inicial e a data final.</div><div class="mgsq-date-footer"><span class="mgsq-date-summary" id="mgsqDateSummary"></span><div class="mgsq-date-actions"><button type="button" class="button" id="mgsqDateCancel">Cancelar</button><button type="button" class="button button-primary" id="mgsqDateApply">Aplicar</button></div></div></div></div></div>';
        echo '<div><label>Gestor</label><select name="gestor"><option value="">Todos</option>'; foreach ( $gestores as $g ) echo '<option '.selected( $filters['gestor'], $g, false ).' value="'.esc_attr($g).'">'.esc_html($g).'</option>'; echo '</select></div>';
        echo '<div><label>Parcela</label><select name="parcela"><option value="">Todas</option>'; foreach ( $parcelas as $p ) echo '<option '.selected( $filters['parcela'], $p, false ).' value="'.esc_attr($p).'">'.esc_html($p).'</option>'; echo '</select></div>';
        echo '<div><label>Buscar</label><input name="q" value="'.esc_attr( $filters['q'] ).'" placeholder="Nome, telefone, campanha"></div>';
        echo '<div><label>Leads por página</label><select name="leads_per_page">'; foreach ( array(5,10,25,50,100,250,500) as $n ) echo '<option '.selected( (int)$filters['leads_per_page'], $n, false ).' value="'.$n.'">'.$n.'</option>'; echo '</select></div>';
        echo '<div><button class="button">Filtrar relatório</button></div></form>';
        ?>
        <script>
        (function(){
          var form=document.getElementById('mgsqReportFilters'),trigger=document.getElementById('mgsqDateRangeTrigger'),popover=document.getElementById('mgsqDatePopover'),fromInput=document.getElementById('mgsqDateFrom'),toInput=document.getElementById('mgsqDateTo'),label=document.getElementById('mgsqDateRangeLabel'),summary=document.getElementById('mgsqDateSummary'),error=document.getElementById('mgsqDateError');
          if(!trigger||!popover||!fromInput||!toInput)return;
          var months=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
          var appliedStart=fromInput.value,appliedEnd=toInput.value,draftStart=appliedStart,draftEnd=appliedEnd,activePreset='custom';
          function parseIso(value){var p=(value||'').split('-').map(Number);return p.length===3&&p[0]&&p[1]&&p[2]?new Date(p[0],p[1]-1,p[2],12,0,0,0):null;}
          function iso(date){return date.getFullYear()+'-'+String(date.getMonth()+1).padStart(2,'0')+'-'+String(date.getDate()).padStart(2,'0');}
          function br(value){var d=parseIso(value);return d?String(d.getDate()).padStart(2,'0')+'/'+String(d.getMonth()+1).padStart(2,'0')+'/'+d.getFullYear():'';}
          function addDays(date,n){var d=new Date(date.getTime());d.setDate(d.getDate()+n);return d;}
          function firstOfMonth(date){return new Date(date.getFullYear(),date.getMonth(),1,12,0,0,0);}
          var base=parseIso(draftStart)||new Date(),viewMonth=firstOfMonth(base);
          function setActivePreset(name){activePreset=name;popover.querySelectorAll('[data-preset]').forEach(function(btn){btn.classList.toggle('is-active',btn.dataset.preset===name);});}
          function updateText(){label.textContent=br(appliedStart)+' — '+br(appliedEnd);summary.textContent=draftStart?(br(draftStart)+(draftEnd?' — '+br(draftEnd):' — selecione a data final')):'Selecione o período';}
          function monthFor(index){return new Date(viewMonth.getFullYear(),viewMonth.getMonth()+index,1,12,0,0,0);}
          function render(){
            popover.querySelectorAll('.mgsq-calendar-panel').forEach(function(panel){
              var index=Number(panel.dataset.calendarIndex||0),month=monthFor(index),year=month.getFullYear(),monthIndex=month.getMonth(),days=new Date(year,monthIndex+1,0).getDate(),offset=month.getDay(),grid=panel.querySelector('.mgsq-days');
              panel.querySelector('.mgsq-month-title').textContent=months[monthIndex]+' '+year;grid.innerHTML='';
              for(var blank=0;blank<offset;blank++){var empty=document.createElement('span');empty.className='mgsq-day-empty';grid.appendChild(empty);}
              for(var day=1;day<=days;day++){var date=new Date(year,monthIndex,day,12,0,0,0),value=iso(date),button=document.createElement('button');button.type='button';button.className='mgsq-day';button.dataset.date=value;button.textContent=day;button.setAttribute('aria-label',br(value));if(value===draftStart)button.classList.add('is-start');if(value===draftEnd)button.classList.add('is-end');if(draftStart&&draftEnd&&value>draftStart&&value<draftEnd)button.classList.add('is-range');if(value===iso(new Date()))button.classList.add('is-today');button.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();selectDate(e.currentTarget.dataset.date);});grid.appendChild(button);}
            });
            updateText();
          }
          function selectDate(value){
            if(!draftStart||(draftStart&&draftEnd)){draftStart=value;draftEnd='';setActivePreset('custom');}
            else if(value<draftStart){draftStart=value;draftEnd='';setActivePreset('custom');}
            else{draftEnd=value;setActivePreset('custom');}
            error.classList.remove('is-visible');render();
          }
          function preset(name){
            var today=new Date(),start,end;
            today=new Date(today.getFullYear(),today.getMonth(),today.getDate(),12,0,0,0);
            if(name==='today'){start=end=today;}
            else if(name==='yesterday'){start=end=addDays(today,-1);}
            else if(name==='last7'){end=today;start=addDays(today,-6);}
            else if(name==='last30'){end=today;start=addDays(today,-29);}
            else if(name==='thisMonth'){start=new Date(today.getFullYear(),today.getMonth(),1,12);end=today;}
            else if(name==='lastMonth'){start=new Date(today.getFullYear(),today.getMonth()-1,1,12);end=new Date(today.getFullYear(),today.getMonth(),0,12);}
            else{setActivePreset('custom');return;}
            draftStart=iso(start);draftEnd=iso(end);viewMonth=firstOfMonth(start);setActivePreset(name);render();
          }
          function applyDraft(){if(!draftStart||!draftEnd){error.classList.add('is-visible');return;}appliedStart=draftStart;appliedEnd=draftEnd;fromInput.value=appliedStart;toInput.value=appliedEnd;close();updateText();if(form){if(typeof form.requestSubmit==='function'){form.requestSubmit();}else{form.submit();}}}
          function open(){draftStart=appliedStart;draftEnd=appliedEnd;viewMonth=firstOfMonth(parseIso(draftStart)||new Date());error.classList.remove('is-visible');popover.classList.add('is-open');trigger.setAttribute('aria-expanded','true');render();}
          function close(){popover.classList.remove('is-open');trigger.setAttribute('aria-expanded','false');}
          trigger.addEventListener('click',function(){popover.classList.contains('is-open')?close():open();});
          popover.querySelectorAll('[data-preset]').forEach(function(shortcut){shortcut.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();preset(e.currentTarget.dataset.preset);});});
          popover.querySelectorAll('[data-shift]').forEach(function(nav){nav.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();viewMonth=new Date(viewMonth.getFullYear(),viewMonth.getMonth()+Number(e.currentTarget.dataset.shift),1,12);render();});});
          document.getElementById('mgsqDateCancel').addEventListener('click',function(){draftStart=appliedStart;draftEnd=appliedEnd;close();});
          document.getElementById('mgsqDateApply').addEventListener('click',applyDraft);
          document.addEventListener('click',function(e){if(popover.classList.contains('is-open')&&!popover.contains(e.target)&&!trigger.contains(e.target))close();});
          document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});
          updateText();
        })();
        </script>
        <?php
        echo '<div class="mgsq-stats"><div class="mgsq-stat">Total de leads<b>'.esc_html( number_format_i18n( $total ) ).'</b></div><div class="mgsq-stat">Telefones únicos<b>'.esc_html( number_format_i18n( $unique ) ).'</b></div><div class="mgsq-stat">Média por dia<b>'.esc_html( $avg ).'</b></div><div class="mgsq-stat">Período<b>'.esc_html( $period_days ).' dia(s)</b></div><div class="mgsq-stat">Custo por registro<b>R$ 0,08</b></div><div class="mgsq-stat">Custo estimado de SMS<b>'.esc_html( 'R$ ' . number_format( $sms_total_cost_centavos / 100, 2, ',', '.' ) ).'</b></div><div class="mgsq-stat">Receita SMS — Smart Bidding<b>'.( $sms_revenue_has_data ? esc_html( 'R$ ' . number_format( (int) $sms_revenue['display_revenue_cents'] / 100, 2, ',', '.' ) ) : 'Não disponível' ).'</b><small>'.esc_html( 'Valor líquido exibido na SB. Cobertura: ' . $sms_revenue_coverage ).'</small></div><div class="mgsq-stat">ROI estimado de SMS<b>'.esc_html( $sms_roi_value ).'</b><small>'.esc_html( $sms_roi_note ).'</small></div></div>';
        echo '<div class="card"><h2>Por parcela escolhida</h2><div class="mgsq-pills">'; foreach ( $by_parcela as $r ) echo '<span>'.esc_html($r['k']).' <b>'.(int)$r['c'].'</b></span>'; echo '</div></div>';

        echo '<div class="card"><h2>Custo estimado de SMS por quiz</h2><p>Base: todos os registros absorvidos no relatório com os filtros atuais, a R$ 0,08 por registro.</p><div class="mgsq-table-wrap"><table class="widefat striped"><thead><tr><th>Quiz</th><th>Slug</th><th>Registros absorvidos</th><th>Custo unitário</th><th>Custo estimado</th></tr></thead><tbody>';
        if ( ! $by_quiz_cost ) {
            echo '<tr><td colspan="5">Nenhum registro encontrado para os filtros atuais.</td></tr>';
        }
        foreach ( $by_quiz_cost as $r ) {
            $quiz_slug = $r['k'];
            $quiz_name = $quiz_names[ $quiz_slug ] ?? $quiz_slug;
            $quiz_cost_centavos = (int) $r['c'] * $sms_unit_cost_centavos;
            echo '<tr><td>'.esc_html( $quiz_name ).'</td><td><code>'.esc_html( $quiz_slug ).'</code></td><td>'.esc_html( number_format_i18n( (int) $r['c'] ) ).'</td><td>R$ 0,08</td><td><strong>'.esc_html( 'R$ ' . number_format( $quiz_cost_centavos / 100, 2, ',', '.' ) ).'</strong></td></tr>';
        }
        echo '</tbody></table></div></div>';

        echo '<div class="mgsq-flex"><div class="card" id="mgsqDaysCard" data-nonce="'.esc_attr( wp_create_nonce( 'mgs_quiz_chart_days' ) ).'" data-slug="'.esc_attr( $filters['slug'] ).'" data-gestor="'.esc_attr( $filters['gestor'] ).'" data-parcela="'.esc_attr( $filters['parcela'] ).'" data-q="'.esc_attr( $filters['q'] ).'"><h2>Leads por dia</h2>';
        echo '<div class="mgsq-chart-controls"><div><label>Data inicial</label><input type="date" id="mgsqChartFrom" value="'.esc_attr( $filters['from'] ).'"></div><div><label>Data final</label><input type="date" id="mgsqChartTo" value="'.esc_attr( $filters['to'] ).'"></div><div><label>Dias por página</label><select id="mgsqChartPerPage">'; foreach ( array(5,10,15,30,60) as $n ) echo '<option '.selected( (string)$filters['days_per_page'], (string)$n, false ).' value="'.$n.'">'.$n.'</option>'; echo '<option '.selected( $filters['days_per_page'], 'all', false ).' value="all">Todos</option></select></div><div><button type="button" class="button" id="mgsqChartApply">Aplicar no bloco</button></div></div>';
        echo '<div id="mgsqChartInner">'.self::render_days_chart_inner( $by_day, $days_page, $days_pages, $days_total ).'</div></div>';
        echo '<div class="card"><h2>Por gestor</h2>'; foreach ( $by_gestor as $r ) { $pct = $total ? round( 100 * (int)$r['c'] / $total ) : 0; echo '<div class="bar-row"><div class="bar-label">'.esc_html($r['k']).'</div><div class="bar-bg"><div class="bar-fill" style="width:'.$pct.'%"></div></div><b>'.(int)$r['c'].' ('.$pct.'%)</b></div>'; } echo '</div></div>';
        echo '<script>(function(){var card=document.getElementById("mgsqDaysCard"),inner=document.getElementById("mgsqChartInner");if(!card||!inner)return;function load(page){card.classList.add("mgsq-chart-loading");var p=new URLSearchParams();p.set("action","mgs_quiz_chart_days");p.set("nonce",card.dataset.nonce);p.set("slug",card.dataset.slug||"");p.set("gestor",card.dataset.gestor||"");p.set("parcela",card.dataset.parcela||"");p.set("q",card.dataset.q||"");p.set("from",document.getElementById("mgsqChartFrom").value||"");p.set("to",document.getElementById("mgsqChartTo").value||"");p.set("days_per_page",document.getElementById("mgsqChartPerPage").value||"5");p.set("days_page",page||1);fetch(ajaxurl,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:p.toString()}).then(function(r){return r.json();}).then(function(j){if(j&&j.success&&j.data&&j.data.html){inner.innerHTML=j.data.html;}}).finally(function(){card.classList.remove("mgsq-chart-loading");});}document.getElementById("mgsqChartApply").addEventListener("click",function(){load(1);});card.addEventListener("click",function(e){var b=e.target.closest(".mgsq-chart-nav");if(b&&!b.disabled){e.preventDefault();load(b.dataset.page||1);}});card.addEventListener("change",function(e){if(e.target.classList.contains("mgsq-chart-page-input")){load(e.target.value||1);}});})();</script>';

        echo '<div class="card mgsq-leads-card" id="mgsqReportLeadsCard" data-nonce="'.esc_attr( wp_create_nonce( 'mgs_quiz_report_leads' ) ).'" data-slug="'.esc_attr( $filters['slug'] ).'" data-from="'.esc_attr( $filters['from'] ).'" data-to="'.esc_attr( $filters['to'] ).'" data-gestor="'.esc_attr( $filters['gestor'] ).'" data-parcela="'.esc_attr( $filters['parcela'] ).'" data-q="'.esc_attr( $filters['q'] ).'" data-per-page="'.esc_attr( $filters['leads_per_page'] ).'"><div class="mgsq-toolbar"><h2>Leads ('.(int)$leads_total.')</h2></div><div id="mgsqReportLeadsInner">'.self::render_report_leads_inner( $leads, $leads_total, $leads_page, $leads_pages ).'</div></div>';
        echo '<script>(function(){var card=document.getElementById("mgsqReportLeadsCard"),inner=document.getElementById("mgsqReportLeadsInner");if(!card||!inner)return;function load(page){card.classList.add("mgsq-chart-loading");var p=new URLSearchParams();p.set("action","mgs_quiz_report_leads");p.set("nonce",card.dataset.nonce);p.set("slug",card.dataset.slug||"");p.set("from",card.dataset.from||"");p.set("to",card.dataset.to||"");p.set("gestor",card.dataset.gestor||"");p.set("parcela",card.dataset.parcela||"");p.set("q",card.dataset.q||"");p.set("leads_per_page",card.dataset.perPage||"5");p.set("leads_page",page||1);fetch(ajaxurl,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:p.toString()}).then(function(r){return r.json();}).then(function(j){if(j&&j.success&&j.data&&j.data.html){inner.innerHTML=j.data.html;}}).finally(function(){card.classList.remove("mgsq-chart-loading");});}card.addEventListener("click",function(e){var b=e.target.closest(".mgsq-leads-nav");if(b&&!b.disabled){e.preventDefault();load(b.dataset.page||1);}});card.addEventListener("change",function(e){if(e.target.classList.contains("mgsq-leads-page-input")){load(e.target.value||1);}});})();</script>';
        echo '</div>';
    }

    public static function render_sms_settings() {
        $presets = self::sms_presets();
        ?>
        <div class="wrap mgsq-sms-settings">
          <h1>SMS Funnel</h1>
          <p>Gerencie aqui a identificação e a URL add-lead de cada gestor. As alterações são propagadas para todas as quizzes que usam o gestor.</p>
          <?php if ( ! empty( $_GET['saved'] ) ) : ?>
            <div class="notice notice-success"><p>Configurações SMS salvas. <?php echo (int) ( $_GET['updated'] ?? 0 ); ?> quiz(es) atualizada(s).</p></div>
          <?php endif; ?>
          <?php if ( ! empty( $_GET['sms_error'] ) ) : ?>
            <div class="notice notice-error"><p>Não foi possível salvar. Todos os nomes são obrigatórios e as URLs devem ser endpoints HTTPS válidos do SMS Funnel terminando em /add-lead.</p></div>
          <?php endif; ?>
          <style>
            .mgsq-sms-settings{max-width:1280px}.mgsq-sms-admin-grid{display:grid;gap:14px;margin:20px 0}.mgsq-sms-admin-row{display:grid;grid-template-columns:100px 280px minmax(440px,1fr);gap:14px;align-items:end;background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:16px}.mgsq-sms-admin-row label{display:block;font-weight:700;margin-bottom:6px}.mgsq-sms-admin-code{font-size:18px;font-weight:800;color:#15803d;padding:12px 0}.mgsq-sms-admin-row input{width:100%;min-height:46px;border:1px solid #d0d5dd;border-radius:10px;padding:10px 12px;font-size:15px}@media(max-width:960px){.mgsq-sms-admin-row{grid-template-columns:1fr}}
          </style>
          <form method="post">
            <?php wp_nonce_field( 'mgs_quiz_save' ); ?>
            <input type="hidden" name="mgs_quiz_action" value="save_sms_presets">
            <div class="mgsq-sms-admin-grid">
              <?php foreach ( $presets as $code => $preset ) : ?>
                <div class="mgsq-sms-admin-row">
                  <div><label>Gestor</label><div class="mgsq-sms-admin-code"><?php echo esc_html( $code ); ?></div></div>
                  <div><label for="sms-label-<?php echo esc_attr( $code ); ?>">Nome/label</label><input id="sms-label-<?php echo esc_attr( $code ); ?>" name="sms_labels[<?php echo esc_attr( $code ); ?>]" required value="<?php echo esc_attr( $preset['label'] ); ?>"></div>
                  <div><label for="sms-url-<?php echo esc_attr( $code ); ?>">URL add-lead</label><input id="sms-url-<?php echo esc_attr( $code ); ?>" type="url" name="sms_urls[<?php echo esc_attr( $code ); ?>]" required value="<?php echo esc_attr( $preset['url'] ); ?>"></div>
                </div>
              <?php endforeach; ?>
            </div>
            <?php submit_button( 'Salvar configurações SMS' ); ?>
          </form>
        </div>
        <?php
    }

    public static function render_edit() {
        global $wpdb;
        $t = $wpdb->prefix . 'mgs_quiz_config';
        $id = isset( $_GET['id'] ) ? sanitize_text_field( $_GET['id'] ) : '';
        $row = $id ? $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$t} WHERE id = %s", $id ), ARRAY_A ) : array();
        $get = function( $k, $d = '' ) use ( $row ) { return isset( $row[ $k ] ) ? $row[ $k ] : $d; };
        $slug = $get( 'slug' );
        $public_url = $slug ? home_url( '/' . $slug . '/' ) : '';
        $opts_text = '';
        if ( ! empty( $row['options'] ) ) { $d = json_decode( $row['options'], true ); if ( is_array( $d ) ) $opts_text = implode( "\n", $d ); }
        $redirect_rows = array();
        if ( $get( 'redirect_url' ) ) {
            $redirect_rows[] = array( 'url' => $get( 'redirect_url' ), 'weight' => (int) $get( 'redirect_url_weight', 100 ) );
        }
        $redirect_extra = json_decode( (string) $get( 'redirect_variants' ), true );
        if ( is_array( $redirect_extra ) ) {
            foreach ( $redirect_extra as $rv ) {
                if ( ! empty( $rv['url'] ) ) {
                    $redirect_rows[] = array( 'url' => $rv['url'], 'weight' => isset( $rv['weight'] ) ? (int) $rv['weight'] : 0 );
                }
            }
        }
        if ( empty( $redirect_rows ) ) {
            $redirect_rows[] = array( 'url' => '', 'weight' => 100 );
        }
        $sms_rows = json_decode( (string) $get( 'sms_funnel_urls' ), true );
        if ( ! is_array( $sms_rows ) ) $sms_rows = array();
        $sms_presets = self::sms_presets();
        $sms_selected_code = '';
        foreach ( $sms_rows as $sr ) {
            $is_active = ! isset( $sr['active'] ) || (int) $sr['active'];
            if ( $is_active && ! empty( $sr['default'] ) && ! empty( $sr['gestor_code'] ) ) {
                $sms_selected_code = strtoupper( $sr['gestor_code'] );
                break;
            }
        }
        if ( ! $sms_selected_code ) {
            foreach ( $sms_rows as $sr ) {
                $is_active = ! isset( $sr['active'] ) || (int) $sr['active'];
                if ( $is_active && ! empty( $sr['gestor_code'] ) && ! empty( $sr['url'] ) ) {
                    $sms_selected_code = strtoupper( $sr['gestor_code'] );
                    break;
                }
            }
        }
        if ( $sms_selected_code && isset( $sms_presets[ $sms_selected_code ] ) ) {
            $sms_rows = array( array_merge( $sms_presets[ $sms_selected_code ], array( 'active' => 1, 'default' => 1 ) ) );
        }
        if ( empty( $sms_rows ) ) {
            $sms_rows[] = array( 'gestor_code' => '', 'label' => '', 'url' => '' );
        }
        $sms_default_found = false;
        foreach ( $sms_rows as $sr ) {
            if ( ! empty( $sr['default'] ) ) { $sms_default_found = true; break; }
        }
        $lead_count = $slug ? (int) $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->prefix}mgs_quiz_leads WHERE quiz_slug = %s", $slug ) ) : 0;
        ?>
        <div class="wrap mgsq-edit">
        <style>
          .mgsq-edit{max-width:1480px}.mgsq-top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin:14px 0 22px}.mgsq-back{text-decoration:none;color:#2271b1}.mgsq-title h1{margin:6px 0 4px;font-size:28px}.mgsq-sub{color:#646970}.mgsq-actions{display:flex;gap:10px;align-items:center}.mgsq-open{color:#15803d;font-weight:600}.mgsq-tabs{display:inline-flex;background:#f0f0f1;border-radius:12px;padding:4px;margin:0 0 18px}.mgsq-tabs span,.mgsq-tabs a{padding:10px 18px;border-radius:9px;text-decoration:none}.mgsq-tabs span{background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.08);font-weight:600}.mgsq-tabs a{color:#646970}.mgsq-card{background:#fff;border:1px solid #dcdcde;border-radius:16px;padding:22px;margin:18px 0;box-shadow:0 2px 10px rgba(0,0,0,.035)}.mgsq-card h2{font-size:22px;margin:0 0 18px}.mgsq-grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}.mgsq-grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px}.mgsq-field label{display:block;font-weight:700;margin:0 0 7px}.mgsq-field input:not([type]),.mgsq-field input[type=text],.mgsq-field input[type=url],.mgsq-field input[type=number],.mgsq-field textarea{width:100%;max-width:none;border-radius:12px;border:1px solid #d0d5dd;padding:14px 16px;background:#fff;box-shadow:0 1px 2px rgba(16,24,40,.03);font-size:16px;line-height:1.45}.mgsq-field input:not([type]),.mgsq-field input[type=text],.mgsq-field input[type=url],.mgsq-field input[type=number]{min-height:48px}.mgsq-field textarea{min-height:112px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}.mgsq-field input:focus,.mgsq-field textarea:focus{border-color:#15803d;box-shadow:0 0 0 3px rgba(21,128,61,.12);outline:0}.mgsq-help{font-size:12px;color:#667085;margin-top:6px}.mgsq-preview-row{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:12px}.mgsq-logo-bg,.mgsq-flag-bg{background:var(--mgs-primary,#1e8323);border-radius:12px;min-height:92px;display:flex;align-items:center;justify-content:center;padding:14px}.mgsq-logo-bg img{max-height:70px;max-width:90%}.mgsq-flag-bg img{max-height:72px;max-width:90%}.mgsq-car-preview img{max-width:220px;border-radius:12px;border:1px solid #eee;background:#fff}.mgsq-sms-box{border:1px solid #e4e7ec;background:#fcfcfd;border-radius:14px;padding:16px}.mgsq-save{position:sticky;bottom:18px;display:flex;justify-content:flex-end;margin-top:18px}.mgsq-save button{font-size:16px;padding:8px 18px!important;border-radius:10px!important;background:#15803d!important;border-color:#15803d!important}.mgsq-colorline{display:flex;gap:10px;align-items:center}.mgsq-colorline input[type=color]{width:48px;height:42px;padding:2px;border-radius:9px}.mgsq-muted{color:#667085}.mgsq-redirect-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px}.mgsq-redirect-row{display:grid;grid-template-columns:minmax(0,1fr) 110px 86px;gap:10px;align-items:center;margin:10px 0}.mgsq-redirect-row:first-child .mgsq-remove-redirect{visibility:hidden}.mgsq-redirect-dist{color:#667085;font-size:13px;margin-top:8px}.mgsq-add-redirect{border-radius:10px!important}.mgsq-remove-redirect{color:#b42318;border:0;background:transparent;cursor:pointer;font-weight:700}@media(max-width:900px){.mgsq-grid2,.mgsq-grid3,.mgsq-preview-row{grid-template-columns:1fr}.mgsq-top{display:block}.mgsq-actions{margin-top:12px}}
        </style>
        <div class="mgsq-top">
          <div class="mgsq-title">
            <a class="mgsq-back" href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-quiz' ) ); ?>">← Voltar</a>
            <h1><?php echo esc_html( $get( 'name', 'Novo Quiz' ) ?: 'Novo Quiz' ); ?></h1>
            <div class="mgsq-sub">URL pública: <?php echo esc_html( $slug ? '/' . $slug . '/' : 'defina o slug' ); ?> · <?php echo (int) $lead_count; ?> leads</div>
          </div>
          <div class="mgsq-actions">
            <?php if ( $slug ) : ?><a class="button" href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-quiz-report&slug=' . urlencode( $slug ) ) ); ?>">Relatório</a><?php endif; ?>
            <?php if ( $public_url ) : ?><a class="mgsq-open" target="_blank" href="<?php echo esc_url( $public_url ); ?>">Abrir página pública ↗</a><?php endif; ?>
          </div>
        </div>
        <div class="mgsq-tabs"><span>Editar Quiz</span><?php if ( $slug ) : ?><a href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-quiz-report&slug=' . urlencode( $slug ) ) ); ?>">Leads (<?php echo (int) $lead_count; ?>)</a><?php endif; ?></div>
        <form method="post" style="--mgs-primary:<?php echo esc_attr( $get( 'primary_color', '#1e8323' ) ); ?>">
            <?php wp_nonce_field( 'mgs_quiz_save' ); ?>
            <input type="hidden" name="mgs_quiz_action" value="save">
            <input type="hidden" name="id" value="<?php echo esc_attr( $get('id') ); ?>">

            <section class="mgsq-card"><h2>Identificação</h2><div class="mgsq-grid2">
              <div class="mgsq-field"><label>Nome do quiz (interno)</label><input name="name" value="<?php echo esc_attr( $get('name') ); ?>"><div class="mgsq-help">Usado só na lista de admin.</div></div>
              <div class="mgsq-field"><label>Slug (URL pública)</label><input name="slug" required value="<?php echo esc_attr( $get('slug') ); ?>" placeholder="quiz-car-parcelas-g003"><div class="mgsq-help">G002/default usa <code>quiz-car-parcelas</code>; os outros usam sufixo g001/g003...</div></div>
              <div class="mgsq-field"><label>Modelo visual</label><select name="layout_template"><option value="" <?php selected( $get('layout_template'), '' ); ?>>Quiz padrão</option><option value="fmybc_sms" <?php selected( $get('layout_template'), 'fmybc_sms' ); ?>>Modelo FMYBC / SMS</option><option value="quiz_maker_sb" <?php selected( $get('layout_template'), 'quiz_maker_sb' ); ?>>Quiz Maker SB</option></select><div class="mgsq-help">O modelo Quiz Maker SB replica o quiz de duas etapas (pergunta e formulário), mantendo o mesmo backend, SMS Funnel e redirecionamento da MGS.</div></div>
            </div></section>

            <section class="mgsq-card"><h2>Textos da página</h2>
              <div class="mgsq-grid2"><div class="mgsq-field"><label>Título principal</label><input name="title" value="<?php echo esc_attr( $get('title') ); ?>"></div><div class="mgsq-field"><label>Subtítulo</label><input name="subtitle" value="<?php echo esc_attr( $get('subtitle') ); ?>"></div></div>
              <div class="mgsq-field" style="margin-top:18px"><label>Pergunta do passo 1</label><input name="question" value="<?php echo esc_attr( $get('question') ); ?>"></div>
              <div class="mgsq-field" style="margin-top:18px"><label>Opções de valor (1 por linha)</label><textarea name="options" rows="5"><?php echo esc_textarea( $opts_text ); ?></textarea></div>
            </section>

            <section class="mgsq-card"><h2>Formulário (passo 2)</h2>
              <div class="mgsq-field"><label>Título do formulário</label><input name="form_title" value="<?php echo esc_attr( $get('form_title') ); ?>"></div>
              <div class="mgsq-grid2" style="margin-top:18px"><div class="mgsq-field"><label>Label do campo Nome</label><input name="form_name_label" value="<?php echo esc_attr( $get('form_name_label','Nome') ); ?>"></div><div class="mgsq-field"><label>Label do campo Telefone</label><input name="form_phone_label" value="<?php echo esc_attr( $get('form_phone_label','Telefone') ); ?>"></div></div>
              <div class="mgsq-grid2" style="margin-top:18px"><div class="mgsq-field"><label>Máscara do telefone</label><input name="form_phone_mask" value="<?php echo esc_attr( $get('form_phone_mask','(99) 99999-9999') ); ?>"><div class="mgsq-help">Use 9 para cada dígito. Ex: (99) 99999-9999</div></div><div class="mgsq-field"><label>Texto do botão de envio</label><input name="form_submit_label" value="<?php echo esc_attr( $get('form_submit_label','ESCOLHER CARRO') ); ?>"></div></div>
              <div class="mgsq-sms-box" style="margin-top:18px"><h3>Link SMS Funnel desta quiz</h3><p class="mgsq-muted">Escolha abaixo o único link SMS Funnel que esta quiz vai usar. Todo lead desta quiz vai para o link selecionado, com ou sem UTMs.</p><div class="mgsq-field mgsq-sms-preset"><label>Gestor / lista SMS Funnel</label><select name="sms_preset_code" id="mgsqSmsPreset" required><option value="">Selecione um gestor</option><?php foreach ( $sms_presets as $preset_code => $preset ) : ?><option value="<?php echo esc_attr( $preset_code ); ?>" data-label="<?php echo esc_attr( $preset['label'] ); ?>" data-url="<?php echo esc_attr( $preset['url'] ); ?>" <?php selected( $sms_selected_code, $preset_code ); ?>><?php echo esc_html( $preset['label'] ); ?></option><?php endforeach; ?></select><div class="mgsq-help">Ao selecionar, Gestor, Nome/label e URL add-lead são preenchidos automaticamente.</div></div><style>.mgsq-sms-preset{margin:16px 0 12px;max-width:520px}.mgsq-sms-preset select{width:100%;min-height:48px;border-radius:12px;border:1px solid #d0d5dd;padding:8px 14px;font-size:16px}.mgsq-sms-rows{display:grid;gap:12px;margin-top:12px}.mgsq-sms-row{display:grid;grid-template-columns:220px minmax(360px,1fr);gap:10px;align-items:end;background:#f8fafc;border:1px solid #e5e7eb;border-radius:14px;padding:12px}.mgsq-sms-row label{display:block;font-weight:700;font-size:12px;margin:0 0 5px;color:#475467}.mgsq-sms-row input{width:100%;max-width:none;border-radius:10px;border:1px solid #d0d5dd;padding:10px 12px;background:#fff;font-size:14px}.mgsq-sms-tools{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap}.mgsq-sms-json{display:none;margin-top:12px}.mgsq-sms-json.is-open{display:block}@media(max-width:1120px){.mgsq-sms-row{grid-template-columns:1fr}}</style><div id="mgsqSmsRows" class="mgsq-sms-rows"><?php foreach ( $sms_rows as $idx => $sr ) : $is_active = ! isset( $sr['active'] ) || (int) $sr['active']; $is_default = ! empty( $sr['default'] ) || ( ! $sms_default_found && $idx === 0 ); ?><div class="mgsq-sms-row"><div><label>Nome/label</label><input name="sms_labels[]" readonly value="<?php echo esc_attr( $sr['label'] ?? '' ); ?>" placeholder="G001 – Nome"></div><div><label>URL add-lead</label><input type="url" name="sms_urls[]" readonly value="<?php echo esc_attr( $sr['url'] ?? '' ); ?>" placeholder="https://v2.smsfunnel.com.br/integrations/lists/.../add-lead"></div><input type="hidden" name="sms_gestor_codes[]" value="<?php echo esc_attr( $sr['gestor_code'] ?? '' ); ?>"></div><?php endforeach; ?></div><div class="mgsq-sms-tools"><button type="button" class="button-link" id="mgsqToggleSmsJson">Ver JSON técnico</button></div><input type="hidden" name="sms_default_idx" value="0"><input type="hidden" name="sms_funnel_url" value="<?php echo esc_attr( $get('sms_funnel_url') ); ?>"><div class="mgsq-field mgsq-sms-json" id="mgsqSmsJson"><label>JSON técnico (somente conferência)</label><textarea readonly rows="5"><?php echo esc_textarea( $get('sms_funnel_urls') ); ?></textarea></div><p><label><input type="checkbox" name="require_sms_success" value="1" <?php checked( (int) $get('require_sms_success', 1), 1 ); ?>> Exigir sucesso SMS Funnel antes de confirmar/redirecionar</label></p><script>(function(){var rows=document.getElementById('mgsqSmsRows'),toggle=document.getElementById('mgsqToggleSmsJson'),json=document.getElementById('mgsqSmsJson'),preset=document.getElementById('mgsqSmsPreset');if(!rows)return;if(toggle&&json)toggle.addEventListener('click',function(){json.classList.toggle('is-open');});function applyPreset(){if(!preset)return;var opt=preset.options[preset.selectedIndex];if(!opt||!opt.value)return;var row=rows.querySelector('.mgsq-sms-row');if(!row)return;var code=row.querySelector('input[name="sms_gestor_codes[]"]'),label=row.querySelector('input[name="sms_labels[]"]'),url=row.querySelector('input[name="sms_urls[]"]');if(code)code.value=opt.value;if(label)label.value=opt.dataset.label||'';if(url)url.value=opt.dataset.url||'';}if(preset)preset.addEventListener('change',applyPreset);})();</script></div>
            </section>

            <section class="mgsq-card"><h2>Mensagem de sucesso & redirecionamento</h2>
              <div class="mgsq-grid2"><div class="mgsq-field"><label>Título do modal de sucesso</label><input name="success_title" value="<?php echo esc_attr( $get('success_title') ); ?>"></div><div class="mgsq-field"><label>Mensagem do modal de sucesso</label><input name="success_message" value="<?php echo esc_attr( $get('success_message') ); ?>"></div></div>
              <div class="mgsq-field" style="margin-top:18px">
                <div class="mgsq-redirect-head"><label>URLs de redirecionamento (split de tráfego)</label><button type="button" class="button mgsq-add-redirect" id="mgsqAddRedirect">+ Adicionar URL</button></div>
                <div id="mgsqRedirectRows">
                  <?php foreach ( $redirect_rows as $idx => $rv ) : ?>
                    <div class="mgsq-redirect-row">
                      <input type="url" name="redirect_urls[]" value="<?php echo esc_attr( $rv['url'] ); ?>" placeholder="https://creditoparaveiculo.com/rec-.../">
                      <input type="number" min="0" name="redirect_weights[]" value="<?php echo esc_attr( $rv['weight'] ); ?>" aria-label="Peso">
                      <button type="button" class="mgsq-remove-redirect">Remover</button>
                    </div>
                  <?php endforeach; ?>
                </div>
                <div class="mgsq-redirect-dist" id="mgsqRedirectDist">Parâmetros da URL (utm_*, gclid, fbclid etc.) são repassados automaticamente.</div>
                <div class="mgsq-help">Use os pesos como porcentagem operacional. Ex.: uma URL com 100 = 100%; duas URLs com 50/50 = metade para cada.</div>
              </div>
              <div class="mgsq-grid2" style="margin-top:18px"><div class="mgsq-field"><label>Tempo até redirecionar (ms)</label><input type="number" name="redirect_delay_ms" value="<?php echo esc_attr( $get('redirect_delay_ms',1800) ); ?>"><div class="mgsq-help">1800 ms = 1,8 segundos.</div></div></div>
              <script>
              (function(){
                var rows=document.getElementById('mgsqRedirectRows');
                var add=document.getElementById('mgsqAddRedirect');
                var dist=document.getElementById('mgsqRedirectDist');
                if(!rows||!add) return;
                function makeRow(url, weight){
                  var row=document.createElement('div'); row.className='mgsq-redirect-row';
                  row.innerHTML='<input type="url" name="redirect_urls[]" placeholder="https://creditoparaveiculo.com/rec-.../" value="'+(url||'').replace(/"/g,'&quot;')+'"><input type="number" min="0" name="redirect_weights[]" aria-label="Peso" value="'+(weight||100)+'"><button type="button" class="mgsq-remove-redirect">Remover</button>';
                  rows.appendChild(row); bind(row); update();
                }
                function bind(row){
                  var rm=row.querySelector('.mgsq-remove-redirect');
                  row.querySelectorAll('input').forEach(function(i){ i.addEventListener('input', update); });
                  if(rm) rm.addEventListener('click', function(){ if(rows.children.length>1){ row.remove(); update(); } });
                }
                function update(){
                  var total=0, parts=[];
                  rows.querySelectorAll('.mgsq-redirect-row').forEach(function(row, idx){
                    var weight=Number((row.querySelector('input[name="redirect_weights[]"]')||{}).value)||0;
                    total+=weight;
                    parts.push((idx===0?'Padrão':'URL '+(idx+1))+' '+weight+'%');
                  });
                  if(dist) dist.textContent='Distribuição: '+parts.join(' · ')+'. Parâmetros da URL (utm_*, gclid, fbclid etc.) são repassados automaticamente.';
                }
                add.addEventListener('click', function(){ makeRow('', 100); });
                rows.querySelectorAll('.mgsq-redirect-row').forEach(bind); update();
              })();
              </script>
            </section>

            <section class="mgsq-card"><h2>Imagens, rodapé e SEO</h2>
              <div class="mgsq-grid2"><div class="mgsq-field"><label>URL do logo (cabeçalho)</label><input type="url" name="logo_url" value="<?php echo esc_attr( $get('logo_url') ); ?>"><?php if ( $get('logo_url') ) : ?><div class="mgsq-logo-bg"><img src="<?php echo esc_url( $get('logo_url') ); ?>"></div><?php endif; ?><div class="mgsq-help">Preview no fundo da cor principal — use PNG transparente.</div></div><div class="mgsq-field"><label>URL da imagem da bandeira</label><input type="url" name="flag_image_url" value="<?php echo esc_attr( $get('flag_image_url') ); ?>"><?php if ( $get('flag_image_url') ) : ?><div class="mgsq-flag-bg"><img src="<?php echo esc_url( $get('flag_image_url') ); ?>"></div><?php endif; ?></div></div>
              <div class="mgsq-field" style="margin-top:18px"><label>URL da foto do carro</label><input type="url" name="car_image_url" value="<?php echo esc_attr( $get('car_image_url') ); ?>"><?php if ( $get('car_image_url') ) : ?><div class="mgsq-car-preview"><img src="<?php echo esc_url( $get('car_image_url') ); ?>"></div><?php endif; ?></div>
              <div class="mgsq-grid2" style="margin-top:18px"><div class="mgsq-field"><label>Link da Política de Privacidade</label><input type="url" name="privacy_url" value="<?php echo esc_attr( $get('privacy_url') ); ?>"></div><div class="mgsq-field"><label>Link dos Termos de Uso</label><input type="url" name="terms_url" value="<?php echo esc_attr( $get('terms_url') ); ?>"></div></div>
              <div class="mgsq-grid2" style="margin-top:18px"><div class="mgsq-field"><label>Título da página (SEO title)</label><input name="seo_title" value="<?php echo esc_attr( $get('seo_title') ); ?>"></div><div class="mgsq-field"><label>Descrição da página (SEO meta description)</label><input name="seo_description" value="<?php echo esc_attr( $get('seo_description') ); ?>"></div></div>
              <div class="mgsq-field" style="margin-top:18px"><label>Footer HTML</label><textarea name="footer_html" rows="3"><?php echo esc_textarea( $get('footer_html') ); ?></textarea></div>
            </section>

            <section class="mgsq-card"><h2>Tracking — cole aqui seus IDs</h2><div class="mgsq-grid3"><div class="mgsq-field"><label>Meta Pixel ID</label><input name="meta_pixel_id" value="<?php echo esc_attr( $get('meta_pixel_id') ); ?>" placeholder="123456789012345"><div class="mgsq-help">Eventos: PageView, QuizStep1, Lead.</div></div><div class="mgsq-field"><label>Google Tag Manager ID</label><input name="gtm_id" value="<?php echo esc_attr( $get('gtm_id') ); ?>" placeholder="GTM-XXXXXX"><div class="mgsq-help">Eventos enviados ao dataLayer.</div></div><div class="mgsq-field"><label>Cor principal (hex)</label><div class="mgsq-colorline"><input name="primary_color" value="<?php echo esc_attr( $get('primary_color','#1e8323') ); ?>"><input type="color" value="<?php echo esc_attr( $get('primary_color','#1e8323') ); ?>" onchange="this.previousElementSibling.value=this.value"></div></div></div></section>

            <div class="mgsq-save"><button class="button button-primary">Salvar alterações</button></div>
        </form></div>
        <?php
    }

    public static function render_leads() {
        global $wpdb;
        $t = $wpdb->prefix . 'mgs_quiz_leads';
        $slug = isset( $_GET['slug'] ) ? sanitize_title( $_GET['slug'] ) : '';
        $from = isset( $_GET['from'] ) ? sanitize_text_field( $_GET['from'] ) : '';
        $to = isset( $_GET['to'] ) ? sanitize_text_field( $_GET['to'] ) : '';
        $q = isset( $_GET['q'] ) ? sanitize_text_field( $_GET['q'] ) : '';
        $per_page = max( 5, min( 500, (int) ( $_GET['per_page'] ?? 5 ) ) );
        $paged = max( 1, (int) ( $_GET['paged'] ?? 1 ) );
        $params = array();
        $where = ' WHERE 1=1 ';
        if ( $slug ) { $where .= ' AND quiz_slug = %s '; $params[] = $slug; }
        if ( $from ) {
            $from_utc = self::local_date_bound_to_utc( $from );
            if ( $from_utc ) { $where .= ' AND created_at >= %s '; $params[] = $from_utc; }
        }
        if ( $to ) {
            $to_utc = self::local_date_bound_to_utc( $to, true );
            if ( $to_utc ) { $where .= ' AND created_at < %s '; $params[] = $to_utc; }
        }
        if ( $q ) {
            $like = '%' . $wpdb->esc_like( $q ) . '%';
            $where .= ' AND (name LIKE %s OR phone LIKE %s OR quiz_slug LIKE %s OR utm_campaign LIKE %s OR utm_medium LIKE %s) ';
            $params = array_merge( $params, array( $like, $like, $like, $like, $like ) );
        }
        $prep = function( $sql ) use ( $wpdb, $params ) { return $params ? $wpdb->prepare( $sql, $params ) : $sql; };
        $total = (int) $wpdb->get_var( $prep( "SELECT COUNT(*) FROM {$t} {$where}" ) );
        $pages = max( 1, (int) ceil( $total / $per_page ) );
        $paged = min( $paged, $pages );
        $offset = ( $paged - 1 ) * $per_page;
        $rows = $wpdb->get_results( $prep( "SELECT id, created_at, quiz_slug, name, phone, parcela, utm_source, utm_medium, fbclid, gclid, sms_funnel_status FROM {$t} {$where} ORDER BY created_at DESC" ) . $wpdb->prepare( " LIMIT %d OFFSET %d", $per_page, $offset ), ARRAY_A );
        $export_url = wp_nonce_url( admin_url( 'admin-post.php?action=mgs_quiz_export_leads' . ( $slug ? '&slug=' . $slug : '' ) . ( $from ? '&from=' . $from : '' ) . ( $to ? '&to=' . $to : '' ) ), 'mgs_quiz_export' );
        $base_args = array_filter( array( 'page' => 'mgs-quiz-leads', 'slug' => $slug, 'from' => $from, 'to' => $to, 'q' => $q, 'per_page' => $per_page ), function( $v ) { return $v !== '' && $v !== null; } );
        echo '<div class="wrap mgsq-leads"><style>.mgsq-leads{max-width:1480px}.mgsq-leads .filters,.mgsq-leads .card{background:#fff;border:1px solid #dcdcde;border-radius:14px;padding:18px;margin:16px 0}.mgsq-leads .filters{display:grid;grid-template-columns:repeat(7,minmax(120px,1fr));gap:12px;align-items:end}.mgsq-leads label{font-weight:600;display:block;margin-bottom:4px}.mgsq-leads input,.mgsq-leads select{width:100%;max-width:none;min-height:38px}.mgsq-toolbar{display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap}.mgsq-pager{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.mgsq-table{table-layout:fixed}.mgsq-table th,.mgsq-table td{vertical-align:top;overflow-wrap:break-word}.mgsq-table .nowrap{white-space:nowrap}.mgsq-table .col-date{width:130px}.mgsq-table .col-phone{width:120px}.mgsq-table .col-gestor,.mgsq-table .col-sms{width:90px}</style>';
        echo '<h1>Leads <a href="'.esc_url( $export_url ).'" class="page-title-action">Exportar CSV</a></h1>';
        echo '<form class="filters" method="get"><input type="hidden" name="page" value="mgs-quiz-leads">';
        echo '<div><label>Quiz / slug</label><input name="slug" value="'.esc_attr($slug).'" placeholder="quiz-car-parcelas"></div>';
        echo '<div><label>Data inicial</label><input type="date" name="from" value="'.esc_attr($from).'"></div>';
        echo '<div><label>Data final</label><input type="date" name="to" value="'.esc_attr($to).'"></div>';
        echo '<div><label>Buscar</label><input name="q" value="'.esc_attr($q).'" placeholder="Nome, telefone, campanha"></div>';
        echo '<div><label>Leads por página</label><select name="per_page">'; foreach ( array(5,10,25,50,100,250,500) as $n ) echo '<option '.selected( $per_page, $n, false ).' value="'.$n.'">'.$n.'</option>'; echo '</select></div>';
        echo '<div><button class="button">Filtrar</button></div></form>';
        echo '<div class="card"><div class="mgsq-toolbar"><h2>Leads ('.(int)$total.')</h2><div class="mgsq-pager">';
        if ( $paged > 1 ) echo '<a class="button" href="'.esc_url( add_query_arg( array_merge( $base_args, array( 'paged' => $paged - 1 ) ), admin_url( 'admin.php' ) ) ).'">Anterior</a>'; 
        echo '<span>pág. '.(int)$paged.'/'.(int)$pages.' · mostrando '.(int)count($rows).' de '.(int)$total.'</span>';
        if ( $paged < $pages ) echo '<a class="button" href="'.esc_url( add_query_arg( array_merge( $base_args, array( 'paged' => $paged + 1 ) ), admin_url( 'admin.php' ) ) ).'">Próxima</a>'; 
        echo '</div></div><table class="widefat striped mgsq-table"><thead><tr><th class="nowrap">ID</th><th class="col-date">Data</th><th>Quiz</th><th>Nome</th><th class="col-phone">Telefone</th><th>Parcela</th><th>utm_source</th><th class="col-gestor">utm_medium</th><th>fbclid</th><th>gclid</th><th class="col-sms">SMS</th></tr></thead><tbody>';
        foreach ( (array) $rows as $r ) {
            echo '<tr><td class="nowrap">'.esc_html($r['id']).'</td><td>'.esc_html( self::format_created_at( $r['created_at'] ) ).'</td><td>'.esc_html($r['quiz_slug']).'</td><td>'.esc_html($r['name']).'</td><td>'.esc_html($r['phone']).'</td><td>'.esc_html($r['parcela']).'</td><td>'.esc_html($r['utm_source']).'</td><td class="nowrap">'.esc_html(strtoupper($r['utm_medium'])).'</td><td>'.esc_html($r['fbclid']).'</td><td>'.esc_html($r['gclid']).'</td><td class="nowrap">'.esc_html($r['sms_funnel_status']).'</td></tr>';
        }
        echo '</tbody></table></div></div>';
    }

}
