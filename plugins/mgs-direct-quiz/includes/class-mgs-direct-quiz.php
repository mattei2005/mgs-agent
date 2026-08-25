<?php
if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

final class MGS_Direct_Quiz {
    const OPTION = 'mgs_direct_quiz_landings';

    public static function boot() {
        add_action( 'init', array( __CLASS__, 'register_rewrite' ) );
        add_filter( 'query_vars', array( __CLASS__, 'query_vars' ) );
        add_action( 'template_redirect', array( __CLASS__, 'maybe_render' ), 0 );
        add_action( 'admin_menu', array( __CLASS__, 'admin_menu' ) );
        add_action( 'admin_post_mgs_dq_save', array( __CLASS__, 'handle_save' ) );
        add_action( 'admin_post_mgs_dq_duplicate', array( __CLASS__, 'handle_duplicate' ) );
    }

    public static function activate() {
        self::register_rewrite();
        flush_rewrite_rules();
    }

    public static function deactivate() {
        flush_rewrite_rules();
    }

    public static function register_rewrite() {
        add_rewrite_rule(
            '^quiz/([a-z]{2})/(quiz-g[0-9]{3,})/?$',
            'index.php?mgs_dq_country=$matches[1]&mgs_dq_slug=$matches[2]',
            'top'
        );
    }

    public static function query_vars( $vars ) {
        $vars[] = 'mgs_dq_country';
        $vars[] = 'mgs_dq_slug';
        return $vars;
    }

    public static function items() {
        $items = get_option( self::OPTION, array() );
        return is_array( $items ) ? array_values( array_filter( $items, 'is_array' ) ) : array();
    }

    public static function save_items( $items ) {
        return update_option( self::OPTION, array_values( $items ), false );
    }

    public static function find_by_id( $id ) {
        foreach ( self::items() as $item ) {
            if ( isset( $item['id'] ) && hash_equals( (string) $item['id'], (string) $id ) ) {
                return $item;
            }
        }
        return null;
    }

    public static function find_by_route( $country, $slug ) {
        foreach ( self::items() as $item ) {
            if ( empty( $item['active'] ) ) {
                continue;
            }
            if ( strtolower( (string) ( $item['country'] ?? '' ) ) === strtolower( $country )
                && (string) ( $item['slug'] ?? '' ) === $slug ) {
                return $item;
            }
        }
        return null;
    }

    public static function maybe_render() {
        $country = sanitize_key( (string) get_query_var( 'mgs_dq_country' ) );
        $slug    = sanitize_title( (string) get_query_var( 'mgs_dq_slug' ) );
        if ( ! $country || ! $slug ) {
            return;
        }

        $item = self::find_by_route( $country, $slug );
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
        if ( ! empty( $item['noindex'] ) && ! headers_sent() ) {
            header( 'X-Robots-Tag: noindex, nofollow', true );
        }
        $mgs_dq_item = $item;
        include MGS_DQ_PATH . 'templates/landing.php';
        exit;
    }

    public static function merge_query_params( $base ) {
        $base = esc_url_raw( $base );
        if ( ! $base ) {
            return '';
        }

        $existing = array();
        $parts    = wp_parse_url( $base );
        if ( ! empty( $parts['query'] ) ) {
            parse_str( $parts['query'], $existing );
        }

        $excluded = array( 'page_id', 'p', 'mgs_dq_country', 'mgs_dq_slug' );
        $add      = array();
        foreach ( $_GET as $key => $value ) {
            $key = sanitize_key( wp_unslash( $key ) );
            if ( ! $key || in_array( $key, $excluded, true ) || array_key_exists( $key, $existing ) || is_array( $value ) ) {
                continue;
            }
            $add[ $key ] = sanitize_text_field( wp_unslash( $value ) );
        }
        return $add ? add_query_arg( $add, $base ) : $base;
    }

