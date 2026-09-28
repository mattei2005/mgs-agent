<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class MGS_Offer_Quiz {
    const OPTION = 'mgs_offer_quiz_items';
    const STATIC_VERSION_OPTION = 'mgs_offer_quiz_static_version';
    const STATIC_MARKER = 'MGS Offer Quiz static';
    const COUNTER_SCHEMA_OPTION = 'mgs_offer_quiz_counter_schema_version';
    const COUNTER_SCHEMA_VERSION = '1';
    const COUNTER_BASELINE = 1892;
    const COUNTER_TIMEZONE = 'America/Sao_Paulo';

    public static function boot() {
        add_action( 'init', array( __CLASS__, 'maybe_install_counter_table' ), 5 );
        add_action( 'init', array( __CLASS__, 'register_rewrite' ) );
        add_action( 'init', array( __CLASS__, 'maybe_sync_static_pages' ), 20 );
        add_action( 'rest_api_init', array( __CLASS__, 'register_rest_routes' ) );
        add_filter( 'query_vars', array( __CLASS__, 'query_vars' ) );
        add_action( 'template_redirect', array( __CLASS__, 'maybe_render' ), 0 );
        add_action( 'admin_menu', array( __CLASS__, 'admin_menu' ) );
        add_action( 'admin_post_mgs_oq_save', array( __CLASS__, 'handle_save' ) );
        add_action( 'admin_post_mgs_oq_duplicate', array( __CLASS__, 'handle_duplicate' ) );
    }

    public static function activate() {
        if ( false === get_option( self::OPTION, false ) ) {
            self::save_items( self::default_items() );
        }
        $counter_result = self::install_counter_table();
        if ( is_wp_error( $counter_result ) ) {
            wp_die( esc_html( $counter_result->get_error_message() ) );
        }
        self::register_rewrite();
        $result = self::sync_static_pages();
        if ( is_wp_error( $result ) ) {
            wp_die( esc_html( $result->get_error_message() ) );
        }
        flush_rewrite_rules();
    }

    public static function deactivate() {
        $result = self::unpublish_all_static();
        if ( is_wp_error( $result ) ) {
            wp_die( esc_html( $result->get_error_message() ) );
        }
        update_option( self::STATIC_VERSION_OPTION, '', false );
        flush_rewrite_rules();
    }

    public static function register_rewrite() {
        add_rewrite_rule(
            '^quiz/(quiz-v1-g00[1-6])/?$',
            'index.php?mgs_oq_slug=$matches[1]',
            'top'
        );
    }

    public static function query_vars( $vars ) {
        $vars[] = 'mgs_oq_slug';
        return $vars;
    }

    public static function items() {
        $items = get_option( self::OPTION, array() );
        return is_array( $items ) ? array_values( array_filter( $items, 'is_array' ) ) : array();
    }

    public static function save_items( $items ) {
        return update_option( self::OPTION, array_values( $items ), false );
    }

    private static function counter_table_name() {
        global $wpdb;
        return $wpdb->prefix . 'mgs_offer_quiz_daily_views';
    }

    public static function install_counter_table() {
        global $wpdb;
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        $table = self::counter_table_name();
        $charset_collate = $wpdb->get_charset_collate();
        $sql = "CREATE TABLE {$table} (
            view_date date NOT NULL,
            view_count bigint(20) unsigned NOT NULL default 0,
            updated_at datetime NOT NULL,
            PRIMARY KEY  (view_date)
        ) {$charset_collate};";
        dbDelta( $sql );
        $exists = $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $wpdb->esc_like( $table ) ) );
        if ( $exists !== $table ) {
            return new WP_Error( 'mgs_oq_counter_table', 'Não foi possível criar a tabela do contador diário.' );
        }
        update_option( self::COUNTER_SCHEMA_OPTION, self::COUNTER_SCHEMA_VERSION, false );
        return true;
    }

    public static function maybe_install_counter_table() {
        if ( get_option( self::COUNTER_SCHEMA_OPTION, '' ) !== self::COUNTER_SCHEMA_VERSION ) {
            self::install_counter_table();
        }
    }

    private static function counter_date() {
        $timezone = new DateTimeZone( self::COUNTER_TIMEZONE );
        return wp_date( 'Y-m-d', null, $timezone );
    }

    public static function increment_daily_counter( $date = '' ) {
        global $wpdb;
        $date = $date ? (string) $date : self::counter_date();
        if ( ! preg_match( '/^\d{4}-\d{2}-\d{2}$/', $date ) ) {
            return new WP_Error( 'mgs_oq_counter_date', 'Data inválida para o contador.' );
        }
        if ( get_option( self::COUNTER_SCHEMA_OPTION, '' ) !== self::COUNTER_SCHEMA_VERSION ) {
            $installed = self::install_counter_table();
            if ( is_wp_error( $installed ) ) {
                return $installed;
            }
        }
        $table = self::counter_table_name();
        $updated_at = gmdate( 'Y-m-d H:i:s' );
        $sql = $wpdb->prepare(
            "INSERT INTO {$table} (view_date, view_count, updated_at)
             VALUES (%s, LAST_INSERT_ID(1), %s)
             ON DUPLICATE KEY UPDATE
               view_count = LAST_INSERT_ID(view_count + 1),
               updated_at = VALUES(updated_at)",
            $date,
            $updated_at
        );
        $result = $wpdb->query( $sql ); // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared
        if ( false === $result ) {
            return new WP_Error( 'mgs_oq_counter_increment', 'Não foi possível incrementar o contador diário.' );
        }
        $views_today = (int) $wpdb->get_var( 'SELECT LAST_INSERT_ID()' ); // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared
        if ( $views_today < 1 ) {
            return new WP_Error( 'mgs_oq_counter_readback', 'O contador diário não retornou um valor válido.' );
        }
        return array(
            'date'          => $date,
            'timezone'      => self::COUNTER_TIMEZONE,
            'views_today'   => $views_today,
            'display_count' => self::COUNTER_BASELINE + $views_today - 1,
        );
    }

    public static function register_rest_routes() {
        register_rest_route(
            'mgs-offer-quiz/v1',
            '/daily-view',
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( __CLASS__, 'rest_increment_daily_counter' ),
                'permission_callback' => '__return_true',
                'args'                => array(
                    'slug' => array(
                        'required'          => true,
                        'sanitize_callback' => 'sanitize_title',
                    ),
                ),
            )
        );
    }

    public static function rest_increment_daily_counter( $request ) {
        $slug = sanitize_title( (string) $request->get_param( 'slug' ) );
        if ( ! self::find_by_slug( $slug ) ) {
            return new WP_Error( 'mgs_oq_counter_slug', 'Quiz inválida.', array( 'status' => 400 ) );
        }
        $result = self::increment_daily_counter();
        if ( is_wp_error( $result ) ) {
            $result->add_data( array( 'status' => 500 ) );
            return $result;
        }
        $response = rest_ensure_response( $result );
        $response->header( 'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0' );
        return $response;
    }

    private static function default_items() {
        $items = array();
        $now = current_time( 'mysql', true );
        for ( $number = 1; $number <= 6; $number++ ) {
            $manager = sprintf( 'G%03d', $number );
            $slug = 'quiz-v1-' . strtolower( $manager );
            $items[] = array(
                'id'           => 'superdigital-' . strtolower( $manager ),
                'name'         => 'Superdigital BR — ' . $manager . ' — V1',
                'manager'      => $manager,
                'slug'         => $slug,
                'active'       => 1 === $number ? 1 : 0,
                'logo_url'     => 'https://dicasfinancas.info/wp-content/uploads/2025/05/dicas-logo-1536x508.png',
                'eyebrow'      => 'OFERTAS DE HOJE',
                'headline'     => 'Conheça uma opção digital para cuidar do seu dinheiro',
                'highlight'    => 'SUPERDIGITAL',
                'subheadline'  => 'Veja as características e condições antes de decidir.',
                'benefits'     => array(
                    'Sem consulta SPC/Serasa',
                    'Sem anuidade',
                    'Sem taxa escondida',
                ),
                'button_label' => 'VER OFERTA AGORA',
                'target_url'   => 'https://dicasfinancas.info/rec-br-cc-cartao-de-credito-nubank/',
                'microcopy'    => 'Acesse o conteúdo completo em poucos segundos',
                'disclaimer'   => 'Conteúdo informativo. A disponibilidade, a aprovação e as condições dependem exclusivamente da instituição responsável.',
                'privacy_url'  => 'https://dicasfinancas.info/politica-de-privacidade/',
                'created_at'   => $now,
                'updated_at'   => $now,
            );
        }
        return $items;
    }

    private static function static_route( $item ) {
        $manager = strtoupper( sanitize_key( (string) ( $item['manager'] ?? '' ) ) );
        $slug = sanitize_title( (string) ( $item['slug'] ?? '' ) );
        if ( ! preg_match( '/^G00[1-6]$/', $manager ) || ! preg_match( '/^quiz-v1-g00[1-6]$/', $slug ) ) {
            return new WP_Error( 'mgs_oq_static_route', 'Rota estática inválida.' );
        }
        if ( 'quiz-v1-' . strtolower( $manager ) !== $slug ) {
            return new WP_Error( 'mgs_oq_static_mismatch', 'Gestor e slug não correspondem.' );
        }
        return array(
            'manager' => $manager,
            'slug'    => $slug,
            'dir'     => trailingslashit( ABSPATH ) . 'quiz/' . $slug,
        );
    }

    public static function static_index_path( $item ) {
        $route = self::static_route( $item );
        return is_wp_error( $route ) ? $route : trailingslashit( $route['dir'] ) . 'index.html';
    }

    private static function render_static_html( $item ) {
        $mgs_oq_item = $item;
        $mgs_oq_static_render = true;
        ob_start();
        include MGS_OQ_PATH . 'templates/landing.php';
        $html = (string) ob_get_clean();
        if ( false === stripos( $html, '<!doctype html>' ) ) {
            return new WP_Error( 'mgs_oq_static_render', 'O template não gerou um documento HTML completo.' );
        }
        $config_hash = hash( 'sha256', wp_json_encode( $item, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
        $marker = '<!-- ' . self::STATIC_MARKER . '; plugin=' . MGS_OQ_VERSION . '; config_sha256=' . $config_hash . ' -->';
        return preg_replace( '/(<\!doctype html>)/i', '$1' . "\n" . $marker, $html, 1 );
    }

    public static function publish_static_item( $item ) {
        if ( empty( $item['active'] ) ) {
            return new WP_Error( 'mgs_oq_static_inactive', 'Uma quiz inativa não pode ser publicada.' );
        }
        $index = self::static_index_path( $item );
        if ( is_wp_error( $index ) ) {
            return $index;
        }
        $html = self::render_static_html( $item );
        if ( is_wp_error( $html ) ) {
            return $html;
        }
        $dir = dirname( $index );
        if ( ! is_dir( $dir ) && ! wp_mkdir_p( $dir ) ) {
            return new WP_Error( 'mgs_oq_static_mkdir', 'Não foi possível criar o diretório da quiz.' );
        }
        if ( ! is_writable( $dir ) ) {
            return new WP_Error( 'mgs_oq_static_permissions', 'O diretório da quiz não permite escrita.' );
        }
        $temp = trailingslashit( $dir ) . '.index-' . wp_generate_uuid4() . '.tmp';
        $written = file_put_contents( $temp, $html, LOCK_EX ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents
        if ( false === $written || $written !== strlen( $html ) ) {
            return new WP_Error( 'mgs_oq_static_write', 'Não foi possível gravar o HTML completo.' );
        }
        chmod( $temp, 0644 ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod
        if ( ! rename( $temp, $index ) ) { // phpcs:ignore WordPress.WP.AlternativeFunctions.rename_rename
            return new WP_Error( 'mgs_oq_static_publish', 'Não foi possível publicar o HTML de forma atômica.' );
        }
        clearstatcache( true, $index );
        $readback = file_get_contents( $index ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents
        if ( $readback !== $html || false === strpos( $readback, self::STATIC_MARKER ) ) {
            return new WP_Error( 'mgs_oq_static_readback', 'O readback não corresponde ao HTML gerado.' );
        }
        return array(
            'manager' => (string) $item['manager'],
            'slug'    => (string) $item['slug'],
            'path'    => $index,
            'bytes'   => strlen( $html ),
            'sha256'  => hash( 'sha256', $html ),
        );
    }

    public static function unpublish_static_item( $item ) {
        $route = self::static_route( $item );
        if ( is_wp_error( $route ) ) {
            return $route;
        }
        $dir = $route['dir'];
        $index = trailingslashit( $dir ) . 'index.html';
        if ( ! is_dir( $dir ) ) {
            return true;
        }
        if ( ! is_file( $index ) ) {
            return new WP_Error( 'mgs_oq_foreign_dir', 'A rota existe, mas não contém o index.html esperado.' );
        }
        $head = file_get_contents( $index, false, null, 0, 512 ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents
        if ( false === $head || false === strpos( $head, self::STATIC_MARKER ) ) {
            return new WP_Error( 'mgs_oq_foreign_index', 'A rota contém um index.html que não pertence ao plugin.' );
        }
        $archive = dirname( $dir ) . '/.' . basename( $dir ) . '.mgs-disabled-' . gmdate( 'YmdHis' ) . '-' . substr( wp_generate_uuid4(), 0, 8 );
        if ( ! rename( $dir, $archive ) ) { // phpcs:ignore WordPress.WP.AlternativeFunctions.rename_rename
            return new WP_Error( 'mgs_oq_unpublish', 'Não foi possível arquivar a rota estática.' );
        }
        return array( 'archived_path' => $archive );
    }

    public static function sync_static_pages() {
        $published = array();
        foreach ( self::items() as $item ) {
            if ( empty( $item['active'] ) ) {
                continue;
            }
            $result = self::publish_static_item( $item );
            if ( is_wp_error( $result ) ) {
                return $result;
            }
            $published[] = $result;
        }
        update_option( self::STATIC_VERSION_OPTION, MGS_OQ_VERSION, false );
        return $published;
    }

    public static function maybe_sync_static_pages() {
        if ( get_option( self::STATIC_VERSION_OPTION, '' ) !== MGS_OQ_VERSION ) {
            self::sync_static_pages();
        }
    }

    public static function unpublish_all_static() {
        $archived = array();
        foreach ( self::items() as $item ) {
            if ( empty( $item['active'] ) ) {
                continue;
            }
            $result = self::unpublish_static_item( $item );
            if ( is_wp_error( $result ) ) {
                return $result;
            }
            $archived[] = $result;
        }
        return $archived;
    }

    public static function find_by_id( $id ) {
        foreach ( self::items() as $item ) {
            if ( isset( $item['id'] ) && hash_equals( (string) $item['id'], (string) $id ) ) {
                return $item;
            }
        }
        return null;
    }

    public static function find_by_slug( $slug ) {
        foreach ( self::items() as $item ) {
            if ( ! empty( $item['active'] ) && (string) ( $item['slug'] ?? '' ) === $slug ) {
                return $item;
            }
        }
        return null;
    }

    public static function maybe_render() {
        $slug = sanitize_title( (string) get_query_var( 'mgs_oq_slug' ) );
        if ( ! $slug ) {
            return;
        }
        $item = self::find_by_slug( $slug );
        if ( ! $item ) {
            global $wp_query;
            if ( is_object( $wp_query ) && method_exists( $wp_query, 'set_404' ) ) {
                $wp_query->set_404();
            }
            status_header( 404 );
            nocache_headers();
            $template = get_404_template();
            if ( $template ) {
                include $template;
            }
            exit;
        }
        status_header( 200 );
        if ( ! headers_sent() ) {
            header( 'X-Robots-Tag: noindex, follow', true );
        }
        $mgs_oq_item = $item;
        include MGS_OQ_PATH . 'templates/landing.php';
        exit;
    }

    private static function https_url( $value, $required = false ) {
        $url = esc_url_raw( trim( (string) $value ) );
        if ( ! $url ) {
            return $required ? false : '';
        }
        $parts = wp_parse_url( $url );
        return is_array( $parts ) && 'https' === strtolower( (string) ( $parts['scheme'] ?? '' ) ) && ! empty( $parts['host'] ) ? $url : false;
    }

    private static function fail( $id, $code ) {
        $args = array( 'page' => 'mgs-offer-quiz-edit', 'error' => $code );
        if ( $id ) {
            $args['id'] = $id;
        }
        wp_safe_redirect( add_query_arg( $args, admin_url( 'admin.php' ) ) );
        exit;
    }

    public static function handle_save() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Sem permissão.' );
        }
        check_admin_referer( 'mgs_oq_save' );
        $id = sanitize_text_field( wp_unslash( $_POST['id'] ?? '' ) );
        $manager = strtoupper( sanitize_key( wp_unslash( $_POST['manager'] ?? '' ) ) );
        $slug = sanitize_title( wp_unslash( $_POST['slug'] ?? '' ) );
        if ( ! preg_match( '/^G00[1-6]$/', $manager ) || ! preg_match( '/^quiz-v1-g00[1-6]$/', $slug ) || 'quiz-v1-' . strtolower( $manager ) !== $slug ) {
            self::fail( $id, 'route' );
        }
        $target = self::https_url( wp_unslash( $_POST['target_url'] ?? '' ), true );
        $logo = self::https_url( wp_unslash( $_POST['logo_url'] ?? '' ) );
        $privacy = self::https_url( wp_unslash( $_POST['privacy_url'] ?? '' ) );
        if ( false === $target || false === $logo || false === $privacy ) {
            self::fail( $id, 'url' );
        }
        $items = self::items();
        $existing = null;
        $index = null;
        foreach ( $items as $position => $item ) {
            if ( (string) ( $item['id'] ?? '' ) === $id ) {
                $existing = $item;
                $index = $position;
                continue;
            }
            if ( (string) ( $item['slug'] ?? '' ) === $slug ) {
                self::fail( $id, 'duplicate' );
            }
        }
        if ( ! $id ) {
            $id = wp_generate_uuid4();
        }
        $now = current_time( 'mysql', true );
        $data = array(
            'id'           => $id,
            'name'         => sanitize_text_field( wp_unslash( $_POST['name'] ?? '' ) ),
            'manager'      => $manager,
            'slug'         => $slug,
            'active'       => empty( $_POST['active'] ) ? 0 : 1,
            'logo_url'     => $logo,
            'eyebrow'      => sanitize_text_field( wp_unslash( $_POST['eyebrow'] ?? '' ) ),
            'headline'     => sanitize_text_field( wp_unslash( $_POST['headline'] ?? '' ) ),
            'highlight'    => sanitize_text_field( wp_unslash( $_POST['highlight'] ?? '' ) ),
            'subheadline'  => sanitize_text_field( wp_unslash( $_POST['subheadline'] ?? '' ) ),
            'benefits'     => array(
                sanitize_text_field( wp_unslash( $_POST['benefit_1'] ?? '' ) ),
                sanitize_text_field( wp_unslash( $_POST['benefit_2'] ?? '' ) ),
                sanitize_text_field( wp_unslash( $_POST['benefit_3'] ?? '' ) ),
            ),
            'button_label' => sanitize_text_field( wp_unslash( $_POST['button_label'] ?? '' ) ),
            'target_url'   => $target,
            'microcopy'    => sanitize_text_field( wp_unslash( $_POST['microcopy'] ?? '' ) ),
            'disclaimer'   => sanitize_textarea_field( wp_unslash( $_POST['disclaimer'] ?? '' ) ),
            'privacy_url'  => $privacy,
            'created_at'   => $existing['created_at'] ?? $now,
            'updated_at'   => $now,
        );
        if ( $existing && ! empty( $existing['active'] ) && ! empty( $data['active'] ) && (string) $existing['slug'] !== $slug ) {
            self::fail( $id, 'deactivate_first' );
        }
        $before = $items;
        if ( null === $index ) {
            $items[] = $data;
        } else {
            $items[ $index ] = $data;
        }
        self::save_items( $items );
        $result = true;
        if ( $existing && ! empty( $existing['active'] ) && empty( $data['active'] ) ) {
            $result = self::unpublish_static_item( $existing );
        } elseif ( ! empty( $data['active'] ) ) {
            $result = self::publish_static_item( $data );
        }
        if ( is_wp_error( $result ) ) {
            self::save_items( $before );
            if ( $existing && ! empty( $existing['active'] ) ) {
                self::publish_static_item( $existing );
            }
            self::fail( $id, 'static' );
        }
        update_option( self::STATIC_VERSION_OPTION, MGS_OQ_VERSION, false );
        wp_safe_redirect( add_query_arg( array( 'page' => 'mgs-offer-quiz-edit', 'id' => $id, 'saved' => 1 ), admin_url( 'admin.php' ) ) );
        exit;
    }

    public static function handle_duplicate() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Sem permissão.' );
        }
        $id = sanitize_text_field( wp_unslash( $_GET['id'] ?? '' ) );
        check_admin_referer( 'mgs_oq_duplicate_' . $id );
        $source = self::find_by_id( $id );
        if ( ! $source ) {
            wp_die( 'Quiz não encontrada.' );
        }
        $copy = $source;
        $copy['id'] = wp_generate_uuid4();
        $copy['name'] = trim( (string) $source['name'] ) . ' — cópia';
        $copy['manager'] = '';
        $copy['slug'] = '';
        $copy['active'] = 0;
        $copy['created_at'] = current_time( 'mysql', true );
        $copy['updated_at'] = $copy['created_at'];
        $items = self::items();
        $items[] = $copy;
        self::save_items( $items );
        wp_safe_redirect( add_query_arg( array( 'page' => 'mgs-offer-quiz-edit', 'id' => $copy['id'], 'duplicated' => 1 ), admin_url( 'admin.php' ) ) );
        exit;
    }

    private static function field( $item, $key, $default = '' ) {
        return isset( $item[ $key ] ) ? $item[ $key ] : $default;
    }

    public static function admin_menu() {
        add_menu_page( 'Quiz de Ofertas', 'Quiz de Ofertas', 'manage_options', 'mgs-offer-quiz', array( __CLASS__, 'render_list' ), 'dashicons-forms', 31 );
        add_submenu_page( 'mgs-offer-quiz', 'Todas as quizzes', 'Todas as quizzes', 'manage_options', 'mgs-offer-quiz', array( __CLASS__, 'render_list' ) );
        add_submenu_page( 'mgs-offer-quiz', 'Nova quiz', 'Nova quiz', 'manage_options', 'mgs-offer-quiz-edit', array( __CLASS__, 'render_edit' ) );
    }

    public static function render_list() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        $items = self::items();
        ?>
        <div class="wrap"><h1 class="wp-heading-inline">Quiz de Ofertas</h1> <a class="page-title-action" href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-offer-quiz-edit' ) ); ?>">Nova quiz</a><hr class="wp-header-end">
        <p>Páginas estáticas por gestor, sem formulário ou captação. Os parâmetros recebidos são preservados no CTA.</p>
        <table class="widefat striped"><thead><tr><th>Nome</th><th>Gestor</th><th>Rota</th><th>Status</th><th>Ações</th></tr></thead><tbody>
        <?php foreach ( $items as $item ) :
            $id = (string) ( $item['id'] ?? '' );
            $url = ! empty( $item['slug'] ) ? home_url( '/quiz/' . $item['slug'] . '/' ) : '';
            $duplicate = wp_nonce_url( admin_url( 'admin-post.php?action=mgs_oq_duplicate&id=' . rawurlencode( $id ) ), 'mgs_oq_duplicate_' . $id );
        ?>
          <tr><td><strong><?php echo esc_html( self::field( $item, 'name', 'Sem nome' ) ); ?></strong></td><td><?php echo esc_html( self::field( $item, 'manager', 'Pendente' ) ); ?></td><td><?php if ( $url ) : ?><a href="<?php echo esc_url( $url ); ?>" target="_blank" rel="noopener"><?php echo esc_html( wp_parse_url( $url, PHP_URL_PATH ) ); ?></a><?php else : ?>Pendente<?php endif; ?></td><td><?php echo empty( $item['active'] ) ? 'Inativa' : 'Ativa'; ?></td><td><a href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-offer-quiz-edit&id=' . rawurlencode( $id ) ) ); ?>">Editar</a> | <a href="<?php echo esc_url( $duplicate ); ?>">Duplicar</a></td></tr>
        <?php endforeach; ?>
        </tbody></table></div>
        <?php
    }

    public static function render_edit() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        $id = sanitize_text_field( wp_unslash( $_GET['id'] ?? '' ) );
        $item = $id ? self::find_by_id( $id ) : null;
        $item = $item ?: array(
            'id' => '', 'name' => '', 'manager' => '', 'slug' => '', 'active' => 0,
            'logo_url' => 'https://dicasfinancas.info/wp-content/uploads/2025/05/dicas-logo-1536x508.png',
            'eyebrow' => 'OFERTAS DE HOJE', 'headline' => 'Conheça uma opção digital para cuidar do seu dinheiro',
            'highlight' => 'SUPERDIGITAL', 'subheadline' => 'Veja as características e condições antes de decidir.',
            'benefits' => array( 'Controle pelo aplicativo', 'Cartão para compras do dia a dia', 'Conteúdo gratuito e sem cadastro' ),
            'button_label' => 'VER OFERTA AGORA',
            'target_url' => 'https://dicasfinancas.info/rec-br-cc-cartao-de-credito-nubank/',
            'microcopy' => 'Acesse o conteúdo completo em poucos segundos',
            'disclaimer' => 'Conteúdo informativo. A disponibilidade, a aprovação e as condições dependem exclusivamente da instituição responsável.',
            'privacy_url' => 'https://dicasfinancas.info/politica-de-privacidade/',
        );
        $benefits = array_values( (array) self::field( $item, 'benefits', array() ) );
        ?>
        <div class="wrap"><h1><?php echo $id ? 'Editar quiz' : 'Nova quiz'; ?></h1>
        <?php if ( isset( $_GET['saved'] ) ) : ?><div class="notice notice-success"><p>Quiz salva e index.html validado.</p></div><?php endif; ?>
        <?php if ( isset( $_GET['duplicated'] ) ) : ?><div class="notice notice-info"><p>Cópia criada inativa. Defina gestor e slug antes de ativar.</p></div><?php endif; ?>
        <?php if ( isset( $_GET['error'] ) ) : ?><div class="notice notice-error"><p>Não foi possível salvar. Revise gestor, slug, URLs e estado da rota.</p></div><?php endif; ?>
        <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
          <input type="hidden" name="action" value="mgs_oq_save"><input type="hidden" name="id" value="<?php echo esc_attr( self::field( $item, 'id' ) ); ?>"><?php wp_nonce_field( 'mgs_oq_save' ); ?>
          <table class="form-table" role="presentation"><tbody>
            <tr><th><label for="oq-name">Nome interno</label></th><td><input class="regular-text" id="oq-name" name="name" required value="<?php echo esc_attr( self::field( $item, 'name' ) ); ?>"></td></tr>
            <tr><th><label for="oq-manager">Gestor</label></th><td><input id="oq-manager" name="manager" required pattern="G00[1-6]" value="<?php echo esc_attr( self::field( $item, 'manager' ) ); ?>"><p class="description">G001 a G006.</p></td></tr>
            <tr><th><label for="oq-slug">Slug</label></th><td><input class="regular-text" id="oq-slug" name="slug" required pattern="quiz-v1-g00[1-6]" value="<?php echo esc_attr( self::field( $item, 'slug' ) ); ?>"><p class="description">Ex.: quiz-v1-g001.</p></td></tr>
            <tr><th><label for="oq-logo">Logo</label></th><td><input class="large-text" type="url" id="oq-logo" name="logo_url" value="<?php echo esc_attr( self::field( $item, 'logo_url' ) ); ?>"></td></tr>
            <tr><th><label for="oq-eyebrow">Chamada superior</label></th><td><input class="regular-text" id="oq-eyebrow" name="eyebrow" value="<?php echo esc_attr( self::field( $item, 'eyebrow' ) ); ?>"></td></tr>
            <tr><th><label for="oq-headline">Título</label></th><td><input class="large-text" id="oq-headline" name="headline" required value="<?php echo esc_attr( self::field( $item, 'headline' ) ); ?>"></td></tr>
            <tr><th><label for="oq-highlight">Destaque</label></th><td><input class="regular-text" id="oq-highlight" name="highlight" required value="<?php echo esc_attr( self::field( $item, 'highlight' ) ); ?>"></td></tr>
            <tr><th><label for="oq-subheadline">Subtítulo</label></th><td><input class="large-text" id="oq-subheadline" name="subheadline" value="<?php echo esc_attr( self::field( $item, 'subheadline' ) ); ?>"></td></tr>
            <?php for ( $i = 0; $i < 3; $i++ ) : ?><tr><th><label for="oq-benefit-<?php echo esc_attr( $i + 1 ); ?>">Benefício <?php echo esc_html( $i + 1 ); ?></label></th><td><input class="large-text" id="oq-benefit-<?php echo esc_attr( $i + 1 ); ?>" name="benefit_<?php echo esc_attr( $i + 1 ); ?>" required value="<?php echo esc_attr( $benefits[ $i ] ?? '' ); ?>"></td></tr><?php endfor; ?>
            <tr><th><label for="oq-button">Botão</label></th><td><input class="regular-text" id="oq-button" name="button_label" required value="<?php echo esc_attr( self::field( $item, 'button_label' ) ); ?>"></td></tr>
            <tr><th><label for="oq-target">URL de destino</label></th><td><input class="large-text" type="url" id="oq-target" name="target_url" required value="<?php echo esc_attr( self::field( $item, 'target_url' ) ); ?>"></td></tr>
            <tr><th><label for="oq-micro">Microtexto</label></th><td><input class="large-text" id="oq-micro" name="microcopy" value="<?php echo esc_attr( self::field( $item, 'microcopy' ) ); ?>"></td></tr>
            <tr><th><label for="oq-disclaimer">Disclaimer</label></th><td><textarea class="large-text" rows="4" id="oq-disclaimer" name="disclaimer"><?php echo esc_textarea( self::field( $item, 'disclaimer' ) ); ?></textarea></td></tr>
            <tr><th><label for="oq-privacy">Política de privacidade</label></th><td><input class="large-text" type="url" id="oq-privacy" name="privacy_url" value="<?php echo esc_attr( self::field( $item, 'privacy_url' ) ); ?>"></td></tr>
            <tr><th>Publicação</th><td><label><input type="checkbox" name="active" value="1" <?php checked( ! empty( $item['active'] ) ); ?>> Ativa</label></td></tr>
          </tbody></table>
          <?php submit_button( $id ? 'Salvar alterações' : 'Criar quiz' ); ?>
        </form></div>
        <?php
    }
}
