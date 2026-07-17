<?php
/**
 * Cria/atualiza as tabelas no ativar do plugin.
 *
 * Mapeamento das tabelas Supabase -> WP:
 *   public.quiz_config -> {prefix}_mgs_quiz_config
 *   public.quiz_leads  -> {prefix}_mgs_quiz_leads
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

class MGS_Quiz_Activator {

    public static function activate() {
        global $wpdb;
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        $charset = $wpdb->get_charset_collate();

        $cfg     = $wpdb->prefix . 'mgs_quiz_config';
        $leads   = $wpdb->prefix . 'mgs_quiz_leads';
        $revenue = $wpdb->prefix . 'mgs_quiz_sms_revenue';

        // quiz_config: identica em colunas relevantes ao schema Supabase original.
        $sql_cfg = "CREATE TABLE {$cfg} (
            id              CHAR(36)        NOT NULL,
            slug            VARCHAR(190)    NOT NULL,
            name            VARCHAR(190)    NULL,
            layout_template VARCHAR(32)     NULL,
            title           TEXT            NULL,
            subtitle        TEXT            NULL,
            question        TEXT            NULL,
            options         LONGTEXT        NULL,
            form_title      VARCHAR(255)    NULL,
            form_name_label VARCHAR(120)    NULL,
            form_phone_label VARCHAR(120)   NULL,
            form_phone_mask VARCHAR(64)     NULL,
            form_submit_label VARCHAR(120)  NULL,
            success_title   VARCHAR(255)    NULL,
            success_message TEXT            NULL,
            primary_color   VARCHAR(16)     NULL,
            redirect_url    TEXT            NULL,
            redirect_delay_ms INT           NULL DEFAULT 1800,
            redirect_variants LONGTEXT      NULL,
            redirect_url_weight INT         NULL DEFAULT 0,
            meta_pixel_id   VARCHAR(32)     NULL,
            gtm_id          VARCHAR(32)     NULL,
            logo_url        TEXT            NULL,
            car_image_url   TEXT            NULL,
            flag_image_url  TEXT            NULL,
            footer_html     LONGTEXT        NULL,
            privacy_url     TEXT            NULL,
            terms_url       TEXT            NULL,
            seo_title       VARCHAR(255)    NULL,
            seo_description TEXT            NULL,
            sms_funnel_url  TEXT            NULL,
            sms_funnel_urls LONGTEXT        NULL,
            require_sms_success TINYINT(1)  NOT NULL DEFAULT 1,
            updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_slug (slug)
        ) {$charset};";

        // quiz_leads: campos preservados + utm e fbclid/gclid serializados em extra_params.
        $sql_leads = "CREATE TABLE {$leads} (
            id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            quiz_slug       VARCHAR(190)    NOT NULL,
            quiz_config_id  CHAR(36)        NULL,
            name            VARCHAR(200)    NOT NULL,
            phone           VARCHAR(32)     NOT NULL,
            parcela         VARCHAR(120)    NULL,
            utm_source      VARCHAR(190)    NULL,
            utm_medium      VARCHAR(190)    NULL,
            utm_campaign    VARCHAR(190)    NULL,
            utm_term        VARCHAR(190)    NULL,
            utm_content     VARCHAR(190)    NULL,
            fbclid          VARCHAR(255)    NULL,
            gclid           VARCHAR(255)    NULL,
            extra_params    LONGTEXT        NULL,
            ip              VARCHAR(64)     NULL,
            user_agent      TEXT            NULL,
            sms_funnel_status VARCHAR(32)   NULL,
            sms_funnel_response TEXT        NULL,
            PRIMARY KEY (id),
            KEY idx_slug (quiz_slug),
            KEY idx_phone (phone),
            KEY idx_created (created_at)
        ) {$charset};";

        // Receita histórica do relatório SMS da Smart Bidding, agregada por dia/campanha.
        $sql_revenue = "CREATE TABLE {$revenue} (
            id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            revenue_date        DATE            NOT NULL,
            publisher           VARCHAR(190)    NOT NULL,
            domain              VARCHAR(190)    NOT NULL,
            utm_campaign        VARCHAR(190)    NOT NULL DEFAULT '',
            currency            CHAR(3)         NOT NULL DEFAULT 'BRL',
            discount_revenue_share TINYINT(1)  NOT NULL DEFAULT 1,
            revenue_cents       BIGINT          NOT NULL DEFAULT 0,
            net_revenue_cents   BIGINT          NOT NULL DEFAULT 0,
            investment_cents    BIGINT          NOT NULL DEFAULT 0,
            source_rows         INT UNSIGNED    NOT NULL DEFAULT 0,
            source_hash         CHAR(64)        NOT NULL,
            synced_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_date_publisher_campaign (revenue_date, publisher, utm_campaign),
            KEY idx_revenue_date (revenue_date),
            KEY idx_revenue_domain (domain)
        ) {$charset};";

        dbDelta( $sql_cfg );
        dbDelta( $sql_leads );
        dbDelta( $sql_revenue );

        update_option( 'mgs_quiz_db_version', MGS_QUIZ_DB_VERSION );

        // Garante rewrite rules ativas.
        MGS_Quiz_Rewrite::register();
        flush_rewrite_rules();
    }

    public static function deactivate() {
        flush_rewrite_rules();
    }
}