    public static function admin_menu() {
        add_menu_page(
            'MGS Landing Quiz',
            'MGS Landing Quiz',
            'manage_options',
            'mgs-direct-quiz',
            array( __CLASS__, 'render_list' ),
            'dashicons-feedback',
            31
        );
        add_submenu_page(
            'mgs-direct-quiz',
            'Landings',
            'Landings',
            'manage_options',
            'mgs-direct-quiz',
            array( __CLASS__, 'render_list' )
        );
        add_submenu_page(
            'mgs-direct-quiz',
            'Nova landing',
            'Nova landing',
            'manage_options',
            'mgs-direct-quiz-edit',
            array( __CLASS__, 'render_edit' )
        );
    }

    private static function admin_fail( $id, $code ) {
        $url = admin_url( 'admin.php?page=mgs-direct-quiz-edit' );
        if ( $id ) {
            $url = add_query_arg( 'id', rawurlencode( $id ), $url );
        }
        wp_safe_redirect( add_query_arg( 'error', rawurlencode( $code ), $url ) );
        exit;
    }

    private static function https_url( $value, $required = false ) {
        $url = esc_url_raw( trim( (string) $value ) );
        if ( ! $url ) {
            return $required ? false : '';
        }
        $parts = wp_parse_url( $url );
        return ( is_array( $parts ) && 'https' === strtolower( (string) ( $parts['scheme'] ?? '' ) ) && ! empty( $parts['host'] ) ) ? $url : false;
    }

