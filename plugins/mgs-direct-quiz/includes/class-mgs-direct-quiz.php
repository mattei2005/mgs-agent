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
        add_action( 'admin_enqueue_scripts', array( __CLASS__, 'admin_assets' ) );
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
            '^quiz/([a-z]{2})/(sh[12]-g[0-9]{3,})/?$',
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
            'Landing Pages SHEIN',
            'Landing SHEIN',
            'manage_options',
            'mgs-direct-quiz',
            array( __CLASS__, 'render_list' ),
            'dashicons-store',
            31
        );
        add_submenu_page(
            'mgs-direct-quiz',
            'Landing Pages SHEIN',
            'Todas as landings',
            'manage_options',
            'mgs-direct-quiz',
            array( __CLASS__, 'render_list' )
        );
        add_submenu_page(
            'mgs-direct-quiz',
            'Nova landing SHEIN',
            'Nova landing',
            'manage_options',
            'mgs-direct-quiz-edit',
            array( __CLASS__, 'render_edit' )
        );
    }

    public static function admin_assets() {
        $page = sanitize_key( wp_unslash( $_GET['page'] ?? '' ) );
        if ( ! in_array( $page, array( 'mgs-direct-quiz', 'mgs-direct-quiz-edit' ), true ) ) {
            return;
        }
        wp_enqueue_media();
        wp_enqueue_style( 'mgs-dq-admin', MGS_DQ_URL . 'assets/admin.css', array(), MGS_DQ_VERSION );
        wp_enqueue_script( 'mgs-dq-admin', MGS_DQ_URL . 'assets/admin.js', array(), MGS_DQ_VERSION, true );
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
        if ( ! in_array( $layout, array( 'lp1', 'lp2' ), true ) ) {
            self::admin_fail( $id, 'layout' );
        }
        $expected_slug = 'sh' . substr( $layout, 2 ) . '-' . strtolower( $manager );
        if ( ! preg_match( '/^sh[12]-g[0-9]{3,}$/', $slug ) || $expected_slug !== $slug ) {
            self::admin_fail( $id, 'slug' );
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
        $items        = self::items();
        $active_count = count( array_filter( $items, static function ( $item ) { return ! empty( $item['active'] ); } ) );
        $models       = array_unique( array_filter( array_map( static function ( $item ) { return $item['layout_template'] ?? ''; }, $items ) ) );
        ?>
        <div class="wrap mgs-dq-admin">
          <section class="mgs-dq-hero">
            <div class="mgs-dq-hero-icon"><span class="dashicons dashicons-store"></span></div>
            <div class="mgs-dq-hero-copy">
              <span class="mgs-dq-eyebrow">Tráfego direto</span>
              <h1>Landing Pages SHEIN</h1>
              <p>Crie e duplique páginas por gestor. Sem lead, SMS ou configuração de campanhas.</p>
            </div>
            <a class="mgs-dq-button mgs-dq-button-primary" href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-direct-quiz-edit' ) ); ?>"><span class="dashicons dashicons-plus-alt2"></span> Nova landing</a>
          </section>

          <section class="mgs-dq-stats" aria-label="Resumo das landings">
            <article class="mgs-dq-stat"><span class="mgs-dq-stat-icon mgs-dq-stat-icon-purple"><span class="dashicons dashicons-admin-page"></span></span><div><strong><?php echo esc_html( count( $items ) ); ?></strong><span>Total de landings</span></div></article>
            <article class="mgs-dq-stat"><span class="mgs-dq-stat-icon mgs-dq-stat-icon-green"><span class="dashicons dashicons-yes-alt"></span></span><div><strong><?php echo esc_html( $active_count ); ?></strong><span>Landings ativas</span></div></article>
            <article class="mgs-dq-stat"><span class="mgs-dq-stat-icon mgs-dq-stat-icon-blue"><span class="dashicons dashicons-layout"></span></span><div><strong><?php echo esc_html( count( $models ) ); ?></strong><span>Modelos em uso</span></div></article>
          </section>

          <section class="mgs-dq-panel">
            <header class="mgs-dq-panel-header">
              <div><h2>Suas landings</h2><p>Gerencie o visual, os destinos e a publicação de cada gestor.</p></div>
            </header>
            <?php if ( ! $items ) : ?>
              <div class="mgs-dq-empty"><span class="dashicons dashicons-admin-page"></span><h3>Nenhuma landing criada</h3><p>Comece com uma landing e depois duplique para os outros gestores.</p><a class="mgs-dq-button mgs-dq-button-primary" href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-direct-quiz-edit' ) ); ?>">Criar primeira landing</a></div>
            <?php else : ?>
              <div class="mgs-dq-table-wrap">
                <table class="mgs-dq-table">
                  <thead><tr><th>Landing</th><th>Gestor</th><th>Modelo</th><th>Status</th><th class="mgs-dq-actions-col">Ações</th></tr></thead>
                  <tbody>
                  <?php foreach ( $items as $item ) :
                      $id      = (string) ( $item['id'] ?? '' );
                      $url     = ( ! empty( $item['country'] ) && ! empty( $item['slug'] ) ) ? home_url( '/quiz/' . $item['country'] . '/' . $item['slug'] . '/' ) : '';
                      $dup     = wp_nonce_url( admin_url( 'admin-post.php?action=mgs_dq_duplicate&id=' . rawurlencode( $id ) ), 'mgs_dq_duplicate_' . $id );
                      $active  = ! empty( $item['active'] );
                      $manager = self::field( $item, 'manager_code', '' );
                      $model = 'V' . substr( self::field( $item, 'layout_template', 'lp1' ), 2 );
                  ?>
                    <tr>
                      <td>
                        <div class="mgs-dq-landing-cell"><span class="mgs-dq-landing-icon"><span class="dashicons dashicons-admin-page"></span></span><div><strong><?php echo esc_html( self::field( $item, 'name', 'Sem nome' ) ); ?></strong><?php if ( $url ) : ?><a href="<?php echo esc_url( $url ); ?>" target="_blank" rel="noopener"><span><?php echo esc_html( wp_parse_url( $url, PHP_URL_PATH ) ); ?></span><span class="dashicons dashicons-external"></span></a><?php else : ?><span class="mgs-dq-muted">URL pendente</span><?php endif; ?></div></div>
                      </td>
                      <td><span class="mgs-dq-badge mgs-dq-badge-manager"><?php echo esc_html( $manager ?: 'Pendente' ); ?></span></td>
                      <td><span class="mgs-dq-badge mgs-dq-badge-model"><?php echo esc_html( $model ); ?></span></td>
                      <td><span class="mgs-dq-badge <?php echo $active ? 'mgs-dq-badge-active' : 'mgs-dq-badge-inactive'; ?>"><span class="mgs-dq-status-dot"></span><?php echo $active ? 'Ativa' : 'Inativa'; ?></span></td>
                      <td>
                        <div class="mgs-dq-actions">
                          <?php if ( $url && $active ) : ?><a class="mgs-dq-icon-button" href="<?php echo esc_url( $url ); ?>" target="_blank" rel="noopener" aria-label="Visualizar landing" title="Visualizar"><span class="dashicons dashicons-visibility"></span></a><?php endif; ?>
                          <a class="mgs-dq-button mgs-dq-button-secondary" href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-direct-quiz-edit&id=' . rawurlencode( $id ) ) ); ?>"><span class="dashicons dashicons-edit"></span> Editar</a>
                          <a class="mgs-dq-button mgs-dq-button-ghost" href="<?php echo esc_url( $dup ); ?>"><span class="dashicons dashicons-admin-page"></span> Duplicar</a>
                        </div>
                      </td>
                    </tr>
                  <?php endforeach; ?>
                  </tbody>
                </table>
              </div>
            <?php endif; ?>
          </section>
        </div>
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
        $public_url = ( ! empty( $item['country'] ) && ! empty( $item['slug'] ) ) ? home_url( '/quiz/' . $item['country'] . '/' . $item['slug'] . '/' ) : '';
        ?>
        <div class="wrap mgs-dq-admin mgs-dq-admin-edit">
          <section class="mgs-dq-hero mgs-dq-hero-compact">
            <a class="mgs-dq-back" href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-direct-quiz' ) ); ?>"><span class="dashicons dashicons-arrow-left-alt2"></span> Voltar para landings</a>
            <div class="mgs-dq-hero-copy">
              <span class="mgs-dq-eyebrow">Landing SHEIN</span>
              <h1><?php echo $id ? 'Editar landing' : 'Nova landing'; ?></h1>
              <p><?php echo $id ? 'Atualize o visual e o destino desta página.' : 'Configure uma nova página para um gestor.'; ?></p>
            </div>
            <?php if ( $id ) : ?><span class="mgs-dq-badge <?php echo ! empty( $item['active'] ) ? 'mgs-dq-badge-active' : 'mgs-dq-badge-inactive'; ?>"><span class="mgs-dq-status-dot"></span><?php echo ! empty( $item['active'] ) ? 'Ativa' : 'Inativa'; ?></span><?php endif; ?>
          </section>

          <?php if ( isset( $_GET['saved'] ) ) : ?><div class="notice notice-success is-dismissible mgs-dq-notice"><p><strong>Landing salva.</strong> As alterações foram registradas.</p></div><?php endif; ?>
          <?php if ( isset( $_GET['duplicated'] ) ) : ?><div class="notice notice-info mgs-dq-notice"><p><strong>Cópia criada inativa.</strong> Defina o novo gestor e slug antes de ativar.</p></div><?php endif; ?>
          <?php if ( isset( $_GET['error'] ) ) : ?><div class="notice notice-error mgs-dq-notice"><p><strong>Não foi possível salvar.</strong> Revise os campos obrigatórios e as URLs HTTPS.</p></div><?php endif; ?>

          <form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
            <input type="hidden" name="action" value="mgs_dq_save">
            <input type="hidden" name="id" value="<?php echo esc_attr( self::field( $item, 'id' ) ); ?>">
            <?php wp_nonce_field( 'mgs_dq_save' ); ?>

            <div class="mgs-dq-form-grid">
              <main class="mgs-dq-form-main">
                <section class="mgs-dq-form-card">
                  <header><span class="mgs-dq-card-icon"><span class="dashicons dashicons-admin-settings"></span></span><div><h2>Identificação</h2><p>Defina o gestor, a URL e o modelo visual.</p></div></header>
                  <div class="mgs-dq-fields mgs-dq-fields-2">
                    <label class="mgs-dq-field mgs-dq-field-full"><span>Nome interno</span><input id="mgsdq-name" name="name" required value="<?php echo esc_attr( self::field( $item, 'name' ) ); ?>" placeholder="Ex.: SHEIN US — G002"></label>
                    <label class="mgs-dq-field"><span>País</span><input id="mgsdq-country" name="country" required pattern="[a-zA-Z]{2}" maxlength="2" value="<?php echo esc_attr( self::field( $item, 'country', 'us' ) ); ?>" placeholder="us"><small>Código de duas letras.</small></label>
                    <label class="mgs-dq-field"><span>Gestor</span><input id="mgsdq-manager" name="manager_code" required pattern="G[0-9]{3,}" value="<?php echo esc_attr( self::field( $item, 'manager_code' ) ); ?>" placeholder="G002"><small>Use o padrão G + número.</small></label>
                    <label class="mgs-dq-field"><span>Slug</span><div class="mgs-dq-input-prefix"><span>quiz/país/</span><input id="mgsdq-slug" name="slug" required value="<?php echo esc_attr( self::field( $item, 'slug' ) ); ?>" placeholder="sh2-g002 ou sh1-g002"></div><small>O modelo define a slug: V2 usa sh2-g002 e V1 usa sh1-g002.</small></label>
                    <label class="mgs-dq-field"><span>Modelo visual</span><select id="mgsdq-layout" name="layout_template"><option value="lp1" <?php selected( self::field( $item, 'layout_template' ), 'lp1' ); ?>>V1 — Minimal escura</option><option value="lp2" <?php selected( self::field( $item, 'layout_template' ), 'lp2' ); ?>>V2 — Branded verde</option></select><small>Você pode trocar o modelo sem alterar a URL.</small></label>
                  </div>
                </section>

                <section class="mgs-dq-form-card">
                  <header><span class="mgs-dq-card-icon mgs-dq-card-icon-green"><span class="dashicons dashicons-format-image"></span></span><div><h2>Marca e conteúdo</h2><p>Escolha o logo e personalize o texto da landing.</p></div></header>
                  <div class="mgs-dq-logo-picker">
                    <div class="mgs-dq-logo-preview <?php echo self::field( $item, 'logo_url' ) ? 'has-image' : ''; ?>" id="mgs-dq-logo-preview">
                      <?php if ( self::field( $item, 'logo_url' ) ) : ?><img src="<?php echo esc_url( self::field( $item, 'logo_url' ) ); ?>" alt="Logo selecionado"><?php else : ?><span class="dashicons dashicons-format-image"></span><span>Nenhum logo selecionado</span><?php endif; ?>
                    </div>
                    <div class="mgs-dq-logo-controls">
                      <label class="mgs-dq-field"><span>Logo do site</span><input type="url" id="mgsdq-logo" name="logo_url" value="<?php echo esc_attr( self::field( $item, 'logo_url' ) ); ?>" placeholder="https://..."></label>
                      <div class="mgs-dq-inline-actions"><button type="button" class="mgs-dq-button mgs-dq-button-secondary" id="mgs-dq-select-logo"><span class="dashicons dashicons-images-alt2"></span> Escolher na Biblioteca de Mídia</button><button type="button" class="mgs-dq-button mgs-dq-button-ghost" id="mgs-dq-remove-logo" <?php echo self::field( $item, 'logo_url' ) ? '' : 'hidden'; ?>>Remover logo</button></div>
                      <small>Usado no V2. No V1 o logo pode ficar vazio.</small>
                    </div>
                  </div>
                  <div class="mgs-dq-fields">
                    <label class="mgs-dq-field"><span>Título</span><input id="mgsdq-title" name="title" required value="<?php echo esc_attr( self::field( $item, 'title' ) ); ?>"></label>
                    <label class="mgs-dq-field"><span>Pergunta</span><input id="mgsdq-question" name="question" required value="<?php echo esc_attr( self::field( $item, 'question' ) ); ?>"></label>
                    <div class="mgs-dq-fields mgs-dq-fields-2 mgs-dq-option-grid">
                      <label class="mgs-dq-field"><span>Opção 1</span><div class="mgs-dq-option-input"><input class="mgs-dq-icon-input" name="option_a_icon" value="<?php echo esc_attr( self::field( $item, 'option_a_icon' ) ); ?>" placeholder="Ícone"><input name="option_a_text" required value="<?php echo esc_attr( self::field( $item, 'option_a_text', 'Yes' ) ); ?>" placeholder="Texto"></div></label>
                      <label class="mgs-dq-field"><span>Opção 2</span><div class="mgs-dq-option-input"><input class="mgs-dq-icon-input" name="option_b_icon" value="<?php echo esc_attr( self::field( $item, 'option_b_icon' ) ); ?>" placeholder="Ícone"><input name="option_b_text" required value="<?php echo esc_attr( self::field( $item, 'option_b_text', 'No' ) ); ?>" placeholder="Texto"></div></label>
                    </div>
                  </div>
                </section>

                <section class="mgs-dq-form-card">
                  <header><span class="mgs-dq-card-icon mgs-dq-card-icon-blue"><span class="dashicons dashicons-admin-links"></span></span><div><h2>Destinos dos botões</h2><p>Os parâmetros recebidos na landing serão preservados automaticamente.</p></div></header>
                  <div class="mgs-dq-fields">
                    <label class="mgs-dq-field"><span>Destino da opção 1</span><input type="url" id="mgsdq-desta" name="destination_a_url" required value="<?php echo esc_attr( self::field( $item, 'destination_a_url' ) ); ?>" placeholder="https://site.com/artigo/"></label>
                    <label class="mgs-dq-field"><span>Destino da opção 2</span><input type="url" id="mgsdq-destb" name="destination_b_url" value="<?php echo esc_attr( self::field( $item, 'destination_b_url' ) ); ?>" placeholder="Deixe vazio para usar o destino da opção 1"><small>Se ficar vazio, usa automaticamente o mesmo destino da opção 1.</small></label>
                  </div>
                </section>

                <section class="mgs-dq-form-card">
                  <header><span class="mgs-dq-card-icon mgs-dq-card-icon-amber"><span class="dashicons dashicons-privacy"></span></span><div><h2>Links jurídicos</h2><p>Rodapé legal exibido na landing.</p></div></header>
                  <div class="mgs-dq-fields">
                    <label class="mgs-dq-field"><span>Privacy Policy</span><input type="url" name="privacy_url" value="<?php echo esc_attr( self::field( $item, 'privacy_url' ) ); ?>"></label>
                    <label class="mgs-dq-field"><span>Terms of Service</span><input type="url" name="terms_url" value="<?php echo esc_attr( self::field( $item, 'terms_url' ) ); ?>"></label>
                    <label class="mgs-dq-field"><span>Disclaimer</span><input type="url" name="disclaimer_url" value="<?php echo esc_attr( self::field( $item, 'disclaimer_url' ) ); ?>"></label>
                  </div>
                </section>
              </main>

              <aside class="mgs-dq-form-sidebar">
                <section class="mgs-dq-form-card mgs-dq-publish-card">
                  <header><div><h2>Publicação</h2><p>Controle quando a landing fica disponível.</p></div></header>
                  <label class="mgs-dq-toggle-row"><span><strong>Landing ativa</strong><small>Publica a URL para receber tráfego.</small></span><span class="mgs-dq-switch"><input type="checkbox" name="active" value="1" <?php checked( ! empty( $item['active'] ) ); ?>><span></span></span></label>
                  <label class="mgs-dq-toggle-row"><span><strong>Bloquear indexação</strong><small>Aplica noindex e nofollow.</small></span><span class="mgs-dq-switch"><input type="checkbox" name="noindex" value="1" <?php checked( ! empty( $item['noindex'] ) ); ?>><span></span></span></label>
                  <?php if ( $public_url ) : ?><div class="mgs-dq-public-url"><span>URL pública</span><a href="<?php echo esc_url( $public_url ); ?>" target="_blank" rel="noopener"><?php echo esc_html( $public_url ); ?><span class="dashicons dashicons-external"></span></a></div><?php endif; ?>
                  <div class="mgs-dq-save-area"><?php submit_button( $id ? 'Salvar alterações' : 'Criar landing', 'primary mgs-dq-save-button', 'submit', false ); ?><a href="<?php echo esc_url( admin_url( 'admin.php?page=mgs-direct-quiz' ) ); ?>">Cancelar</a></div>
                </section>
                <section class="mgs-dq-help-card"><span class="dashicons dashicons-lightbulb"></span><div><strong>Dica</strong><p>Para outro gestor, salve esta landing e use <b>Duplicar</b> na listagem. A cópia nasce inativa.</p></div></section>
              </aside>
            </div>
          </form>
        </div>
        <?php
    }
}
