<?php
/**
 * Endpoints REST do MGS Quiz.
 *
 *  GET  /wp-json/mgs-quiz/v1/config?slug=quiz-car-parcelas-g002
 *  POST /wp-json/mgs-quiz/v1/lead
 *       body JSON: { slug, name, phone, parcela, utm_*, fbclid, gclid, extra, website, ts }
 *
 * Fluxo do POST /lead:
 *   1) anti-spam (honeypot + tempo mínimo 3s)
 *   2) valida + sanitiza (name >= 2, phone >= 10 dígitos)
 *   3) grava em {prefix}_mgs_quiz_leads
 *   4) encaminha p/ SMS Funnel (URL por gestor, fallback global)
 *   5) responde { ok: true/false, ... } — o cliente só redireciona se ok=true
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

class MGS_Quiz_REST {

    const NS = 'mgs-quiz/v1';
    const MIN_FILL_MS = 3000;

    public static function register() {
        register_rest_route( self::NS, '/config', array(
            'methods'             => 'GET',
            'permission_callback' => '__return_true',
            'callback'            => array( __CLASS__, 'get_config' ),
        ) );
        register_rest_route( self::NS, '/lead', array(
            'methods'             => 'POST',
            'permission_callback' => '__return_true',
            'callback'            => array( __CLASS__, 'create_lead' ),
        ) );
    }

    /* ----------------- helpers ----------------- */

    public static function get_config_by_slug( $slug ) {
        global $wpdb;
        $t   = $wpdb->prefix . 'mgs_quiz_config';
        $row = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$t} WHERE slug = %s LIMIT 1", $slug ), ARRAY_A );
        if ( ! $row ) return null;
        $row['options']           = self::json_or_array( isset( $row['options'] ) ? $row['options'] : '' );
        $row['redirect_variants'] = self::json_or_array( isset( $row['redirect_variants'] ) ? $row['redirect_variants'] : '' );
        $row['sms_funnel_urls']   = self::json_or_array( isset( $row['sms_funnel_urls'] ) ? $row['sms_funnel_urls'] : '' );
        return $row;
    }

    private static function json_or_array( $val ) {
        if ( is_array( $val ) ) return $val;
        if ( ! is_string( $val ) || $val === '' ) return array();
        $d = json_decode( $val, true );
        return is_array( $d ) ? $d : array();
    }

    private static function parse_gestor_from_medium( $medium ) {
        if ( ! is_string( $medium ) ) return null;
        if ( preg_match( '/g0*([1-9]\d*)/i', $medium, $m ) ) {
            return 'G' . str_pad( $m[1], 3, '0', STR_PAD_LEFT );
        }
        return null;
    }

    private static function pick_sms_funnel_url( $cfg, $gestor_code, $utm_medium, $utm_campaign = '', $extra = array() ) {
        $resolved = $gestor_code ? strtoupper( trim( $gestor_code ) ) : null;
        if ( ! $resolved ) {
            $candidates = array(
                $utm_medium,
                $utm_campaign,
                isset( $extra['utm_adgroup'] ) ? $extra['utm_adgroup'] : '',
                isset( $extra['utm_content'] ) ? $extra['utm_content'] : '',
                isset( $cfg['slug'] ) ? $cfg['slug'] : '',
            );
            foreach ( $candidates as $candidate ) {
                $resolved = self::parse_gestor_from_medium( $candidate );
                if ( $resolved ) break;
            }
        }

        $list = ( isset( $cfg['sms_funnel_urls'] ) && is_array( $cfg['sms_funnel_urls'] ) ) ? $cfg['sms_funnel_urls'] : array();
        foreach ( $list as $it ) {
            if ( empty( $it['url'] ) || ( isset( $it['active'] ) && ! (int) $it['active'] ) ) continue;
            if ( ! empty( $it['default'] ) ) {
                $code = isset( $it['gestor_code'] ) ? $it['gestor_code'] : 'default';
                return array( $it['url'], $code );
            }
        }
        if ( $resolved ) {
            foreach ( $list as $it ) {
                if ( isset( $it['active'] ) && ! (int) $it['active'] ) continue;
                if ( ! empty( $it['gestor_code'] ) && strtoupper( $it['gestor_code'] ) === $resolved && ! empty( $it['url'] ) ) {
                    return array( $it['url'], $resolved );
                }
            }
        }
        $valid = array_values( array_filter( $list, function ( $it ) { return ! empty( $it['url'] ) && ( ! isset( $it['active'] ) || (int) $it['active'] ); } ) );
        if ( count( $valid ) >= 1 ) {
            $code = isset( $valid[0]['gestor_code'] ) ? $valid[0]['gestor_code'] : 'default';
            return array( $valid[0]['url'], $code );
        }
        if ( ! empty( $cfg['sms_funnel_url'] ) ) {
            return array( $cfg['sms_funnel_url'], 'fallback' );
        }
        return array( null, null );
    }

    /* ----------------- endpoints ----------------- */

    public static function get_config( WP_REST_Request $req ) {
        $slug = sanitize_title( $req->get_param( 'slug' ) );
        if ( ! $slug ) return new WP_Error( 'bad_slug', 'slug required', array( 'status' => 400 ) );
        $cfg = self::get_config_by_slug( $slug );
        if ( ! $cfg ) return new WP_Error( 'not_found', 'quiz not found', array( 'status' => 404 ) );

        // Não expor SMS Funnel URLs no endpoint público.
        unset( $cfg['sms_funnel_url'], $cfg['sms_funnel_urls'] );
        return rest_ensure_response( $cfg );
    }

    public static function create_lead( WP_REST_Request $req ) {
        global $wpdb;
        $params = $req->get_json_params();
        if ( ! is_array( $params ) ) $params = $req->get_params();

        // ---------- anti-spam ----------
        $hp = isset( $params['website'] ) ? trim( (string) $params['website'] ) : '';
        if ( $hp !== '' ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'spam' ), 400 );
        }
        $ts = isset( $params['ts'] ) ? (int) $params['ts'] : 0;
        $now_ms = (int) round( microtime( true ) * 1000 );
        if ( $ts <= 0 ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'timestamp inválido' ), 400 );
        }
        if ( ( $now_ms - $ts ) < self::MIN_FILL_MS ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'submissão muito rápida' ), 400 );
        }
        if ( ( $now_ms - $ts ) > 21600000 ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'formulário expirado' ), 400 );
        }

        $slug    = sanitize_title( isset( $params['slug'] ) ? $params['slug'] : '' );
        $name    = trim( wp_strip_all_tags( isset( $params['name'] )  ? (string) $params['name']  : '' ) );
        $phone   = preg_replace( '/\D/', '', isset( $params['phone'] ) ? (string) $params['phone'] : '' );
        $parcela = sanitize_text_field( isset( $params['parcela'] ) ? (string) $params['parcela'] : '' );

        if ( ! $slug || strlen( $name ) < 2 || strlen( $phone ) < 10 ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'Nome ou telefone inválido.' ), 400 );
        }

        $cfg = self::get_config_by_slug( $slug );
        if ( ! $cfg ) return new WP_REST_Response( array( 'ok' => false, 'error' => 'Quiz não encontrado.' ), 404 );

        $utm = array(
            'utm_source'   => sanitize_text_field( isset( $params['utm_source'] )   ? $params['utm_source']   : '' ),
            'utm_medium'   => sanitize_text_field( isset( $params['utm_medium'] )   ? $params['utm_medium']   : '' ),
            'utm_campaign' => sanitize_text_field( isset( $params['utm_campaign'] ) ? $params['utm_campaign'] : '' ),
            'utm_term'     => sanitize_text_field( isset( $params['utm_term'] )     ? $params['utm_term']     : '' ),
            'utm_content'  => sanitize_text_field( isset( $params['utm_content'] )  ? $params['utm_content']  : '' ),
        );
        $fbclid = sanitize_text_field( isset( $params['fbclid'] ) ? $params['fbclid'] : '' );
        $gclid  = sanitize_text_field( isset( $params['gclid'] )  ? $params['gclid']  : '' );
        $extra  = ( isset( $params['extra'] ) && is_array( $params['extra'] ) ) ? $params['extra'] : array();

        $table = $wpdb->prefix . 'mgs_quiz_leads';
        $wpdb->insert( $table, array(
            'quiz_slug'      => $slug,
            'quiz_config_id' => isset( $cfg['id'] ) ? $cfg['id'] : '',
            'name'           => substr( $name,  0, 200 ),
            'phone'          => substr( $phone, 0, 20 ),
            'parcela'        => $parcela,
            'utm_source'     => $utm['utm_source'],
            'utm_medium'     => $utm['utm_medium'],
            'utm_campaign'   => $utm['utm_campaign'],
            'utm_term'       => $utm['utm_term'],
            'utm_content'    => $utm['utm_content'],
            'fbclid'         => $fbclid,
            'gclid'          => $gclid,
            'extra_params'   => wp_json_encode( $extra ),
            'ip'             => substr( isset( $_SERVER['REMOTE_ADDR'] ) ? $_SERVER['REMOTE_ADDR'] : '', 0, 64 ),
            'user_agent'     => substr( isset( $_SERVER['HTTP_USER_AGENT'] ) ? $_SERVER['HTTP_USER_AGENT'] : '', 0, 500 ),
        ) );
        $lead_id = (int) $wpdb->insert_id;
        if ( ! $lead_id ) {
            return new WP_REST_Response( array( 'ok' => false, 'error' => 'Erro ao gravar lead.' ), 500 );
        }

        // -------- SMS Funnel (apenas name + phone) --------
        $gestor_code = isset( $params['gestor_code'] ) ? $params['gestor_code'] : '';
        list( $url, $routed ) = self::pick_sms_funnel_url( $cfg, $gestor_code, $utm['utm_medium'], $utm['utm_campaign'], $extra );
        $sms_status = 'skipped';
        $sms_body   = '';

        if ( $url ) {
            $resp = wp_remote_post( $url, array(
                'timeout' => 10,
                'headers' => array(
                    'Content-Type' => 'application/json',
                    'Accept'       => 'application/json',
                ),
                'body'    => wp_json_encode( array( 'name' => $name, 'phone' => $phone ) ),
            ) );
            if ( is_wp_error( $resp ) ) {
                $sms_status = 'error';
                $sms_body   = $resp->get_error_message();
            } else {
                $code     = wp_remote_retrieve_response_code( $resp );
                $sms_body = substr( wp_remote_retrieve_body( $resp ), 0, 500 );
                $sms_status = ( $code >= 200 && $code < 300 ) ? ( 'ok:' . $routed ) : ( 'fail:' . $code );
            }
            $wpdb->update( $table,
                array( 'sms_funnel_status' => $sms_status, 'sms_funnel_response' => $sms_body ),
                array( 'id' => $lead_id )
            );
        }

        $require_sms_success = ! isset( $cfg['require_sms_success'] ) || (int) $cfg['require_sms_success'] === 1;
        $sms_ok = ( strpos( $sms_status, 'ok:' ) === 0 );
        if ( $require_sms_success && ! $sms_ok ) {
            $msg = $url ? 'Não foi possível enviar para o SMS Funnel. Tente novamente.' : 'SMS Funnel não configurado para este quiz.';
            return new WP_REST_Response( array(
                'ok'         => false,
                'lead_id'    => $lead_id,
                'error'      => $msg,
                'sms_funnel' => $sms_status,
            ), 502 );
        }

        return rest_ensure_response( array(
            'ok'                  => true,
            'lead_id'             => $lead_id,
            'sms_funnel'          => $sms_status,
            'redirect_url'        => isset( $cfg['redirect_url'] ) ? $cfg['redirect_url'] : '',
            'redirect_variants'   => isset( $cfg['redirect_variants'] ) ? $cfg['redirect_variants'] : array(),
            'redirect_delay_ms'   => (int) ( ! empty( $cfg['redirect_delay_ms'] ) ? $cfg['redirect_delay_ms'] : 1800 ),
            'redirect_url_weight' => (int) ( isset( $cfg['redirect_url_weight'] ) ? $cfg['redirect_url_weight'] : 0 ),
        ) );
    }
}
