<?php
/**
 * Importador/exportador CSV.
 *
 *  Exportar leads:
 *    /wp-admin/admin-post.php?action=mgs_quiz_export_leads&slug=... (com nonce)
 *
 *  Importar configs:
 *    multipart POST com action=mgs_quiz_import_config + arquivo "csv".
 *    Espera o mesmo cabeçalho do quiz_config.csv exportado.
 *    Faz upsert pela coluna "slug".
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

class MGS_Quiz_CSV {

    const BUSINESS_TIMEZONE = 'America/Sao_Paulo';

    private static function business_timezone() {
        return new DateTimeZone( self::BUSINESS_TIMEZONE );
    }

    private static function local_date_bound_to_utc( $date, $next_day = false ) {
        $date = trim( (string) $date );
        if ( ! preg_match( '/^\d{4}-\d{2}-\d{2}$/', $date ) ) return '';
        $local = DateTimeImmutable::createFromFormat( '!Y-m-d', $date, self::business_timezone() );
        $errors = DateTimeImmutable::getLastErrors();
        if ( ! $local || ( is_array( $errors ) && ( $errors['warning_count'] || $errors['error_count'] ) ) ) return '';
        if ( $next_day ) $local = $local->modify( '+1 day' );
        return $local->setTimezone( new DateTimeZone( 'UTC' ) )->format( 'Y-m-d H:i:s' );
    }

    private static function format_created_at( $created_at ) {
        try {
            $utc = new DateTimeImmutable( (string) $created_at, new DateTimeZone( 'UTC' ) );
            return wp_date( 'Y-m-d H:i:s', $utc->getTimestamp(), self::business_timezone() );
        } catch ( Exception $e ) {
            return (string) $created_at;
        }
    }

    /* ---------------- Export leads ---------------- */

    public static function export_leads() {
        if ( ! current_user_can( 'manage_options' ) ) wp_die( 'forbidden' );
        check_admin_referer( 'mgs_quiz_export' );

        global $wpdb;
        $t    = $wpdb->prefix . 'mgs_quiz_leads';
        $slug = isset( $_GET['slug'] ) ? sanitize_title( $_GET['slug'] ) : '';
        $from = isset( $_GET['from'] ) ? sanitize_text_field( $_GET['from'] ) : '';
        $to   = isset( $_GET['to'] )   ? sanitize_text_field( $_GET['to'] )   : '';

        $where  = ' WHERE 1=1 ';
        $params = array();
        if ( $slug ) { $where .= ' AND quiz_slug = %s ';   $params[] = $slug; }
        if ( $from ) {
            $from_utc = self::local_date_bound_to_utc( $from );
            if ( $from_utc ) { $where .= ' AND created_at >= %s '; $params[] = $from_utc; }
        }
        if ( $to ) {
            $to_utc = self::local_date_bound_to_utc( $to, true );
            if ( $to_utc ) { $where .= ' AND created_at < %s '; $params[] = $to_utc; }
        }

        $sql = "SELECT id, created_at, quiz_slug, name, phone, parcela,
                       utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                       fbclid, gclid, sms_funnel_status
                  FROM {$t} {$where} ORDER BY created_at DESC";
        if ( $params ) $sql = $wpdb->prepare( $sql, $params );
        $rows = $wpdb->get_results( $sql, ARRAY_A );

        nocache_headers();
        header( 'Content-Type: text/csv; charset=utf-8' );
        header( 'Content-Disposition: attachment; filename="mgs-quiz-leads-' . wp_date( 'Ymd-His', null, self::business_timezone() ) . '.csv"' );

        $out = fopen( 'php://output', 'w' );
        fwrite( $out, "\xEF\xBB\xBF" );
        if ( $rows ) {
            fputcsv( $out, array_keys( $rows[0] ) );
            foreach ( $rows as $r ) {
                $r['created_at'] = self::format_created_at( $r['created_at'] );
                fputcsv( $out, $r );
            }
        } else {
            fputcsv( $out, array( 'id','created_at','quiz_slug','name','phone','parcela','utm_source','utm_medium','utm_campaign','utm_term','utm_content','fbclid','gclid','sms_funnel_status' ) );
        }
        fclose( $out );
        exit;
    }

    /* ---------------- Import configs ---------------- */

    public static function import_config() {
        if ( ! current_user_can( 'manage_options' ) ) wp_die( 'forbidden' );
        check_admin_referer( 'mgs_quiz_import_config' );

        if ( empty( $_FILES['csv']['tmp_name'] ) || ! is_uploaded_file( $_FILES['csv']['tmp_name'] ) ) {
            wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz&imported=0&err=nofile' ) );
            exit;
        }

        global $wpdb;
        $t      = $wpdb->prefix . 'mgs_quiz_config';
        $cols   = $wpdb->get_col( "DESC {$t}", 0 );
        $fp     = fopen( $_FILES['csv']['tmp_name'], 'r' );
        if ( ! $fp ) { wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz&imported=0&err=open' ) ); exit; }

        // Detecta BOM
        $bom = fread( $fp, 3 );
        if ( $bom !== "\xEF\xBB\xBF" ) { rewind( $fp ); }

        $header = fgetcsv( $fp );
        if ( ! $header ) { fclose( $fp ); wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz&imported=0&err=header' ) ); exit; }
        $header = array_map( 'trim', $header );

        $inserted = 0; $updated = 0; $skipped = 0;
        while ( ( $row = fgetcsv( $fp ) ) !== false ) {
            $r = array();
            foreach ( $header as $i => $col ) {
                $col = (string) $col;
                if ( ! in_array( $col, $cols, true ) ) continue;
                $r[ $col ] = isset( $row[ $i ] ) ? (string) $row[ $i ] : '';
            }
            if ( empty( $r['slug'] ) ) { $skipped++; continue; }
            $r['slug'] = sanitize_title( $r['slug'] );

            if ( empty( $r['id'] ) ) $r['id'] = wp_generate_uuid4();
            $r['updated_at'] = current_time( 'mysql' );

            $exists = $wpdb->get_var( $wpdb->prepare( "SELECT id FROM {$t} WHERE slug = %s", $r['slug'] ) );
            if ( $exists ) {
                $r['id'] = $exists;
                $wpdb->update( $t, $r, array( 'id' => $exists ) );
                $updated++;
            } else {
                $wpdb->insert( $t, $r );
                $inserted++;
            }
        }
        fclose( $fp );

        wp_safe_redirect( admin_url( 'admin.php?page=mgs-quiz&imported=1&ins=' . $inserted . '&upd=' . $updated . '&skp=' . $skipped ) );
        exit;
    }
}