    public static function handle_save() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Sem permissão.' );
        }
        check_admin_referer( 'mgs_dq_save' );

        $id      = sanitize_text_field( wp_unslash( $_POST['id'] ?? '' ) );
        $country = strtolower( sanitize_key( wp_unslash( $_POST['country'] ?? '' ) ) );
        $manager = strtoupper( sanitize_text_field( wp_unslash( $_POST['manager_code'] ?? '' ) ) );
        $slug    = sanitize_title( wp_unslash( $_POST['slug'] ?? '' ) );
        $layout  = sanitize_key( wp_unslash( $_POST['layout_template'] ?? 'lp1' ) );

        if ( ! preg_match( '/^[a-z]{2}$/', $country ) ) {
            self::admin_fail( $id, 'country' );
        }
        if ( ! preg_match( '/^G[0-9]{3,}$/', $manager ) ) {
            self::admin_fail( $id, 'manager' );
        }
        if ( ! preg_match( '/^quiz-g[0-9]{3,}$/', $slug ) || 'quiz-' . strtolower( $manager ) !== $slug ) {
            self::admin_fail( $id, 'slug' );
        }
        if ( ! in_array( $layout, array( 'lp1', 'lp2' ), true ) ) {
            self::admin_fail( $id, 'layout' );
        }

        $destination_a = self::https_url( wp_unslash( $_POST['destination_a_url'] ?? '' ), true );
        $destination_b = self::https_url( wp_unslash( $_POST['destination_b_url'] ?? '' ) );
        $logo          = self::https_url( wp_unslash( $_POST['logo_url'] ?? '' ) );
        $privacy      = self::https_url( wp_unslash( $_POST['privacy_url'] ?? '' ) );
        $terms         = self::https_url( wp_unslash( $_POST['terms_url'] ?? '' ) );
        $disclaimer    = self::https_url( wp_unslash( $_POST['disclaimer_url'] ?? '' ) );
        if ( false === $destination_a || false === $destination_b || false === $logo || false === $privacy || false === $terms || false === $disclaimer ) {
            self::admin_fail( $id, 'url' );
        }
        if ( ! $destination_b ) {
            $destination_b = $destination_a;
        }

        $items    = self::items();
        $existing = null;
        $index    = null;
        foreach ( $items as $i => $item ) {
            if ( (string) ( $item['id'] ?? '' ) === $id ) {
                $existing = $item;
                $index    = $i;
                continue;
            }
            if ( strtolower( (string) ( $item['country'] ?? '' ) ) === $country && (string) ( $item['slug'] ?? '' ) === $slug ) {
                self::admin_fail( $id, 'duplicate' );
            }
        }

        if ( ! $id ) {
            $id = wp_generate_uuid4();
        }
        $now  = current_time( 'mysql', true );
        $data = array(
            'id'                => $id,
            'name'              => sanitize_text_field( wp_unslash( $_POST['name'] ?? '' ) ),
            'country'           => $country,
            'manager_code'      => $manager,
            'slug'              => $slug,
            'layout_template'   => $layout,
            'logo_url'          => $logo,
            'title'             => sanitize_text_field( wp_unslash( $_POST['title'] ?? '' ) ),
            'question'          => sanitize_text_field( wp_unslash( $_POST['question'] ?? '' ) ),
            'option_a_text'     => sanitize_text_field( wp_unslash( $_POST['option_a_text'] ?? '' ) ),
            'option_a_icon'     => sanitize_text_field( wp_unslash( $_POST['option_a_icon'] ?? '' ) ),
            'option_b_text'     => sanitize_text_field( wp_unslash( $_POST['option_b_text'] ?? '' ) ),
            'option_b_icon'     => sanitize_text_field( wp_unslash( $_POST['option_b_icon'] ?? '' ) ),
            'destination_a_url' => $destination_a,
            'destination_b_url' => $destination_b,
            'privacy_url'       => $privacy,
            'terms_url'         => $terms,
            'disclaimer_url'    => $disclaimer,
            'noindex'           => empty( $_POST['noindex'] ) ? 0 : 1,
            'active'            => empty( $_POST['active'] ) ? 0 : 1,
            'created_at'        => $existing['created_at'] ?? $now,
            'updated_at'        => $now,
        );

        if ( null === $index ) {
            $items[] = $data;
        } else {
            $items[ $index ] = $data;
        }
        self::save_items( $items );
        wp_safe_redirect( add_query_arg( array( 'page' => 'mgs-direct-quiz-edit', 'id' => rawurlencode( $id ), 'saved' => 1 ), admin_url( 'admin.php' ) ) );
        exit;
    }

    public static function handle_duplicate() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_die( 'Sem permissão.' );
        }
        $id = sanitize_text_field( wp_unslash( $_GET['id'] ?? '' ) );
        check_admin_referer( 'mgs_dq_duplicate_' . $id );
        $source = self::find_by_id( $id );
        if ( ! $source ) {
            wp_die( 'Landing não encontrada.' );
        }

        $copy                 = $source;
        $copy['id']           = wp_generate_uuid4();
        $copy['name']         = trim( (string) ( $source['name'] ?? '' ) ) . ' — cópia';
        $copy['manager_code'] = '';
        $copy['slug']         = '';
        $copy['active']       = 0;
        $copy['created_at']   = current_time( 'mysql', true );
        $copy['updated_at']   = $copy['created_at'];
        $items                = self::items();
        $items[]              = $copy;
        self::save_items( $items );

        wp_safe_redirect( add_query_arg( array( 'page' => 'mgs-direct-quiz-edit', 'id' => rawurlencode( $copy['id'] ), 'duplicated' => 1 ), admin_url( 'admin.php' ) ) );
        exit;
    }

    private static function field( $item, $key, $default = '' ) {
        return isset( $item[ $key ] ) ? $item[ $key ] : $default;
    }

    public static function render_list() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        $items = self::items();
        ?>
        <div class="wrap"><h1 class="wp-heading-inline">MGS Landing Quiz</h1>
        <a class="page-title-action" href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-direct-quiz-edit' ) ); ?>">Nova landing</a>
        <p>Landings simples: sem formulário, sem integrações e sem configuração de campanhas. Os parâmetros recebidos são apenas preservados nos CTAs.</p>
        <table class="widefat striped"><thead><tr><th>Nome</th><th>Gestor</th><th>Modelo</th><th>URL</th><th>Status</th><th>Ações</th></tr></thead><tbody>
        <?php if ( ! $items ) : ?><tr><td colspan="6">Nenhuma landing criada.</td></tr><?php endif; ?>
        <?php foreach ( $items as $item ) :
            $id  = (string) ( $item['id'] ?? '' );
            $url = ( ! empty( $item['country'] ) && ! empty( $item['slug'] ) ) ? home_url( '/quiz/' . $item['country'] . '/' . $item['slug'] . '/' ) : '';
            $dup = wp_nonce_url( admin_url( 'admin-post.php?action=mgs_dq_duplicate&id=' . rawurlencode( $id ) ), 'mgs_dq_duplicate_' . $id );
        ?>
          <tr>
            <td><strong><?php echo esc_html( self::field( $item, 'name', 'Sem nome' ) ); ?></strong></td>
            <td><?php echo esc_html( self::field( $item, 'manager_code', 'Pendente' ) ); ?></td>
            <td><?php echo esc_html( strtoupper( self::field( $item, 'layout_template', 'lp1' ) ) ); ?></td>
            <td><?php if ( $url ) : ?><a href="<?php echo esc_url( $url ); ?>" target="_blank" rel="noopener"><?php echo esc_html( $url ); ?></a><?php else : ?>Pendente<?php endif; ?></td>
            <td><?php echo ! empty( $item['active'] ) ? 'Ativa' : 'Inativa'; ?></td>
            <td><a href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-direct-quiz-edit&id=' . rawurlencode( $id ) ) ); ?>">Editar</a> | <a href="<?php echo esc_url( $dup ); ?>">Duplicar</a></td>
          </tr>
        <?php endforeach; ?>
        </tbody></table></div>
        <?php
    }

    public static function render_edit() {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        $id   = sanitize_text_field( wp_unslash( $_GET['id'] ?? '' ) );
        $item = $id ? self::find_by_id( $id ) : null;
        $item = $item ?: array(
            'id' => '', 'name' => '', 'country' => 'us', 'manager_code' => '', 'slug' => '',
            'layout_template' => 'lp1', 'logo_url' => '',
            'title' => 'Get Free Products Delivered to Your Home',
            'question' => 'Would you like to get free products?',
            'option_a_text' => 'Yes', 'option_a_icon' => '', 'option_b_text' => 'No', 'option_b_icon' => '',
            'destination_a_url' => '', 'destination_b_url' => '',
            'privacy_url' => home_url( '/privacy-policy/' ),
            'terms_url' => home_url( '/terms-of-service/' ),
            'disclaimer_url' => home_url( '/disclaimer/' ),
            'noindex' => 1, 'active' => 0,
        );
        ?>
        <div class="wrap"><h1><?php echo $id ? 'Editar landing' : 'Nova landing'; ?></h1>
        <?php if ( isset( $_GET['saved'] ) ) : ?><div class="notice notice-success"><p>Landing salva.</p></div><?php endif; ?>
        <?php if ( isset( $_GET['duplicated'] ) ) : ?><div class="notice notice-info"><p>Cópia criada inativa. Defina gestor e slug antes de ativar.</p></div><?php endif; ?>
        <?php if ( isset( $_GET['error'] ) ) : ?><div class="notice notice-error"><p>Não foi possível salvar. Revise os campos obrigatórios e URLs HTTPS.</p></div><?php endif; ?>
        <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
          <input type="hidden" name="action" value="mgs_dq_save">
          <input type="hidden" name="id" value="<?php echo esc_attr( self::field( $item, 'id' ) ); ?>">
          <?php wp_nonce_field( 'mgs_dq_save' ); ?>
          <table class="form-table" role="presentation">
            <tr><th><label for="mgsdq-name">Nome interno</label></th><td><input class="regular-text" id="mgsdq-name" name="name" required value="<?php echo esc_attr( self::field( $item, 'name' ) ); ?>"></td></tr>
            <tr><th><label for="mgsdq-country">País</label></th><td><input id="mgsdq-country" name="country" required pattern="[a-zA-Z]{2}" maxlength="2" value="<?php echo esc_attr( self::field( $item, 'country', 'us' ) ); ?>"><p class="description">Ex.: us.</p></td></tr>
            <tr><th><label for="mgsdq-manager">Gestor</label></th><td><input id="mgsdq-manager" name="manager_code" required pattern="G[0-9]{3,}" value="<?php echo esc_attr( self::field( $item, 'manager_code' ) ); ?>"><p class="description">Ex.: G002.</p></td></tr>
            <tr><th><label for="mgsdq-slug">Slug</label></th><td><input class="regular-text" id="mgsdq-slug" name="slug" required value="<?php echo esc_attr( self::field( $item, 'slug' ) ); ?>"><p class="description">Deve corresponder ao gestor: quiz-g002.</p></td></tr>
            <tr><th><label for="mgsdq-layout">Modelo</label></th><td><select id="mgsdq-layout" name="layout_template"><option value="lp1" <?php selected( self::field( $item, 'layout_template' ), 'lp1' ); ?>>LP1 — minimal escura</option><option value="lp2" <?php selected( self::field( $item, 'layout_template' ), 'lp2' ); ?>>LP2 — branded verde</option></select></td></tr>
            <tr><th><label for="mgsdq-logo">Logo HTTPS</label></th><td><input class="large-text" type="url" id="mgsdq-logo" name="logo_url" value="<?php echo esc_attr( self::field( $item, 'logo_url' ) ); ?>"><p class="description">Usada no LP2; pode ficar vazia no LP1.</p></td></tr>
            <tr><th><label for="mgsdq-title">Título</label></th><td><input class="large-text" id="mgsdq-title" name="title" required value="<?php echo esc_attr( self::field( $item, 'title' ) ); ?>"></td></tr>
            <tr><th><label for="mgsdq-question">Pergunta</label></th><td><input class="large-text" id="mgsdq-question" name="question" required value="<?php echo esc_attr( self::field( $item, 'question' ) ); ?>"></td></tr>
            <tr><th>Opção 1</th><td><input name="option_a_icon" style="width:70px" value="<?php echo esc_attr( self::field( $item, 'option_a_icon' ) ); ?>" placeholder="Ícone"><input class="regular-text" name="option_a_text" required value="<?php echo esc_attr( self::field( $item, 'option_a_text', 'Yes' ) ); ?>"></td></tr>
            <tr><th>Opção 2</th><td><input name="option_b_icon" style="width:70px" value="<?php echo esc_attr( self::field( $item, 'option_b_icon' ) ); ?>" placeholder="Ícone"><input class="regular-text" name="option_b_text" required value="<?php echo esc_attr( self::field( $item, 'option_b_text', 'No' ) ); ?>"></td></tr>
            <tr><th><label for="mgsdq-desta">Destino opção 1</label></th><td><input class="large-text" type="url" id="mgsdq-desta" name="destination_a_url" required value="<?php echo esc_attr( self::field( $item, 'destination_a_url' ) ); ?>"></td></tr>
            <tr><th><label for="mgsdq-destb">Destino opção 2</label></th><td><input class="large-text" type="url" id="mgsdq-destb" name="destination_b_url" value="<?php echo esc_attr( self::field( $item, 'destination_b_url' ) ); ?>"><p class="description">Vazio usa o mesmo destino da opção 1.</p></td></tr>
            <tr><th>Links jurídicos</th><td><input class="large-text" type="url" name="privacy_url" value="<?php echo esc_attr( self::field( $item, 'privacy_url' ) ); ?>" placeholder="Privacy Policy"><br><input class="large-text" type="url" name="terms_url" value="<?php echo esc_attr( self::field( $item, 'terms_url' ) ); ?>" placeholder="Terms of Service"><br><input class="large-text" type="url" name="disclaimer_url" value="<?php echo esc_attr( self::field( $item, 'disclaimer_url' ) ); ?>" placeholder="Disclaimer"></td></tr>
            <tr><th>Publicação</th><td><label><input type="checkbox" name="active" value="1" <?php checked( ! empty( $item['active'] ) ); ?>> Ativa</label><br><label><input type="checkbox" name="noindex" value="1" <?php checked( ! empty( $item['noindex'] ) ); ?>> noindex,nofollow</label></td></tr>
          </table>
          <?php submit_button( 'Salvar landing' ); ?>
        </form></div>
        <?php
    }
}
