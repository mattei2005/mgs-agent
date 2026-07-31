<?php
/**
 * Plugin Name: MGS Chat Funnels
 * Description: Config-driven WhatsApp-style chat funnels by vertical and country (EMP-BR, CC-BR, CAR-BR) with rewarded/interstitial gate, UTM passthrough, cards/sequential offers, and shortcode/route rendering.
 * Version: 0.4.5
 * Author: MGS Digital Corp
 */

if (!defined('ABSPATH')) {
    exit;
}

require_once plugin_dir_path(__FILE__) . 'includes/class-mgs-chat-sms.php';
MGS_Chat_SMS::boot();

final class MGS_Chat_Funnels {
    const VERSION = '0.4.5';
    const SHORTCODE = 'mgs_chat_funnel';
    const MENU_SLUG = 'mgs-chat-funnels';

    private static $instance = null;
    private $configs = null;
    private $rendered_assets = false;

    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action('init', array($this, 'register_shortcodes'));
        add_action('template_redirect', array($this, 'maybe_render_route'));
        add_action('wp_enqueue_scripts', array($this, 'register_assets'));
        add_action('admin_menu', array($this, 'register_admin_menu'));
    }

    public function register_shortcodes() {
        add_shortcode(self::SHORTCODE, array($this, 'shortcode'));
    }

    public function register_assets() {
        $base_url = plugin_dir_url(__FILE__);
        wp_register_style('mgs-chat-funnels', $base_url . 'assets/chat-funnels.css', array(), self::VERSION);
        wp_register_script('mgs-chat-funnels', $base_url . 'assets/chat-funnels.js', array(), self::VERSION, true);
    }

    private function enqueue_assets($config = null) {
        if (!$this->rendered_assets) {
            $ad_provider = is_array($config) ? $this->ad_provider($config) : 'jbf';
            if (is_array($config) && (($config['ads_enabled'] ?? true) !== false) && $ad_provider === 'jbf') {
                wp_enqueue_script('mgs-chat-funnels-gpt', 'https://securepubads.g.doubleclick.net/tag/js/gpt.js', array(), null, false);
                $wrapper_url = $this->ad_wrapper_url($config);
                if ($wrapper_url !== '') {
                    wp_enqueue_script('mgs-chat-funnels-wrapper', $wrapper_url, array('mgs-chat-funnels-gpt'), self::VERSION, false);
                    wp_script_add_data('mgs-chat-funnels-wrapper', 'strategy', 'defer');
                }
            } elseif (is_array($config) && (($config['ads_enabled'] ?? true) !== false) && $ad_provider === 'actview') {
                wp_enqueue_script('mgs-chat-funnels-actview', 'https://scr.actview.net/zuout.js', array(), null, false);
            }
            wp_enqueue_style('mgs-chat-funnels');
            wp_enqueue_script('mgs-chat-funnels');
            $this->rendered_assets = true;
        }
    }

    public function shortcode($atts) {
        $atts = shortcode_atts(array('id' => ''), $atts, self::SHORTCODE);
        $id = $this->normalize_id($atts['id']);
        if ($id === '') {
            return '<!-- MGS Chat Funnels: missing id -->';
        }
        $config = $this->get_config($id);
        if (!$config) {
            return '<!-- MGS Chat Funnels: config not found for ' . esc_html($id) . ' -->';
        }
        $this->enqueue_assets($config);
        return $this->render_container($config);
    }

    public function maybe_render_route() {
        if (is_admin() || wp_doing_ajax() || (defined('REST_REQUEST') && REST_REQUEST)) {
            return;
        }
        $path = isset($_SERVER['REQUEST_URI']) ? parse_url(wp_unslash($_SERVER['REQUEST_URI']), PHP_URL_PATH) : '';
        $path = '/' . trim((string) $path, '/');
        if ($path === '/') {
            return;
        }
        foreach ($this->get_configs() as $config) {
            $route = isset($config['route']) ? '/' . trim((string) $config['route'], '/') : '';
            if ($route !== '' && untrailingslashit($route) === untrailingslashit($path)) {
                status_header(200);
                nocache_headers();
                $this->render_full_page($config);
                exit;
            }
        }
    }

    private function render_full_page($config) {
        $template = $this->asset_contents('templates/ciro-index-template.html');
        if ($template === '') {
            status_header(500);
            echo '<!doctype html><html><body>Missing chat template.</body></html>';
            return;
        }

        $title = isset($config['title']) ? (string) $config['title'] : 'Chat Funnel';
        $language = isset($config['language']) ? (string) $config['language'] : (get_locale() ?: 'pt-BR');
        $language = str_replace('_', '-', $language);
        $tags = isset($config['tags']) && is_array($config['tags']) ? array_values($config['tags']) : array();
        $tags_json = $this->js_json($tags);
        $persona = isset($config['persona']) && is_array($config['persona']) ? $config['persona'] : array();
        $wrapper_url = (($config['ads_enabled'] ?? true) !== false) ? $this->ad_wrapper_url($config) : '';
        $ad_provider = $this->ad_provider($config);
        $standalone = !empty($config['standalone']);

        $sms_enabled = !empty($config['sms_enabled']);
        $replacements = array(
            '{{HTML_LANG}}' => esc_attr($language),
            '{{TITLE}}' => esc_html($title),
            '{{WP_HEAD}}' => $standalone ? $this->render_tracking_head_html($config) : $this->capture_wp_head($config),
            '{{WP_BODY_OPEN}}' => $standalone ? $this->render_tracking_body_html($config) : $this->capture_wp_body_open(),
            '{{WP_FOOTER}}' => $standalone ? '' : $this->capture_wp_footer(),
            '{{TAGS_SCRIPT}}' => '<script>window.tags = JSON.parse(' . $this->js_json($tags_json) . ');</script>',
            '{{ADS_HEAD}}' => $this->render_ads_head_html($config),
            '{{WRAPPER_URL}}' => esc_url($wrapper_url),
            '{{REWARDED_BUTTON_CLASS}}' => esc_attr($sms_enabled ? '' : ($ad_provider === 'm2' ? 'pg-rewarded' : ($ad_provider === 'actview' ? 'av-rewarded' : ''))),
            '{{REWARDED_BUTTON_CLASS_JS}}' => $this->js_json($ad_provider === 'm2' ? 'pg-rewarded' : ($ad_provider === 'actview' ? 'av-rewarded' : '')),
            '{{REWARDED_CTA_TAG}}' => $ad_provider === 'actview' ? 'a' : 'button',
            '{{REWARDED_CTA_ATTRS}}' => $ad_provider === 'actview'
                ? ($sms_enabled
                    ? 'role="button" tabindex="0"'
                    : 'role="button" tabindex="0" onclick="window.mgsCloseQuizAfterReward && window.mgsCloseQuizAfterReward(); return false;"')
                : 'type="button"',
            '{{BOT_NAMES_JS}}' => $this->js_json($persona['names'] ?? array('Maria')),
            '{{FEMALE_NAMES_JS}}' => $this->js_json($persona['female_names'] ?? array()),
            '{{MALE_NAMES_JS}}' => $this->js_json($persona['male_names'] ?? array()),
            '{{FEMALE_PHOTOS_JS}}' => $this->js_json($persona['female_photos'] ?? array()),
            '{{MALE_PHOTOS_JS}}' => $this->js_json($persona['male_photos'] ?? array()),
            '{{PERSONA_ROLE_JS}}' => $this->js_json($persona['role'] ?? 'Consultor'),
            '{{QUESTIONS_JS}}' => $this->js_json($this->ciro_questions_from_config($config)),
            '{{OFFER_URLS_JS}}' => $this->js_json($this->offer_urls_from_config($config)),
            '{{GATE_SLIDES_HTML}}' => $this->render_gate_slides_html($config),
            '{{GATE_QUESTION_COUNT_JS}}' => (string) $this->gate_question_count($config),
            '{{GATE_CONFIG_JS}}' => $this->js_json($this->gate_public_config($config)),
            '{{GEO_INDICATOR_HTML}}' => $this->render_geo_indicator_html($config),
            '{{GATE_IMAGE_HTML}}' => $this->render_gate_image_html($config),
            '{{GATE_FINAL_HEADER_HTML}}' => $this->render_gate_final_header_html($config),
            '{{LEGAL_FOOTER_HTML}}' => $this->render_legal_footer_html($config),
            '{{SMS_FORM_HTML}}' => MGS_Chat_SMS::form_html($config),
            '{{SMS_SKIP_HTML}}' => MGS_Chat_SMS::skip_html($config, $this->ad_provider($config)),
            '{{SMS_CONFIG_JS}}' => MGS_Chat_SMS::template_js_config($config),
            '{{SMS_CTA_LABEL}}' => esc_html($config['sms_submit_label'] ?? 'TRANSFERIR PARA ESPECIALISTA →'),
            '{{JBF_REWARDED_PRELOAD_JS}}' => $ad_provider === 'jbf' ? "window.jbftag = window.jbftag || { cmd: [] };\n          window.jbftag.cmd.push(() => {\n            if (window.jbftag.requestRewardAds) {\n              window.jbftag.requestRewardAds();\n            }\n          });" : '',
            '{{JBF_REWARDED_SHOW_JS}}' => $ad_provider === 'jbf' ? "try {\n              window.jbftag = window.jbftag || { cmd: [] };\n              window.jbftag.cmd.push(() => {\n                if (window.jbftag.showRewardedAds) {\n                  window.jbftag.showRewardedAds(safeCloseQuiz);\n                } else {\n                  safeCloseQuiz();\n                }\n              });\n            } catch (err) {\n              safeCloseQuiz();\n            }" : '',

        );

        if ($ad_provider === 'actview') {
            $actview_top = '<div id="zout_top_wrapper" align="center" style="width: 100%; margin-top: 2rem; margin-bottom: 2rem; min-height: 400px;"><div><p style="font-size: 10px; text-transform: uppercase; text-align: center;">Anúncios</p><div id="zout_top"></div></div></div>';
            $template = str_replace('adBanner.innerHTML = `<div></div>`;', 'adBanner.innerHTML = `' . $actview_top . '`;', $template);
        }

        echo strtr($template, $replacements); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
    }

    private function gtm_container_id($config) {
        $container_id = strtoupper(trim((string) ($config['gtm_container_id'] ?? '')));
        return preg_match('/^GTM-[A-Z0-9]+$/', $container_id) ? $container_id : '';
    }

    private function ga4_measurement_id($config) {
        $measurement_id = strtoupper(trim((string) ($config['ga4_measurement_id'] ?? '')));
        return preg_match('/^G-[A-Z0-9]+$/', $measurement_id) ? $measurement_id : '';
    }

    private function tracking_mode($config) {
        $mode = strtolower(trim((string) ($config['tracking_mode'] ?? 'gtm')));
        return $mode === 'direct_ga4' ? 'direct_ga4' : 'gtm';
    }

    private function render_tracking_head_html($config) {
        if ($this->tracking_mode($config) === 'direct_ga4') {
            $measurement_id = $this->ga4_measurement_id($config);
            if ($measurement_id === '') {
                return '';
            }
            $id_json = $this->js_json($measurement_id);
            return '<!-- Google Analytics 4 (direct) -->' . "\n"
                . '<script async src="https://www.googletagmanager.com/gtag/js?id=' . esc_attr($measurement_id) . '"></script>' . "\n"
                . '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag(\'js\',new Date());gtag(\'config\',' . $id_json . ');</script>' . "\n"
                . '<!-- End Google Analytics 4 (direct) -->';
        }

        $container_id = $this->gtm_container_id($config);
        if ($container_id === '') {
            return '';
        }
        $id_json = $this->js_json($container_id);
        return '<!-- Google Tag Manager + Analytics -->' . "\n"
            . '<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({\'gtm.start\':new Date().getTime(),event:\'gtm.js\'});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!==\'dataLayer\'?\'&l=\'+l:\'\';j.async=true;j.src=\'https://www.googletagmanager.com/gtm.js?id=\'+i+dl;f.parentNode.insertBefore(j,f);})(window,document,\'script\',\'dataLayer\',' . $id_json . ');</script>' . "\n"
            . '<!-- End Google Tag Manager + Analytics -->';
    }

    private function render_tracking_body_html($config) {
        if ($this->tracking_mode($config) !== 'gtm') {
            return '';
        }
        $container_id = $this->gtm_container_id($config);
        if ($container_id === '') {
            return '';
        }
        return '<!-- Google Tag Manager (noscript) -->' . "\n"
            . '<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=' . esc_attr($container_id) . '" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>' . "\n"
            . '<!-- End Google Tag Manager (noscript) -->';
    }

    private function capture_wp_head($config = null) {
        ob_start();
        wp_head();
        $output = ob_get_clean();
        if (!is_string($output)) {
            return '';
        }
        return $this->sanitize_captured_wp_head($output, $config);
    }

    private function sanitize_captured_wp_head($output, $config = null) {
        if (!is_array($config) || (($config['ads_enabled'] ?? true) === false) || $this->ad_provider($config) === 'm2') {
            return $output;
        }

        // Chat routes own the ad stack through {{ADS_HEAD}}. WordPress head/theme/WPCode
        // may also inject the same JBF/GPT wrapper; strip that layer to avoid duplicate
        // GPT imports, duplicate wrapper scripts, and duplicate window.wrapper_url setup.
        $patterns = array(
            '#<script\b[^>]*src=["\'][^"\']*securepubads\.g\.doubleclick\.net/tag/js/gpt\.js[^"\']*["\'][^>]*>\s*</script>#i',
            '#<script\b[^>]*src=["\'][^"\']*assets\.jbfdigital\.com\.br/[^"\']*\.builder\.js[^"\']*["\'][^>]*>\s*</script>#i',
            '#<script\b[^>]*>[\s\S]*?window\.wrapper_url\s*=\s*["\'][^"\']*assets\.jbfdigital\.com\.br/[^"\']*\.builder\.js[^"\']*["\'][\s\S]*?</script>#i',
        );

        if ($this->ad_provider($config) === 'actview') {
            $patterns[] = '#<script\b[^>]*src=["\'][^"\']*scr\.actview\.net/zuout\.js[^"\']*["\'][^>]*>\s*</script>#i';
        }

        return preg_replace($patterns, '', $output);
    }

    private function capture_wp_body_open() {
        ob_start();
        if (function_exists('wp_body_open')) {
            wp_body_open();
        } else {
            do_action('wp_body_open');
        }
        $output = ob_get_clean();
        return is_string($output) ? $output : '';
    }

    private function capture_wp_footer() {
        ob_start();
        wp_footer();
        $output = ob_get_clean();
        return is_string($output) ? $output : '';
    }

    private function asset_contents($relative_path) {
        $path = plugin_dir_path(__FILE__) . ltrim($relative_path, '/');
        if (!is_readable($path)) {
            return '';
        }
        $contents = file_get_contents($path);
        return is_string($contents) ? $contents : '';
    }

    private function js_json($value) {
        $json = wp_json_encode($value, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
        return $json ? $json : 'null';
    }

    private function ciro_questions_from_config($config) {
        $chat = isset($config['chat']) && is_array($config['chat']) ? $config['chat'] : array();
        $offers = isset($config['offers']) && is_array($config['offers']) ? array_values($config['offers']) : array();
        $mode = $config['mode'] ?? ($chat['offer_mode'] ?? 'cards');
        $questions = array();

        $intro = isset($chat['intro']) && is_array($chat['intro']) ? $chat['intro'] : array('Olá! Eu sou {botName}.');
        $questions[] = array(
            'question' => implode(' | ', array_map('strval', $intro)),
            'answers' => isset($chat['start_answers']) && is_array($chat['start_answers']) ? array_values($chat['start_answers']) : array('✅ Vamos lá!'),
        );

        if (!empty($chat['questions']) && is_array($chat['questions'])) {
            foreach ($chat['questions'] as $item) {
                if (!is_array($item)) {
                    continue;
                }
                $questions[] = array(
                    'question' => (string) ($item['text'] ?? $item['question'] ?? ''),
                    'answers' => isset($item['answers']) && is_array($item['answers']) ? array_values($item['answers']) : array(),
                );
            }
        }

        if ($mode === 'cards') {
            $card_offers = array();
            foreach ($offers as $offer) {
                if (!is_array($offer)) {
                    continue;
                }
                $card_offers[] = array(
                    'name' => (string) ($offer['name'] ?? 'Oferta'),
                    'subtitle' => (string) ($offer['subtitle'] ?? 'Ver oferta'),
                    'bank' => (string) ($offer['bank'] ?? ''),
                    'image' => (string) ($offer['image'] ?? ($offer['logo'] ?? '')),
                    'url' => (string) ($offer['target'] ?? ($offer['url'] ?? '#')),
                );
            }

            $offer_messages = array();
            if (!empty($chat['pre_offer_messages']) && is_array($chat['pre_offer_messages'])) {
                foreach ($chat['pre_offer_messages'] as $message) {
                    $message = trim((string) $message);
                    if ($message !== '') {
                        $offer_messages[] = $message;
                    }
                }
            }
            $headline = (string) ($chat['offer_headline'] ?? '🚗 Encontrei 3 ofertas exclusivas para você! | Toque na que mais te interessa para ver as condições:');
            foreach (explode('|', $headline) as $message) {
                $message = trim((string) $message);
                if ($message !== '') {
                    $offer_messages[] = $message;
                }
            }

            $questions[] = array(
                'question' => implode(' | ', $offer_messages),
                'offers' => $card_offers,
            );
            $questions[] = array('question' => '');
            return $questions;
        }

        foreach ($offers as $index => $offer) {
            if (!is_array($offer)) {
                continue;
            }
            $messages = isset($offer['messages']) && is_array($offer['messages']) ? $offer['messages'] : array($offer['name'] ?? 'Oferta encontrada.');
            $answers = array();
            $answers[] = (string) ($offer['accept_label'] ?? 'Sim, quero conhecer →');
            if (!empty($offer['reject_label']) && isset($offers[$index + 1])) {
                $answers[] = (string) $offer['reject_label'];
            }
            $questions[] = array(
                'question' => implode(' | ', array_map('strval', $messages)),
                'answers' => $answers,
                'target' => (string) ($offer['target'] ?? '#'),
            );
        }

        $questions[] = array('question' => '');
        return $questions;
    }

    private function active_gate_questions($config) {
        $gate = isset($config['gate']) && is_array($config['gate']) ? $config['gate'] : array();
        $raw_questions = isset($gate['questions']) && is_array($gate['questions']) ? array_values($gate['questions']) : array();
        if (empty($raw_questions)) {
            $raw_questions[] = array(
                'text' => '🚗 Você já tem um carro?',
                'answers' => array(array('label' => 'Sim', 'value' => 'sim'), array('label' => 'Não', 'value' => 'nao')),
            );
        }
        $active = array();
        foreach ($raw_questions as $index => $question) {
            if (!is_array($question)) {
                continue;
            }
            if ($index > 0 && isset($question['enabled']) && !$question['enabled']) {
                continue;
            }
            $text = (string) ($question['text'] ?? ($question['question'] ?? ''));
            $answers = isset($question['answers']) && is_array($question['answers']) ? array_values($question['answers']) : array();
            if ($text === '' || empty($answers)) {
                continue;
            }
            $active[] = array('text' => $text, 'answers' => $answers);
        }
        if (empty($active) && !empty($raw_questions[0]) && is_array($raw_questions[0])) {
            $active[] = $raw_questions[0];
        }
        return $active;
    }

    private function gate_question_count($config) {
        return max(1, count($this->active_gate_questions($config)));
    }

    private function render_gate_slides_html($config) {
        $questions = $this->active_gate_questions($config);
        $html = '';
        foreach ($questions as $index => $question) {
            $display = $index === 0 ? 'flex' : 'none';
            $html .= '<div class="aq-slide" data-step="' . esc_attr((string) $index) . '" style="display:' . esc_attr($display) . '; flex-direction:column; align-items:center;">';
            $html .= '<p class="question" style="font-size:22px; margin-bottom:25px; text-align:center; color:#333; font-weight:500;">' . esc_html((string) ($question['text'] ?? '')) . '</p>';
            $html .= '<div style="display:flex; flex-direction:column; gap:12px; width:100%;">';
            foreach ((array) ($question['answers'] ?? array()) as $answer) {
                $label = is_array($answer) ? (string) ($answer['label'] ?? '') : (string) $answer;
                $value = is_array($answer) ? (string) ($answer['value'] ?? $label) : $label;
                if ($label === '') {
                    continue;
                }
                $html .= '<button class="aq-answer" data-value="' . esc_attr($value) . '" style="padding:14px 20px; border:none; border-radius:12px; font-size:15px; cursor:pointer; background:#075e54; color:white; font-family:\'Roboto\',Arial,sans-serif; transition:all 0.3s ease;">' . esc_html($label) . '</button>';
            }
            $html .= '</div></div>';
        }
        return $html;
    }

    private function gate_public_config($config) {
        $gate = isset($config['gate']) && is_array($config['gate']) ? $config['gate'] : array();
        return array(
            'skipLoading' => !empty($gate['skip_loading']),
            'loadingMs' => max(0, (int) ($gate['loading_ms'] ?? 2000)),
            'geoEnabled' => !empty($config['geo_enabled']),
            'geoFallback' => sanitize_text_field($config['geo_fallback_text'] ?? 'Analisando ofertas disponíveis na sua região'),
            'geoPrefix' => sanitize_text_field($config['geo_prefix_text'] ?? 'Analisando ofertas de veículos em'),
        );
    }

    private function render_geo_indicator_html($config) {
        if (empty($config['geo_enabled'])) {
            return '';
        }
        $fallback = sanitize_text_field($config['geo_fallback_text'] ?? 'Analisando ofertas disponíveis na sua região');
        return '<div id="mgs-cf-geo-indicator" aria-live="polite"><span aria-hidden="true">🔍</span> <span id="mgs-cf-geo-text">' . esc_html($fallback) . '</span></div>';
    }

    private function render_gate_image_html($config) {
        $image = trim((string) ($config['sms_gate_image'] ?? ''));
        if ($image === '') {
            return '';
        }
        if ($image === 'default') {
            $image = plugin_dir_url(__FILE__) . 'assets/car-financing-hero.png';
        }
        $image = esc_url($image);
        if ($image === '') {
            return '';
        }
        $alt = sanitize_text_field($config['sms_gate_image_alt'] ?? 'Financiamento de veículos');
        return '<div class="mgs-cf-gate-image"><img src="' . $image . '" alt="' . esc_attr($alt) . '"></div>';
    }

    private function render_gate_final_header_html($config) {
        if (!empty($config['sms_compact_gate'])) {
            $intro = sanitize_text_field($config['sms_form_intro'] ?? 'Preencha seus dados e veja as parcelas:');
            return '<p class="mgs-cf-sms-intro">' . esc_html($intro) . '</p>';
        }
        $gate = isset($config['gate']) && is_array($config['gate']) ? $config['gate'] : array();
        $icon = sanitize_text_field($gate['final_icon'] ?? '🚗');
        $title = sanitize_text_field($gate['final_title'] ?? 'Oferta encontrada!');
        $subtitle = sanitize_text_field($gate['final_subtitle'] ?? 'Um especialista foi identificado para te atender agora.');
        return '<div class="mgs-cf-final-icon">' . esc_html($icon) . '</div>'
            . '<p class="mgs-cf-final-title">' . esc_html($title) . '</p>'
            . '<p class="mgs-cf-final-subtitle">' . esc_html($subtitle) . '</p>';
    }

    private function render_legal_footer_html($config) {
        $links = isset($config['legal_links']) && is_array($config['legal_links']) ? array_values($config['legal_links']) : array();
        $items = array();
        foreach ($links as $link) {
            if (!is_array($link)) {
                continue;
            }
            $label = sanitize_text_field($link['label'] ?? '');
            $url = esc_url($link['url'] ?? '');
            if ($label === '' || $url === '') {
                continue;
            }
            $items[] = '<a href="' . $url . '" target="_blank" rel="noopener noreferrer">' . esc_html($label) . '</a>';
        }
        if (empty($items)) {
            return '';
        }
        return '<nav class="mgs-cf-legal-footer" aria-label="Links legais">' . implode('<span aria-hidden="true">|</span>', $items) . '</nav>';
    }

    private function offer_urls_from_config($config) {
        $offers = isset($config['offers']) && is_array($config['offers']) ? array_values($config['offers']) : array();
        $urls = array();
        foreach ($offers as $offer) {
            if (is_array($offer) && !empty($offer['target'])) {
                $urls[] = (string) $offer['target'];
            }
        }
        return $urls;
    }

    private function render_container($config) {
        $this->enqueue_assets($config);
        $id = isset($config['id']) ? $this->normalize_id($config['id']) : 'mgs-chat-funnel';
        $public_config = MGS_Chat_SMS::public_config($config);
        $json = wp_json_encode($public_config, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP);
        if (!$json) {
            return '<!-- MGS Chat Funnels: invalid config JSON -->';
        }
        ob_start();
        ?>
<div class="mgs-chat-funnel" data-funnel-id="<?php echo esc_attr($id); ?>">
    <script type="application/json" class="mgs-chat-funnel-config"><?php echo $json; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?></script>
    <div class="mgs-chat-funnel-root" aria-live="polite"></div>
</div>
        <?php
        return trim(ob_get_clean());
    }

    private function get_config($id) {
        $configs = $this->get_configs();
        $id = $this->normalize_id($id);
        return isset($configs[$id]) ? $configs[$id] : null;
    }

    private function get_configs() {
        if ($this->configs !== null) {
            return $this->configs;
        }
        $this->configs = array();
        $dir = $this->configs_dir();
        if (!is_dir($dir)) {
            wp_mkdir_p($dir);
        }
        foreach (glob($dir . '*.json') as $file) {
            $raw = file_get_contents($file);
            $config = json_decode($raw, true);
            if (!is_array($config) || empty($config['id'])) {
                continue;
            }
            $id = $this->normalize_id($config['id']);
            $config['_file'] = basename($file);
            $this->configs[$id] = $config;
        }
        ksort($this->configs);
        return $this->configs;
    }

    private function configs_dir() {
        return plugin_dir_path(__FILE__) . 'configs/';
    }

    private function config_file_for_id($id) {
        $id = $this->normalize_id($id);
        if ($id === '') {
            return '';
        }
        return $this->configs_dir() . strtolower($id) . '.json';
    }

    private function normalize_id($id) {
        $id = strtoupper(trim((string) $id));
        $id = preg_replace('/[^A-Z0-9_-]+/', '-', $id);
        return trim($id, '-');
    }

    private function clean_route($route) {
        $route = '/' . trim((string) $route, '/');
        $route = preg_replace('#/+#', '/', $route);
        return $route === '/' ? '/chat/novo/br1' : $route;
    }

    private function clean_ad_slug($value, $fallback = '') {
        $value = strtolower(trim((string) $value));
        $value = preg_replace('/[^a-z0-9_-]+/', '-', $value);
        $value = trim($value, '-_');
        return $value !== '' ? $value : $fallback;
    }

    private function current_site_ad_slug() {
        $host = parse_url(home_url(), PHP_URL_HOST);
        $host = preg_replace('/^www\./', '', (string) $host);
        return $this->clean_ad_slug(strtok($host, '.') ?: '', '');
    }

    private function ad_wrapper_url($config) {
        if (in_array($this->ad_provider($config), array('m2', 'actview'), true)) {
            return '';
        }
        $company = $this->clean_ad_slug($config['ad_company'] ?? 'digital-trust', 'digital-trust');
        $domain = $this->clean_ad_slug($config['ad_domain'] ?? '', '');
        if ($domain === '') {
            $domain = $this->current_site_ad_slug();
        }
        if ($domain === '') {
            return '';
        }
        return 'https://assets.jbfdigital.com.br/assets/' . rawurlencode($company) . '/' . rawurlencode($domain) . '/' . rawurlencode($company . '_' . $domain) . '.builder.js';
    }

    private function ad_provider($config) {
        $provider = strtolower(trim((string) ($config['ad_provider'] ?? 'jbf')));
        if (in_array($provider, array('m2', 'monetizemore', 'monetize-more'), true)) {
            return 'm2';
        }
        if (in_array($provider, array('actview', 'zuout-actview'), true)) {
            return 'actview';
        }
        return 'jbf';
    }

    private function render_ads_head_html($config) {
        if (($config['ads_enabled'] ?? true) === false) {
            return '';
        }
        if ($this->ad_provider($config) === 'm2') {
            return '<!-- MGS Chat Funnels: MonetizeMore/M2 mode. Rewarded ads trigger from .pg-rewarded buttons. -->' . "\n" . '<script type="text/javascript" async src="https://c.pubguru.net/pg.wantabrand.js"></script>';
        }
        if ($this->ad_provider($config) === 'actview') {
            return "<link rel='preload' as='script' href='https://securepubads.g.doubleclick.net/tag/js/gpt.js' />" . "\n" . '<script async src="https://scr.actview.net/zuout.js"></script>';
        }

        $tags = isset($config['tags']) && is_array($config['tags']) ? array_values($config['tags']) : array();
        $tags_json = $this->js_json($tags);
        $wrapper_url = $this->ad_wrapper_url($config);
        $html = '<script>window.tags = JSON.parse(' . $this->js_json($tags_json) . ');</script>' . "\n";
        $html .= '<script async src="https://securepubads.g.doubleclick.net/tag/js/gpt.js"></script>' . "\n";
        if ($wrapper_url !== '') {
            $html .= '<script defer src="' . esc_url($wrapper_url) . '"></script>';
        }
        return $html;
    }

    private function render_ads_head_config($config) {
        $tags = isset($config['tags']) && is_array($config['tags']) ? array_values($config['tags']) : array();
        $json = wp_json_encode($tags, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP);
        if (!$json) {
            $json = '[]';
        }
        echo '<script>window.tags = ' . $json . ';</script>' . "
"; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
    }

    public function register_admin_menu() {
        add_menu_page(
            'MGS Chat Funnels',
            'MGS Chats',
            'manage_options',
            self::MENU_SLUG,
            array($this, 'render_admin_page'),
            'dashicons-format-chat',
            58
        );
        add_submenu_page(self::MENU_SLUG, 'Todos os chats', 'Todos os chats', 'manage_options', self::MENU_SLUG, array($this, 'render_admin_page'));
        add_submenu_page(self::MENU_SLUG, 'Criar chat', 'Criar chat', 'manage_options', self::MENU_SLUG . '-new', array($this, 'render_admin_new_page'));
        add_submenu_page(self::MENU_SLUG, 'Leads SMS', 'Leads', 'manage_options', self::MENU_SLUG . '-leads', array('MGS_Chat_SMS', 'render_leads_page'));
        add_submenu_page(self::MENU_SLUG, 'Relatórios SMS', 'Relatórios', 'manage_options', self::MENU_SLUG . '-reports', array('MGS_Chat_SMS', 'render_report_page'));
        add_submenu_page(self::MENU_SLUG, 'SMS Funnel', 'SMS', 'manage_options', self::MENU_SLUG . '-sms', array('MGS_Chat_SMS', 'render_sms_settings_page'));
    }

    public function render_admin_new_page() {
        $_GET['view'] = 'new';
        $this->render_admin_page();
    }

    public function render_admin_reports_page() {
        $_GET['view'] = 'reports';
        $this->render_admin_page();
    }

    public function render_admin_page() {
        if (!current_user_can('manage_options')) {
            wp_die(esc_html__('Você não tem permissão para acessar esta página.', 'mgs-chat-funnels'));
        }

        $notice = $this->handle_admin_post();
        $configs = $this->get_configs();
        $view = isset($_GET['view']) ? sanitize_key(wp_unslash($_GET['view'])) : 'edit';
        $selected_id = isset($_GET['funnel']) ? $this->normalize_id(wp_unslash($_GET['funnel'])) : '';
        if ($selected_id === '' && !empty($configs)) {
            $selected_id = array_key_first($configs);
        }
        $selected = ($selected_id && isset($configs[$selected_id])) ? $configs[$selected_id] : null;

        $this->admin_css();
        echo '<div class="wrap mgs-cf-admin">';
        echo '<div class="mgs-cf-topbar">';
        echo '<div><h1>MGS Chat Funnels</h1><p>Gerenciador humano de chats: criar, duplicar, editar campos, excluir e acompanhar rotas publicadas.</p></div>';
        echo '<div class="mgs-cf-top-actions">';
        echo '<a class="button button-primary" href="' . esc_url(admin_url('admin.php?page=' . self::MENU_SLUG . '&view=new')) . '">Criar chat novo</a> ';
        echo '<a class="button" href="' . esc_url(admin_url('admin.php?page=' . self::MENU_SLUG . '&view=duplicate')) . '">Duplicar chat</a> ';
        echo '<a class="button" href="' . esc_url(admin_url('admin.php?page=' . self::MENU_SLUG . '-reports')) . '">Relatórios</a>';
        echo '</div></div>';

        if ($notice) {
            printf('<div class="notice notice-%s is-dismissible"><p>%s</p></div>', esc_attr($notice['type']), wp_kses_post($notice['message']));
        }

        echo '<div class="mgs-cf-admin-grid">';
        $this->render_sidebar($configs, $selected_id, $view);
        echo '<main class="mgs-cf-panel mgs-cf-main">';
        if ($view === 'new') {
            $this->render_human_editor($this->default_config(), true);
        } elseif ($view === 'duplicate') {
            $this->render_duplicate_panel($configs, $selected_id);
        } elseif ($view === 'reports') {
            MGS_Chat_SMS::render_report_page();
        } elseif ($selected) {
            $this->render_human_editor($selected, false);
        } else {
            echo '<h2>Nenhum chat encontrado</h2><p>Crie o primeiro chat para começar.</p>';
        }
        echo '</main></div></div>';
    }

    private function render_sidebar($configs, $selected_id, $view) {
        echo '<aside class="mgs-cf-panel mgs-cf-sidebar">';
        echo '<h2>Chats</h2>';
        echo '<div class="mgs-cf-side-buttons"><a class="button button-primary" href="' . esc_url(admin_url('admin.php?page=' . self::MENU_SLUG . '&view=new')) . '">+ Novo</a><a class="button" href="' . esc_url(admin_url('admin.php?page=' . self::MENU_SLUG . '&view=duplicate')) . '">Duplicar</a></div>';
        echo '<ul class="mgs-cf-list">';
        foreach ($configs as $id => $config) {
            $active = ($id === $selected_id && $view === 'edit') ? ' is-active' : '';
            $mode = $config['mode'] ?? ($config['chat']['offer_mode'] ?? 'cards');
            $route = $config['route'] ?? '';
            echo '<li class="' . esc_attr($active) . '"><a href="' . esc_url(admin_url('admin.php?page=' . self::MENU_SLUG . '&funnel=' . rawurlencode($id))) . '">';
            echo '<strong>' . esc_html($id) . '</strong><span>' . esc_html($config['title'] ?? 'Sem título') . '</span><em>' . esc_html($mode . ' • ' . $route) . '</em>';
            echo '</a></li>';
        }
        echo '</ul>';
        echo '</aside>';
    }

    private function handle_admin_post() {
        if ($_SERVER['REQUEST_METHOD'] !== 'POST' || empty($_POST['mgs_cf_action'])) {
            return null;
        }
        check_admin_referer('mgs_cf_save', 'mgs_cf_nonce');
        $action = sanitize_key(wp_unslash($_POST['mgs_cf_action']));

        if ($action === 'delete') {
            return $this->handle_delete();
        }
        if ($action === 'duplicate') {
            return $this->handle_duplicate();
        }
        if ($action === 'save_raw') {
            return $this->handle_save_raw();
        }
        if ($action === 'save_human') {
            return $this->handle_save_human();
        }
        return array('type' => 'error', 'message' => 'Ação desconhecida.');
    }

    private function handle_delete() {
        $id = $this->normalize_id(wp_unslash($_POST['id'] ?? ''));
        $file = $this->config_file_for_id($id);
        if ($id && is_file($file) && unlink($file)) {
            $this->configs = null;
            return array('type' => 'success', 'message' => 'Chat excluído: <code>' . esc_html($id) . '</code>.');
        }
        return array('type' => 'error', 'message' => 'Não foi possível excluir o chat.');
    }

    private function handle_duplicate() {
        $source_id = $this->normalize_id(wp_unslash($_POST['source_id'] ?? ''));
        $new_id = $this->normalize_id(wp_unslash($_POST['new_id'] ?? ''));
        $new_route = $this->clean_route(wp_unslash($_POST['new_route'] ?? ''));
        $new_title = sanitize_text_field(wp_unslash($_POST['new_title'] ?? ''));
        $source = $this->get_config($source_id);
        if (!$source || $new_id === '') {
            return array('type' => 'error', 'message' => 'Escolha o chat de origem e informe o novo ID.');
        }
        $file = $this->config_file_for_id($new_id);
        if (is_file($file)) {
            return array('type' => 'error', 'message' => 'Já existe um chat com esse ID. Escolha outro nome.');
        }
        unset($source['_file']);
        $source['id'] = $new_id;
        $source['route'] = $new_route;
        if ($new_title !== '') {
            $source['title'] = $new_title;
        }
        $saved = $this->save_config($source);
        if (is_wp_error($saved)) {
            return array('type' => 'error', 'message' => esc_html($saved->get_error_message()));
        }
        return array('type' => 'success', 'message' => 'Chat duplicado: <code>' . esc_html($source_id) . '</code> → <code>' . esc_html($new_id) . '</code>. Pasta/URL criada: <code>' . esc_html($new_route) . '</code>.');
    }

    private function handle_save_raw() {
        $raw_json = isset($_POST['raw_json']) ? wp_unslash($_POST['raw_json']) : '';
        $config = json_decode($raw_json, true);
        if (!is_array($config)) {
            return array('type' => 'error', 'message' => 'JSON inválido. Nada foi salvo.');
        }
        $saved = $this->save_config($config);
        if (is_wp_error($saved)) {
            return array('type' => 'error', 'message' => esc_html($saved->get_error_message()));
        }
        return array('type' => 'success', 'message' => 'JSON salvo com sucesso: <code>' . esc_html($this->normalize_id($config['id'] ?? '')) . '</code>.');
    }

    private function handle_save_human() {
        $id = $this->normalize_id(wp_unslash($_POST['id'] ?? ''));
        $existing = $this->get_config($id);
        $config = is_array($existing) ? $existing : $this->default_config();
        unset($config['_file']);

        $config['id'] = $id;
        $config['title'] = sanitize_text_field(wp_unslash($_POST['title'] ?? ''));
        unset($config['brand']);
        $config['vertical'] = sanitize_key(wp_unslash($_POST['vertical'] ?? 'emp'));
        $config['country'] = sanitize_key(wp_unslash($_POST['country'] ?? 'br'));
        $config['language'] = sanitize_text_field(wp_unslash($_POST['language'] ?? 'pt-BR'));
        $posted_route = $this->clean_route(wp_unslash($_POST['route'] ?? ''));
        $config['route'] = is_array($existing) && !empty($existing['route']) ? $existing['route'] : $posted_route;
        $config['theme'] = 'whatsapp';
        $config['mode'] = sanitize_key(wp_unslash($_POST['mode'] ?? 'cards'));
        $config['sms_enabled'] = !empty($_POST['sms_enabled']);
        $config['sms_manager_code'] = strtoupper(sanitize_text_field(wp_unslash($_POST['sms_manager_code'] ?? '')));
        $config['sms_name_label'] = sanitize_text_field(wp_unslash($_POST['sms_name_label'] ?? 'Nome'));
        $config['sms_phone_label'] = sanitize_text_field(wp_unslash($_POST['sms_phone_label'] ?? 'Telefone'));
        $config['sms_submit_label'] = sanitize_text_field(wp_unslash($_POST['sms_submit_label'] ?? 'TRANSFERIR PARA ESPECIALISTA →'));
        $config['sms_optional'] = !empty($_POST['sms_optional']);
        $config['sms_skip_label'] = sanitize_text_field(wp_unslash($_POST['sms_skip_label'] ?? 'Pular, quero ver as ofertas'));
        $config['sms_consent_enabled'] = !empty($_POST['sms_consent_enabled']);
        $config['sms_consent_default'] = !empty($_POST['sms_consent_default']);
        $config['sms_consent_label'] = sanitize_text_field(wp_unslash($_POST['sms_consent_label'] ?? 'Aceito receber ofertas por SMS.'));
        $config['sms_compact_gate'] = !empty($_POST['sms_compact_gate']);
        $config['sms_form_intro'] = sanitize_text_field(wp_unslash($_POST['sms_form_intro'] ?? 'Preencha seus dados e veja as parcelas:'));
        $gate_image = trim((string) wp_unslash($_POST['sms_gate_image'] ?? ''));
        $config['sms_gate_image'] = $gate_image === 'default' ? 'default' : esc_url_raw($gate_image);
        $config['sms_gate_image_alt'] = sanitize_text_field(wp_unslash($_POST['sms_gate_image_alt'] ?? 'Financiamento de veículos'));
        $config['geo_enabled'] = !empty($_POST['geo_enabled']);
        $config['geo_fallback_text'] = sanitize_text_field(wp_unslash($_POST['geo_fallback_text'] ?? 'Analisando ofertas disponíveis na sua região'));
        $config['geo_prefix_text'] = sanitize_text_field(wp_unslash($_POST['geo_prefix_text'] ?? 'Analisando ofertas de veículos em'));
        if ($config['sms_enabled'] && !MGS_Chat_SMS::manager_is_configured($config['sms_manager_code'])) {
            return array('type' => 'error', 'message' => 'Configure a URL do gestor no menu SMS antes de ativar a captura neste chat.');
        }
        $config['standalone'] = !empty($_POST['standalone']);
        $config['tracking_mode'] = sanitize_key(wp_unslash($_POST['tracking_mode'] ?? 'gtm'));
        if (!in_array($config['tracking_mode'], array('gtm', 'direct_ga4'), true)) {
            $config['tracking_mode'] = 'gtm';
        }
        $config['gtm_container_id'] = $this->gtm_container_id(array('gtm_container_id' => wp_unslash($_POST['gtm_container_id'] ?? '')));
        $config['ga4_measurement_id'] = $this->ga4_measurement_id(array('ga4_measurement_id' => wp_unslash($_POST['ga4_measurement_id'] ?? '')));
        foreach (array('rewarded' . '_enabled', 'rewarded' . '_auctions', 'rewarded' . '_timeout_ms') as $legacy_ads_key) {
            unset($config[$legacy_ads_key]);
        }
        $config['ads_enabled'] = true;
        $config['ad_company'] = $this->clean_ad_slug(wp_unslash($_POST['ad_company'] ?? 'digital-trust'), 'digital-trust');
        $posted_ad_domain = $this->clean_ad_slug(wp_unslash($_POST['ad_domain'] ?? ''), '');
        $config['ad_domain'] = $posted_ad_domain !== '' ? $posted_ad_domain : $this->current_site_ad_slug();
        $config['utm_passthrough'] = !empty($_POST['utm_passthrough']);
        $config['tags'] = $this->parse_csv_text(wp_unslash($_POST['tags'] ?? ''));

        $config['persona'] = isset($config['persona']) && is_array($config['persona']) ? $config['persona'] : array();
        $config['persona']['names'] = $this->parse_lines(wp_unslash($_POST['persona_names'] ?? ''));
        $config['persona']['female_names'] = $this->parse_lines(wp_unslash($_POST['persona_female_names'] ?? ''));
        $config['persona']['role'] = sanitize_text_field(wp_unslash($_POST['persona_role'] ?? 'Consultor'));
        $config['persona']['status'] = sanitize_text_field(wp_unslash($_POST['persona_status'] ?? '🟢 online agora'));

        $gate_questions = $this->parse_questions(wp_unslash($_POST['gate_questions'] ?? ''));
        if (!empty($gate_questions[0])) {
            $gate_questions[0]['enabled'] = true;
        }
        if (isset($gate_questions[1])) {
            $gate_questions[1]['enabled'] = !empty($_POST['gate_question_2_enabled']);
        }

        $config['gate'] = array(
            'enabled' => !empty($_POST['gate_enabled']),
            'questions' => $gate_questions,
            'skip_loading' => !empty($_POST['gate_skip_loading']),
            'loading_text' => sanitize_text_field(wp_unslash($_POST['gate_loading_text'] ?? '')),
            'loading_ms' => max(200, intval($_POST['gate_loading_ms'] ?? 1800)),
            'final_icon' => sanitize_text_field(wp_unslash($_POST['gate_final_icon'] ?? '💬')),
            'final_title' => sanitize_text_field(wp_unslash($_POST['gate_final_title'] ?? 'Oferta encontrada!')),
            'final_subtitle' => sanitize_text_field(wp_unslash($_POST['gate_final_subtitle'] ?? '')),
            'cta_label' => sanitize_text_field(wp_unslash($_POST['gate_cta_label'] ?? 'VER OFERTAS →')),
            'footer_note' => sanitize_text_field(wp_unslash($_POST['gate_footer_note'] ?? '')),
        );

        $pre_offer_messages = $this->parse_lines(wp_unslash($_POST['chat_pre_offer_messages'] ?? ''));
        $offer_headline = sanitize_textarea_field(wp_unslash($_POST['chat_offer_headline'] ?? ''));
        if (isset($_POST['chat_offer_search_message']) || isset($_POST['chat_offer_found_message']) || isset($_POST['chat_offer_instruction_message'])) {
            $search_message = sanitize_text_field(wp_unslash($_POST['chat_offer_search_message'] ?? ''));
            $found_message = sanitize_text_field(wp_unslash($_POST['chat_offer_found_message'] ?? ''));
            $instruction_message = sanitize_text_field(wp_unslash($_POST['chat_offer_instruction_message'] ?? ''));
            $pre_offer_messages = $search_message !== '' ? array($search_message) : array();
            $offer_headline = implode(' | ', array_values(array_filter(array($found_message, $instruction_message), function($v) { return $v !== ''; })));
        }

        $config['chat'] = array(
            'intro' => $this->parse_lines(wp_unslash($_POST['chat_intro'] ?? '')),
            'start_answers' => $this->parse_lines(wp_unslash($_POST['chat_start_answers'] ?? '')),
            'questions' => $this->parse_questions(wp_unslash($_POST['chat_questions'] ?? '')),
            'pre_offer_messages' => $pre_offer_messages,
            'offer_headline' => $offer_headline,
        );

        $config['offers'] = $this->parse_offer_fields($_POST, $config['mode']);

        $saved = $this->save_config($config);
        if (is_wp_error($saved)) {
            return array('type' => 'error', 'message' => esc_html($saved->get_error_message()));
        }
        return array('type' => 'success', 'message' => 'Chat salvo: <code>' . esc_html($config['id']) . '</code>. A rota pública foi atualizada.');
    }

    private function save_config($config) {
        if (!is_array($config)) {
            return new WP_Error('invalid_config', 'Config inválida.');
        }
        $id = $this->normalize_id($config['id'] ?? '');
        if ($id === '') {
            return new WP_Error('missing_id', 'O campo ID é obrigatório.');
        }
        $config['id'] = $id;
        unset($config['_file']);
        $pretty = wp_json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if (!$pretty) {
            return new WP_Error('json_error', 'Erro ao serializar JSON.');
        }
        $dir = $this->configs_dir();
        if (!is_dir($dir)) {
            wp_mkdir_p($dir);
        }
        $file = $this->config_file_for_id($id);
        if (file_put_contents($file, $pretty . PHP_EOL) === false) {
            return new WP_Error('write_error', 'Não foi possível gravar o arquivo de configuração.');
        }
        $this->configs = null;
        return true;
    }

    private function render_human_editor($config, $is_new = false) {
        $config = $this->strip_internal_config($config);
        $id = $this->normalize_id($config['id'] ?? '');
        $route = $config['route'] ?? '';
        $public_url = $route ? home_url('/' . trim($route, '/')) : '';
        $shortcode = '[mgs_chat_funnel id="' . $id . '"]';
        $raw = wp_json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $mode = $config['mode'] ?? ($config['chat']['offer_mode'] ?? 'cards');

        echo '<div class="mgs-cf-edit-header">';
        echo '<div><h2>' . esc_html($is_new ? 'Criar chat novo' : 'Editar chat') . '</h2><p>Interface de gestor: edite campos reais, não JSON bruto.</p></div>';
        echo '<div class="mgs-cf-pills"><span>' . esc_html($id) . '</span><span>' . esc_html(strtoupper($mode)) . '</span></div></div>';

        echo '<div class="mgs-cf-meta">';
        echo '<span><strong>URL do chat:</strong> ' . ($public_url ? '<a href="' . esc_url($public_url) . '" target="_blank" rel="noopener noreferrer">' . esc_html($public_url) . '</a>' : '—') . '</span>';
        echo '<span><strong>Shortcode:</strong> <code>' . esc_html($shortcode) . '</code></span>';
        echo '<span><strong>Arquivo:</strong> <code>configs/' . esc_html(strtolower($id)) . '.json</code></span>';
        echo '</div>';

        echo '<form method="post" class="mgs-cf-form">';
        wp_nonce_field('mgs_cf_save', 'mgs_cf_nonce');
        echo '<input type="hidden" name="mgs_cf_action" value="save_human">';

        echo '<section class="mgs-cf-section"><h3>1. Modelo de oferta</h3><div class="mgs-cf-fields">';
        echo '<label><span>Modelo de oferta</span><select name="mode"><option value="cards"' . selected($mode, 'cards', false) . '>Cards: mostra todas as ofertas</option><option value="sequential"' . selected($mode, 'sequential', false) . '>Sequencial: uma oferta por vez</option></select><small>Cards: mostra todas as opções juntas, bom para comparação/vitrine. Sequencial: mostra uma oferta por vez, bom para simular atendimento humano e priorizar a oferta com maior EPC/ROI; se o usuário recusar, aparece a próxima.</small></label>';
        echo '<div class="mgs-cf-mode-help mgs-cf-full"><strong>Diferença prática:</strong><br><b>Cards</b> = o usuário vê Nubank/C6/BV ao mesmo tempo e escolhe. <br><b>Sequencial</b> = o consultor apresenta Oferta 1; se o usuário clicar “não, mostre outra”, aparece Oferta 2, depois Oferta 3. Use sequencial quando existir prioridade comercial.</div>';
        echo '</div></section>';

        echo '<section class="mgs-cf-section"><h3>2. Identidade e URL</h3><div class="mgs-cf-fields">';
        $this->field_text('ID do chat', 'id', $id, 'Ex: EMP-BR-02. Esse nome vira o arquivo de configuração.', $is_new ? '' : 'readonly');
        $this->field_text('Nome interno', 'title', $config['title'] ?? '', 'Aparece no painel e no título da rota.');
        $this->field_text('URL / pasta do chat', 'route', $route, $is_new ? 'Ex: /chat/emp/br2. Defina isso na criação ou duplicação.' : 'Travado para evitar quebrar campanha/link já em tráfego. Para mudar URL, duplique o chat e escolha nova pasta.', $is_new ? '' : 'readonly');
        $this->field_select('Vertical', 'vertical', strtolower($config['vertical'] ?? 'emp'), array(
            'app' => 'APP',
            'car' => 'CAR',
            'cc' => 'CC',
            'emp' => 'EMP',
            'job' => 'JOB',
            'loan' => 'LOAN',
        ), 'Selecione a vertical do chat.');
        $this->field_select('País', 'country', strtolower($config['country'] ?? 'br'), array(
            'ar' => 'AR',
            'br' => 'BR',
            'ca' => 'CA',
            'es' => 'ES',
            'mx' => 'MX',
            'tr' => 'TR',
            'us' => 'US',
            'za' => 'ZA',
        ), 'Selecione o país/mercado do chat.');
        $this->field_select('Idioma', 'language', $config['language'] ?? 'pt-BR', array(
            'de' => 'Alemão',
            'es' => 'Espanhol',
            'fr' => 'Francês',
            'en-US' => 'Inglês',
            'ja' => 'Japonês',
            'pt-BR' => 'Português-BR',
            'pt-PT' => 'Português-PT',
            'tr' => 'Turco',
        ), 'Selecione o idioma do chat.');
        echo '</div></section>';

        echo '<section class="mgs-cf-section"><h3>3. Captura SMS</h3><div class="mgs-cf-fields">';
        $this->field_checkbox('Ativar nome e telefone antes de transferir', 'sms_enabled', !empty($config['sms_enabled']), 'Ativo somente nesta variante. O chat só continua depois que o lead for salvo e aceito pelo SMS Funnel.');
        $sms_options = array('' => 'Selecione um gestor') + MGS_Chat_SMS::manager_options();
        $this->field_select('Gestor / lista SMS Funnel', 'sms_manager_code', strtoupper($config['sms_manager_code'] ?? ''), $sms_options, 'O gestor escolhido é fixo para este chat, com ou sem UTM. As URLs são administradas no menu SMS.');
        $this->field_text('Label do campo Nome', 'sms_name_label', $config['sms_name_label'] ?? 'Nome', 'Texto mostrado acima do campo de nome.');
        $this->field_text('Label do campo Telefone', 'sms_phone_label', $config['sms_phone_label'] ?? 'Telefone', 'Texto mostrado acima do campo de telefone.');
        $this->field_text('Texto do botão de envio', 'sms_submit_label', $config['sms_submit_label'] ?? 'TRANSFERIR PARA ESPECIALISTA →', 'Depois do envio bem-sucedido, o fluxo atual de anúncio e chat continua normalmente.');
        $this->field_checkbox('Permitir pular nome e telefone', 'sms_optional', !empty($config['sms_optional']), 'Mostra um botão secundário que continua sem criar lead nem enviar SMS.');
        $this->field_text('Texto do botão Pular', 'sms_skip_label', $config['sms_skip_label'] ?? 'Pular, quero ver as ofertas', 'Usado somente quando a captura é opcional.');
        $this->field_checkbox('Mostrar consentimento para SMS', 'sms_consent_enabled', !empty($config['sms_consent_enabled']), 'Exibe o consentimento dentro do formulário.');
        $this->field_checkbox('Consentimento selecionado por padrão', 'sms_consent_default', !empty($config['sms_consent_default']), 'O visitante ainda pode desmarcar e continuar sem cadastrar o lead.');
        $this->field_text('Texto do consentimento', 'sms_consent_label', $config['sms_consent_label'] ?? 'Aceito receber ofertas por SMS.', 'Texto ao lado do checkbox.');
        $this->field_checkbox('Formulário compacto, sem “Oferta encontrada”', 'sms_compact_gate', !empty($config['sms_compact_gate']), 'Vai direto da pergunta inicial para nome/telefone.');
        $this->field_text('Introdução do formulário', 'sms_form_intro', $config['sms_form_intro'] ?? 'Preencha seus dados e veja as parcelas:', 'Linha acima de Nome e Telefone.');
        $this->field_text('Imagem do gate/formulário', 'sms_gate_image', $config['sms_gate_image'] ?? '', 'Use default para a imagem padrão do plugin ou informe uma URL HTTPS.');
        $this->field_text('Texto alternativo da imagem', 'sms_gate_image_alt', $config['sms_gate_image_alt'] ?? 'Financiamento de veículos', 'Descrição acessível da imagem.');
        $this->field_checkbox('Mostrar região do visitante', 'geo_enabled', !empty($config['geo_enabled']), 'Consulta cidade/região pelo IP; em falha, mantém o texto genérico.');
        $this->field_text('Texto quando a região não carregar', 'geo_fallback_text', $config['geo_fallback_text'] ?? 'Analisando ofertas disponíveis na sua região', 'Fallback sem inventar cidade ou quantidade.');
        $this->field_text('Prefixo antes da cidade', 'geo_prefix_text', $config['geo_prefix_text'] ?? 'Analisando ofertas de veículos em', 'Ex.: Analisando ofertas de veículos em Miami, FL.');
        echo '<div class="mgs-cf-mode-help mgs-cf-full"><strong>URLs por gestor:</strong> cadastre ou altere em <a href="' . esc_url(admin_url('admin.php?page=' . self::MENU_SLUG . '-sms')) . '">MGS Chats → SMS</a>. Nenhuma URL é exposta na página pública.</div>';
        echo '</div></section>';

        echo '<section class="mgs-cf-section"><h3>4. Monetização e rastreamento</h3><div class="mgs-cf-fields mgs-cf-fields-compact">';
        $ad_domain_value = $this->clean_ad_slug($config['ad_domain'] ?? '', '');
        if ($ad_domain_value === '') {
            $ad_domain_value = $this->current_site_ad_slug();
        }
        $preview_config = array_merge($config, array(
            'ad_company' => $config['ad_company'] ?? 'digital-trust',
            'ad_domain' => $ad_domain_value,
        ));
        $ad_provider_preview = $this->ad_provider($preview_config);
        if ($ad_provider_preview === 'actview') {
            echo '<input type="hidden" name="ad_company" value="' . esc_attr($config['ad_company'] ?? 'digital-trust') . '">';
            echo '<input type="hidden" name="ad_domain" value="' . esc_attr($ad_domain_value) . '">';
            echo '<div class="mgs-cf-mode-help mgs-cf-full"><strong>Provider de anúncios: ActView / Zuout</strong><br><code>https://scr.actview.net/zuout.js</code><br><small>Zuout é exceção operacional: não usa wrapper JBF no chat ActView. O bloco de topo é <code>#zout_top_wrapper</code> contendo <code>#zout_top</code>.</small></div>';
        } else {
            $this->field_text('Company do wrapper', 'ad_company', $config['ad_company'] ?? 'digital-trust', 'Ex: digital-trust. Usado apenas para montar a URL do wrapper.');
            $this->field_text('Domain do wrapper', 'ad_domain', $ad_domain_value, 'Ex: openzed. Já vem preenchido com a slug do domínio atual.');
            if ($ad_provider_preview === 'm2') {
                $wrapper_preview = 'https://c.pubguru.net/pg.wantabrand.js';
                $wrapper_label = 'Script M2/PubGuru carregado:';
                $wrapper_help = 'No Wantabrand/M2, o trigger é a classe pg-rewarded e o bloco inline usa <pubguru data-pg-ad="wantabrand_mob_top">.';
            } else {
                $wrapper_preview = $this->ad_wrapper_url($preview_config);
                $wrapper_label = 'Wrapper carregado:';
                $wrapper_help = 'O plugin não configura auctions, rewarded ou interstitial. Isso fica 100% com o wrapper.';
            }
            echo '<div class="mgs-cf-mode-help mgs-cf-full"><strong>' . esc_html($wrapper_label) . '</strong><br><code>' . esc_html($wrapper_preview ?: 'Preencha o domain para gerar a URL do wrapper.') . '</code><br><small>' . esc_html($wrapper_help) . '</small></div>';
        }
        $this->field_checkbox('Página standalone (sem scripts globais do WordPress)', 'standalone', !empty($config['standalone']), 'Mantém somente o chat, GTM/Analytics e monetização configurados aqui.');
        $tracking_mode = $this->tracking_mode($config);
        $this->field_select('Modo de rastreamento', 'tracking_mode', $tracking_mode, array(
            'gtm' => 'Google Tag Manager (Analytics dentro do GTM)',
            'direct_ga4' => 'Google Analytics 4 direto (sem GTM)',
        ), 'Escolha uma fonte para evitar pageview duplicado.');
        $this->field_text('ID do Google Tag Manager', 'gtm_container_id', $this->gtm_container_id($config), 'Ex: GTM-K3V9CL5B. Usado quando o modo selecionado é Google Tag Manager.');
        $this->field_text('ID do Google Analytics 4', 'ga4_measurement_id', $this->ga4_measurement_id($config), 'Ex: G-499W6E48Z8. No modo GTM é referência do Analytics dentro do container; no modo GA4 direto é carregado pelo plugin.');
        if ($tracking_mode === 'direct_ga4') {
            $tracking_summary = 'Ativo: Google Analytics 4 direto ' . ($this->ga4_measurement_id($config) ?: '—') . '. O GTM não é carregado neste modo.';
        } else {
            $tracking_summary = 'Ativo: ' . ($this->gtm_container_id($config) ?: 'GTM não configurado') . ' → Analytics ' . ($this->ga4_measurement_id($config) ?: 'não informado') . ' dentro do container. O GA4 direto não é carregado.';
        }
        echo '<div class="mgs-cf-mode-help mgs-cf-full"><strong>Rastreamento carregado:</strong><br><code>' . esc_html($tracking_summary) . '</code></div>';
        $this->field_checkbox('Preservar UTMs nos links finais', 'utm_passthrough', !empty($config['utm_passthrough']), 'Mantém utm_source, utm_campaign, gclid, etc.');
        $this->field_text('Tags', 'tags', implode(', ', $config['tags'] ?? array()), 'Separadas por vírgula.');
        echo '</div></section>';

        $persona = $config['persona'] ?? array();
        echo '<section class="mgs-cf-section"><h3>5. Persona do atendente</h3><div class="mgs-cf-fields">';
        $this->field_textarea('Nomes possíveis', 'persona_names', implode("\n", $persona['names'] ?? array()), 'Um nome por linha.');
        $this->field_textarea('Nomes femininos', 'persona_female_names', implode("\n", $persona['female_names'] ?? array()), 'Usado para escolher foto feminina quando houver fotos configuradas.');
        $this->field_text('Cargo no header', 'persona_role', $persona['role'] ?? 'Consultor', 'Ex: Consultor de Empréstimo.');
        $this->field_text('Status', 'persona_status', $persona['status'] ?? '🟢 online agora', 'Ex: 🟢 online agora.');
        echo '</div></section>';

        $gate = $config['gate'] ?? array();
        echo '<section class="mgs-cf-section"><h3>6. Gate inicial</h3><div class="mgs-cf-fields">';
        $this->field_checkbox('Gate ativo', 'gate_enabled', !isset($gate['enabled']) || !empty($gate['enabled']), 'Mostra perguntas antes do chat.');
        $this->field_textarea('Perguntas do gate', 'gate_questions', $this->questions_to_text($gate['questions'] ?? array()), "Formato: Pergunta | resposta 1; resposta 2; resposta 3");
        $gate_questions_editor = isset($gate['questions']) && is_array($gate['questions']) ? array_values($gate['questions']) : array();
        $gate_question_2_enabled = !isset($gate_questions_editor[1]['enabled']) || !empty($gate_questions_editor[1]['enabled']);
        echo '<div class="mgs-cf-mode-help mgs-cf-full"><strong>Pergunta 1 é obrigatória</strong> e sempre aparece para iniciar o gate. A pergunta 2 pode ser ligada/desligada abaixo.</div>';
        $this->field_checkbox('Mostrar pergunta 2 do gate', 'gate_question_2_enabled', $gate_question_2_enabled, 'Desmarque para pular a segunda pergunta e ir direto para o loading/oferta encontrada.');
        $this->field_checkbox('Pular loading do gate', 'gate_skip_loading', !empty($gate['skip_loading']), 'Vai direto da última pergunta para o formulário/CTA.');
        $this->field_text('Texto de loading', 'gate_loading_text', $gate['loading_text'] ?? '', 'Ex: Buscando a melhor oferta...');
        $this->field_number('Tempo de loading (ms)', 'gate_loading_ms', $gate['loading_ms'] ?? 1800, 'Tempo antes do CTA.');
        $this->field_text('Ícone final', 'gate_final_icon', $gate['final_icon'] ?? '💬', 'Emoji ou texto curto.');
        $this->field_text('Título final', 'gate_final_title', $gate['final_title'] ?? 'Oferta encontrada!', 'Título antes do CTA.');
        $this->field_text('Subtítulo final', 'gate_final_subtitle', $gate['final_subtitle'] ?? '', 'Linha de apoio.');
        $this->field_text('Botão CTA', 'gate_cta_label', $gate['cta_label'] ?? 'VER OFERTAS →', 'Texto do botão que libera o chat.');
        $this->field_text('Nota de rodapé', 'gate_footer_note', $gate['footer_note'] ?? '', 'Opcional.');
        echo '</div></section>';

        $chat = $config['chat'] ?? array();
        echo '<section class="mgs-cf-section"><h3>7. Conversa do chat</h3><div class="mgs-cf-fields">';
        $this->field_textarea('Mensagens de abertura', 'chat_intro', implode("\n", $chat['intro'] ?? array()), 'Uma mensagem por linha. Use {botName} para o nome do atendente.');
        $this->field_textarea('Botões iniciais', 'chat_start_answers', implode("\n", $chat['start_answers'] ?? array()), 'Um botão por linha.');
        $this->field_textarea('Perguntas do chat', 'chat_questions', $this->questions_to_text($chat['questions'] ?? array()), "Formato: Pergunta | resposta 1; resposta 2; resposta 3");
        $offer_headline_parts = array_map('trim', explode('|', (string) ($chat['offer_headline'] ?? '')));
        $offer_found_message = $offer_headline_parts[0] ?? '🚗 Encontrei 3 ofertas exclusivas para você!';
        $offer_instruction_message = $offer_headline_parts[1] ?? 'Toque na que mais te interessa para ver as condições:';
        $this->field_text('Mensagem de busca antes das ofertas', 'chat_offer_search_message', $chat['pre_offer_messages'][0] ?? '🔍 Estou pesquisando as melhores condições para você...', 'Aparece depois da última resposta e antes dos cards.');
        $this->field_text('Mensagem “ofertas encontradas”', 'chat_offer_found_message', $offer_found_message, 'Primeira fala acima dos cards.');
        $this->field_text('Mensagem de instrução dos cards', 'chat_offer_instruction_message', $offer_instruction_message, 'Segunda fala acima dos cards.');
        echo '<input type="hidden" name="chat_pre_offer_messages" value="' . esc_attr(implode("\n", $chat['pre_offer_messages'] ?? array())) . '">';
        echo '<input type="hidden" name="chat_offer_headline" value="' . esc_attr($chat['offer_headline'] ?? '') . '">';
        echo '</div></section>';

        echo '<section class="mgs-cf-section"><h3>8. Ofertas finais</h3>';
        echo '<p class="description">Edite como gestor: cada oferta tem nome, URL, CTA e mensagens próprias. Sem pipe, sem formato técnico.</p>';
        $this->render_offer_fields($config['offers'] ?? array(), $mode);
        echo '</section>';

        echo '<p class="mgs-cf-sticky-save"><button type="submit" class="button button-primary button-hero">Salvar chat</button> ';
        if ($public_url) {
            echo '<a class="button button-hero" target="_blank" rel="noopener noreferrer" href="' . esc_url($public_url) . '">Abrir URL do chat</a> ';
        }
        echo '</p></form>';

        echo '<details class="mgs-cf-advanced"><summary>Avançado: editar JSON bruto</summary>';
        echo '<form method="post">';
        wp_nonce_field('mgs_cf_save', 'mgs_cf_nonce');
        echo '<input type="hidden" name="mgs_cf_action" value="save_raw">';
        echo '<textarea name="raw_json" class="mgs-cf-json" spellcheck="false">' . esc_textarea($raw) . '</textarea>';
        echo '<p><button type="submit" class="button">Salvar JSON bruto</button></p>';
        echo '</form></details>';

        if (!$is_new) {
            echo '<div class="mgs-cf-danger"><h3>Excluir chat</h3><p>Remove o arquivo de configuração deste chat. A URL deixa de responder por este funil.</p>';
            echo '<form method="post" onsubmit="return confirm(\'Excluir este chat definitivamente?\');">';
            wp_nonce_field('mgs_cf_save', 'mgs_cf_nonce');
            echo '<input type="hidden" name="mgs_cf_action" value="delete"><input type="hidden" name="id" value="' . esc_attr($id) . '">';
            echo '<button type="submit" class="button button-link-delete">Excluir ' . esc_html($id) . '</button></form></div>';
        }
    }

    private function render_duplicate_panel($configs, $selected_id) {
        echo '<h2>Duplicar chat</h2><p>Use isso para criar uma variação sem começar do zero. Você escolhe o nome e a pasta/URL que será criada.</p>';
        echo '<form method="post" class="mgs-cf-form"><section class="mgs-cf-section"><div class="mgs-cf-fields">';
        wp_nonce_field('mgs_cf_save', 'mgs_cf_nonce');
        echo '<input type="hidden" name="mgs_cf_action" value="duplicate">';
        echo '<label><span>Chat de origem</span><select name="source_id">';
        foreach ($configs as $id => $config) {
            echo '<option value="' . esc_attr($id) . '"' . selected($selected_id, $id, false) . '>' . esc_html($id . ' — ' . ($config['title'] ?? 'Sem título')) . '</option>';
        }
        echo '</select><small>O novo chat começa como cópia desse.</small></label>';
        $this->field_text('Novo nome / ID', 'new_id', '', 'Ex: EMP-BR-02 ou CAR-BR-BV-FIRST.');
        $this->field_text('Nova pasta / URL', 'new_route', '', 'Ex: /chat/emp/br2. Essa é a URL pública que o tráfego vai usar.');
        $this->field_text('Novo título interno', 'new_title', '', 'Ex: Chatbot Empréstimo Pessoal V2.');
        echo '</div><p><button type="submit" class="button button-primary button-hero">Duplicar e criar pasta</button></p></section></form>';
    }

    private function render_reports($configs) {
        $total = count($configs);
        $cards = 0;
        $seq = 0;
        foreach ($configs as $config) {
            $mode = $config['mode'] ?? ($config['chat']['offer_mode'] ?? 'cards');
            if ($mode === 'sequential') {
                $seq++;
            } else {
                $cards++;
            }
        }
        echo '<h2>Relatórios</h2><p>Visão operacional rápida dos chats configurados. Analytics de clique/evento pode ser plugado depois, mas aqui já fica o inventário de rotas e ofertas.</p>';
        echo '<div class="mgs-cf-report-cards"><div><strong>' . esc_html($total) . '</strong><span>Chats ativos</span></div><div><strong>' . esc_html($cards) . '</strong><span>Modo cards</span></div><div><strong>' . esc_html($seq) . '</strong><span>Modo sequencial</span></div></div>';
        echo '<table class="widefat striped mgs-cf-report-table"><thead><tr><th>Chat</th><th>Vertical</th><th>País</th><th>Modo</th><th>Ofertas</th><th>URL pública</th><th>Shortcode</th></tr></thead><tbody>';
        foreach ($configs as $id => $config) {
            $route = $config['route'] ?? '';
            $url = $route ? home_url('/' . trim($route, '/')) : '';
            echo '<tr><td><strong><a href="' . esc_url(admin_url('admin.php?page=' . self::MENU_SLUG . '&funnel=' . rawurlencode($id))) . '">' . esc_html($id) . '</a></strong><br><span>' . esc_html($config['title'] ?? '') . '</span></td>';
            echo '<td>' . esc_html($config['vertical'] ?? '') . '</td><td>' . esc_html($config['country'] ?? '') . '</td><td>' . esc_html($config['mode'] ?? '') . '</td><td>' . esc_html(count($config['offers'] ?? array())) . '</td>';
            echo '<td>' . ($url ? '<a target="_blank" rel="noopener noreferrer" href="' . esc_url($url) . '">' . esc_html($route) . '</a>' : '—') . '</td>';
            echo '<td><code>[mgs_chat_funnel id=&quot;' . esc_html($id) . '&quot;]</code></td></tr>';
        }
        echo '</tbody></table>';
    }

    private function field_text($label, $name, $value, $help = '', $extra = '') {
        echo '<label><span>' . esc_html($label) . '</span><input type="text" name="' . esc_attr($name) . '" value="' . esc_attr($value) . '" ' . esc_attr($extra) . '>'; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
        if ($help) {
            echo '<small>' . esc_html($help) . '</small>';
        }
        echo '</label>';
    }

    private function field_number($label, $name, $value, $help = '') {
        echo '<label><span>' . esc_html($label) . '</span><input type="number" name="' . esc_attr($name) . '" value="' . esc_attr($value) . '">';
        if ($help) {
            echo '<small>' . esc_html($help) . '</small>';
        }
        echo '</label>';
    }

    private function field_select($label, $name, $value, $options, $help = '') {
        echo '<label><span>' . esc_html($label) . '</span><select name="' . esc_attr($name) . '">';
        foreach ($options as $option_value => $option_label) {
            echo '<option value="' . esc_attr($option_value) . '" ' . selected((string) $value, (string) $option_value, false) . '>' . esc_html($option_label) . '</option>';
        }
        echo '</select>';
        if ($help) {
            echo '<small>' . esc_html($help) . '</small>';
        }
        echo '</label>';
    }

    private function field_textarea($label, $name, $value, $help = '') {
        echo '<label class="mgs-cf-full"><span>' . esc_html($label) . '</span><textarea name="' . esc_attr($name) . '" rows="5">' . esc_textarea($value) . '</textarea>';
        if ($help) {
            echo '<small>' . esc_html($help) . '</small>';
        }
        echo '</label>';
    }

    private function field_checkbox($label, $name, $checked, $help = '') {
        echo '<label class="mgs-cf-check"><input type="checkbox" name="' . esc_attr($name) . '" value="1" ' . checked($checked, true, false) . '><span>' . esc_html($label) . '</span>';
        if ($help) {
            echo '<small>' . esc_html($help) . '</small>';
        }
        echo '</label>';
    }

    private function render_offer_fields($offers, $mode) {
        $offers = array_values((array) $offers);
        if (empty($offers)) {
            $offers[] = array();
        }
        echo '<div class="mgs-cf-offer-editor" id="mgs-cf-offer-editor" data-mode="' . esc_attr($mode) . '">';
        foreach ($offers as $i => $offer) {
            $this->render_offer_row($offer, $mode, $i, false);
        }
        $this->render_offer_row(array(), $mode, '__INDEX__', true);
        echo '</div>';
        echo '<p><button type="button" class="button button-secondary" id="mgs-cf-add-offer">+ Adicionar oferta</button></p>';
        echo '<p class="description">A ordem aqui é a prioridade do funil. No modo sequencial, a oferta 1 aparece primeiro; se o usuário recusar, aparece a próxima.</p>';
        echo '<script>
        (function(){
          var editor=document.getElementById("mgs-cf-offer-editor");
          var btn=document.getElementById("mgs-cf-add-offer");
          if(!editor||!btn)return;
          function renumber(){
            var rows=editor.querySelectorAll(".mgs-cf-offer-row:not(.mgs-cf-template)");
            rows.forEach(function(row,i){
              var n=row.querySelector(".mgs-cf-offer-number"); if(n)n.textContent="Oferta "+(i+1);
            });
          }
          editor.addEventListener("click",function(e){
            if(e.target&&e.target.classList.contains("mgs-cf-remove-offer")){
              e.preventDefault();
              var row=e.target.closest(".mgs-cf-offer-row");
              if(row){row.remove(); renumber();}
            }
          });
          btn.addEventListener("click",function(e){
            e.preventDefault();
            var tpl=editor.querySelector(".mgs-cf-template"); if(!tpl)return;
            var clone=tpl.cloneNode(true);
            clone.classList.remove("mgs-cf-template");
            clone.style.display="";
            clone.innerHTML=clone.innerHTML.replace(/__INDEX__/g, String(Date.now()));
            editor.insertBefore(clone,tpl);
            renumber();
          });
        })();
        </script>';
    }

    private function render_offer_row($offer, $mode, $index, $template = false) {
        $has = !empty($offer['name']) || !empty($offer['target']);
        $classes = 'mgs-cf-offer-row' . ($has ? ' has-offer' : '') . ($template ? ' mgs-cf-template' : '');
        $style = $template ? ' style="display:none"' : '';
        $number = is_numeric($index) ? intval($index) + 1 : '__INDEX__';
        echo '<div class="' . esc_attr($classes) . '"' . $style . '>';
        echo '<div class="mgs-cf-offer-head"><strong class="mgs-cf-offer-number">Oferta ' . esc_html($number) . '</strong><button type="button" class="button-link-delete mgs-cf-remove-offer">Remover oferta</button></div>';
        echo '<div class="mgs-cf-fields">';
        echo '<label><span>Nome da oferta</span><input type="text" name="offer_name[]" value="' . esc_attr($offer['name'] ?? '') . '" placeholder="Volkswagen Polo, T-Cross, HB20..."><small>Nome que aparece no card ou na fala do consultor.</small></label>';
        if ($mode !== 'sequential') {
            echo '<label><span>URL final</span><input type="text" name="offer_target[]" value="' . esc_attr($offer['target'] ?? ($offer['url'] ?? '')) . '" placeholder="https://..."><small>Link final. UTMs são adicionadas automaticamente.</small></label>';
        } else {
            echo '<label><span>URL de destino</span><input type="text" name="offer_target[]" value="' . esc_attr($offer['target'] ?? '') . '" placeholder="https://..."><small>Link final. UTMs são adicionadas automaticamente.</small></label>';
        }
        if ($mode === 'sequential') {
            echo '<label><span>Botão aceitar</span><input type="text" name="offer_accept[]" value="' . esc_attr($offer['accept_label'] ?? 'Sim, quero conhecer →') . '"><small>CTA principal desta oferta.</small></label>';
            echo '<label><span>Botão recusar / próxima oferta</span><input type="text" name="offer_reject[]" value="' . esc_attr($offer['reject_label'] ?? '') . '" placeholder="Não, mostre outra opção"><small>Deixe vazio na última oferta.</small></label>';
            echo '<label class="mgs-cf-full"><span>Mensagens da oferta</span><textarea name="offer_messages[]" rows="4" placeholder="Uma mensagem por linha">' . esc_textarea(implode("\n", $offer['messages'] ?? array())) . '</textarea><small>Uma fala por linha. O chat mostra em sequência antes dos botões.</small></label>';
            echo '<input type="hidden" name="offer_subtitle[]" value=""><input type="hidden" name="offer_logo[]" value="">';
        } else {
            echo '<label><span>Texto abaixo do nome</span><input type="text" name="offer_subtitle[]" value="' . esc_attr($offer['subtitle'] ?? 'Ver oferta') . '" placeholder="Taxas a partir de 1,29% a.m."><small>Linha chamativa abaixo do nome do carro.</small></label>';
            echo '<label><span>Texto verde</span><input type="text" name="offer_bank[]" value="' . esc_attr($offer['bank'] ?? '') . '" placeholder="Financie pelo Banco BV"><small>Linha verde abaixo do texto chamativo.</small></label>';
            echo '<label><span>Imagem do carro</span><input type="text" name="offer_logo[]" value="' . esc_attr($offer['image'] ?? ($offer['logo'] ?? '')) . '" placeholder="https://.../carro.png"><small>URL da imagem exibida no card.</small></label>';
            echo '<input type="hidden" name="offer_accept[]" value=""><input type="hidden" name="offer_reject[]" value=""><input type="hidden" name="offer_messages[]" value="">';
        }
        echo '</div></div>';
    }

    private function parse_lines($text) {
        $lines = preg_split('/\r\n|\r|\n/', (string) $text);
        $out = array();
        foreach ($lines as $line) {
            $line = trim($line);
            if ($line !== '') {
                $out[] = $line;
            }
        }
        return $out;
    }

    private function parse_csv_text($text) {
        $parts = preg_split('/[,\n]+/', (string) $text);
        $out = array();
        foreach ($parts as $part) {
            $part = trim($part);
            if ($part !== '') {
                $out[] = $part;
            }
        }
        return $out;
    }

    private function parse_questions($text) {
        $lines = $this->parse_lines($text);
        $questions = array();
        foreach ($lines as $line) {
            $parts = array_map('trim', explode('|', $line, 2));
            $q = $parts[0] ?? '';
            $answers = isset($parts[1]) ? array_map('trim', explode(';', $parts[1])) : array('Continuar');
            $answers = array_values(array_filter($answers, function($v) { return $v !== ''; }));
            if ($q !== '') {
                $questions[] = array('text' => $q, 'answers' => $answers);
            }
        }
        return $questions;
    }

    private function questions_to_text($questions) {
        $lines = array();
        foreach ((array) $questions as $q) {
            $text = $q['text'] ?? ($q['question'] ?? '');
            $answers = array();
            foreach (($q['answers'] ?? array()) as $answer) {
                $answers[] = is_array($answer) ? ($answer['label'] ?? '') : $answer;
            }
            $lines[] = $text . ' | ' . implode('; ', array_filter($answers));
        }
        return implode("\n", $lines);
    }

    private function parse_offer_fields($post, $mode) {
        $names = isset($post['offer_name']) && is_array($post['offer_name']) ? $post['offer_name'] : array();
        $targets = isset($post['offer_target']) && is_array($post['offer_target']) ? $post['offer_target'] : array();
        $subtitles = isset($post['offer_subtitle']) && is_array($post['offer_subtitle']) ? $post['offer_subtitle'] : array();
        $logos = isset($post['offer_logo']) && is_array($post['offer_logo']) ? $post['offer_logo'] : array();
        $banks = isset($post['offer_bank']) && is_array($post['offer_bank']) ? $post['offer_bank'] : array();
        $accepts = isset($post['offer_accept']) && is_array($post['offer_accept']) ? $post['offer_accept'] : array();
        $rejects = isset($post['offer_reject']) && is_array($post['offer_reject']) ? $post['offer_reject'] : array();
        $messages = isset($post['offer_messages']) && is_array($post['offer_messages']) ? $post['offer_messages'] : array();
        $offers = array();
        $count = max(count($names), count($targets));
        for ($i = 0; $i < $count; $i++) {
            $name = sanitize_text_field(wp_unslash($names[$i] ?? ''));
            $target = esc_url_raw(wp_unslash($targets[$i] ?? ''));
            if ($name === '' || $target === '') {
                continue;
            }
            if ($mode === 'sequential') {
                $line_messages = $this->parse_lines(wp_unslash($messages[$i] ?? ''));
                $offers[] = array(
                    'name' => $name,
                    'messages' => !empty($line_messages) ? $line_messages : array($name),
                    'accept_label' => sanitize_text_field(wp_unslash($accepts[$i] ?? 'Sim, quero conhecer →')),
                    'reject_label' => sanitize_text_field(wp_unslash($rejects[$i] ?? '')),
                    'target' => $target,
                );
            } else {
                $offer = array(
                    'name' => $name,
                    'subtitle' => sanitize_text_field(wp_unslash($subtitles[$i] ?? 'Ver oferta')),
                    'target' => $target,
                );
                $bank = sanitize_text_field(wp_unslash($banks[$i] ?? ''));
                if ($bank !== '') {
                    $offer['bank'] = $bank;
                }
                $logo = esc_url_raw(wp_unslash($logos[$i] ?? ''));
                if ($logo !== '') {
                    $offer['image'] = $logo;
                    $offer['logo'] = $logo;
                }
                $offers[] = $offer;
            }
        }
        return $offers;
    }

    private function parse_offers($text, $mode) {
        $lines = $this->parse_lines($text);
        $offers = array();
        foreach ($lines as $line) {
            $parts = array_map('trim', explode('|', $line));
            if ($mode === 'sequential') {
                $name = $parts[0] ?? '';
                $target = $parts[1] ?? '';
                if ($name === '' || $target === '') {
                    continue;
                }
                $messages = isset($parts[4]) ? array_map('trim', explode(';', $parts[4])) : array($name);
                $offers[] = array(
                    'name' => $name,
                    'messages' => array_values(array_filter($messages, function($v) { return $v !== ''; })),
                    'accept_label' => $parts[2] ?? 'Sim, quero conhecer →',
                    'reject_label' => $parts[3] ?? '',
                    'target' => $target,
                );
            } else {
                $name = $parts[0] ?? '';
                $subtitle = $parts[1] ?? 'Ver oferta';
                $target = $parts[2] ?? '';
                if ($name === '' || $target === '') {
                    continue;
                }
                $offer = array('name' => $name, 'subtitle' => $subtitle, 'target' => $target);
                if (!empty($parts[3])) {
                    $offer['logo'] = $parts[3];
                }
                $offers[] = $offer;
            }
        }
        return $offers;
    }

    private function offers_to_text($offers, $mode) {
        $lines = array();
        foreach ((array) $offers as $offer) {
            if ($mode === 'sequential') {
                $messages = implode('; ', $offer['messages'] ?? array());
                $lines[] = implode(' | ', array($offer['name'] ?? '', $offer['target'] ?? '', $offer['accept_label'] ?? '', $offer['reject_label'] ?? '', $messages));
            } else {
                $lines[] = implode(' | ', array($offer['name'] ?? '', $offer['subtitle'] ?? '', $offer['target'] ?? '', $offer['logo'] ?? ''));
            }
        }
        return implode("\n", $lines);
    }

    private function strip_internal_config($config) {
        unset($config['_file']);
        return $config;
    }

    private function default_config() {
        return array(
            'id' => 'NOVO-BR-01',
            'vertical' => 'emp',
            'country' => 'br',
            'language' => 'pt-BR',
            'route' => '/chat/novo/br1',
            'title' => 'Novo Chat Funnel - MGS',
            'brand' => 'MGS',
            'theme' => 'whatsapp',
            'mode' => 'cards',
            'sms_enabled' => false,
            'sms_manager_code' => '',
            'sms_name_label' => 'Nome',
            'sms_phone_label' => 'Telefone',
            'sms_submit_label' => 'TRANSFERIR PARA ESPECIALISTA →',
            'sms_optional' => false,
            'sms_skip_label' => 'Pular, quero ver as ofertas',
            'sms_consent_enabled' => false,
            'sms_consent_default' => false,
            'sms_consent_label' => 'Aceito receber ofertas por SMS.',
            'sms_compact_gate' => false,
            'sms_form_intro' => 'Preencha seus dados e veja as parcelas:',
            'sms_gate_image' => '',
            'sms_gate_image_alt' => 'Financiamento de veículos',
            'geo_enabled' => false,
            'geo_fallback_text' => 'Analisando ofertas disponíveis na sua região',
            'geo_prefix_text' => 'Analisando ofertas de veículos em',
            'standalone' => false,
            'tracking_mode' => 'gtm',
            'gtm_container_id' => '',
            'ga4_measurement_id' => '',
            'ads_enabled' => true,
            'ad_company' => 'digital-trust',
            'ad_domain' => '',
            'utm_passthrough' => true,
            'tags' => array('br', 'rec'),
            'persona' => array('names' => array('Maria', 'João'), 'female_names' => array('Maria'), 'role' => 'Consultor', 'status' => '🟢 online agora'),
            'gate' => array('enabled' => true, 'questions' => array(array('text' => 'Qual opção você procura?', 'answers' => array('Opção 1', 'Opção 2'))), 'loading_text' => '🔍 Buscando a melhor oferta para você...', 'loading_ms' => 1800, 'final_icon' => '💬', 'final_title' => 'Oferta encontrada!', 'final_subtitle' => 'Um especialista foi identificado para te atender agora.', 'cta_label' => 'VER OFERTAS →'),
            'chat' => array('intro' => array('Olá! Eu sou {botName}.', 'Vou te ajudar a encontrar a melhor opção.'), 'start_answers' => array('✅ Vamos lá!'), 'questions' => array(), 'pre_offer_messages' => array('🔍 Estou pesquisando as melhores opções para você...'), 'offer_headline' => 'Encontrei opções para você!'),
            'offers' => array(array('name' => 'Oferta 1', 'subtitle' => 'Ver oferta', 'target' => 'https://example.com/')),
        );
    }

    private function admin_css() {
        echo '<style>
        .mgs-cf-admin{--mgs-blue:#155eef;--mgs-dark:#111827;--mgs-border:#d9e0ea;--mgs-bg:#f3f6fb}.mgs-cf-topbar{display:flex;justify-content:space-between;align-items:center;gap:20px;margin:10px 0 18px}.mgs-cf-topbar h1{margin-bottom:6px}.mgs-cf-topbar p{margin:0;color:#475467;font-size:14px}.mgs-cf-top-actions{display:flex;gap:8px;flex-wrap:wrap}.mgs-cf-admin-grid{display:grid;grid-template-columns:320px minmax(0,1fr);gap:18px;align-items:start}.mgs-cf-panel{background:#fff;border:1px solid var(--mgs-border);border-radius:14px;padding:18px;box-shadow:0 1px 2px rgba(16,24,40,.04)}.mgs-cf-main{padding:24px}.mgs-cf-sidebar h2{margin-top:0}.mgs-cf-side-buttons{display:flex;gap:8px;margin-bottom:14px}.mgs-cf-list{margin:0}.mgs-cf-list li{margin:0 0 8px}.mgs-cf-list a{display:block;padding:12px;border:1px solid #edf1f7;border-radius:10px;text-decoration:none;background:#fff}.mgs-cf-list .is-active a{background:#eef4ff;border-color:#84adff;box-shadow:inset 4px 0 0 var(--mgs-blue)}.mgs-cf-list strong{display:block;color:#111827;font-size:14px}.mgs-cf-list span{display:block;color:#475467;margin-top:2px}.mgs-cf-list em{display:block;color:#667085;font-size:12px;margin-top:6px;font-style:normal}.mgs-cf-edit-header{display:flex;justify-content:space-between;align-items:start;gap:20px;margin-bottom:14px}.mgs-cf-edit-header h2{margin:0}.mgs-cf-edit-header p{margin:6px 0 0;color:#667085}.mgs-cf-pills{display:flex;gap:8px;flex-wrap:wrap}.mgs-cf-pills span{background:#eef4ff;color:#155eef;border:1px solid #b2ccff;border-radius:999px;padding:6px 10px;font-weight:700;font-size:12px}.mgs-cf-meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:10px 0 20px;padding:14px;background:#f8fafc;border:1px solid #e4e7ec;border-radius:10px}.mgs-cf-meta span{min-width:0;overflow-wrap:anywhere}.mgs-cf-section{border:1px solid #e4e7ec;border-radius:14px;padding:18px;margin:0 0 18px;background:#fff}.mgs-cf-section h3{margin:0 0 14px;color:#111827}.mgs-cf-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.mgs-cf-fields-compact{grid-template-columns:repeat(3,minmax(0,1fr))}.mgs-cf-form label{display:flex;flex-direction:column;gap:6px}.mgs-cf-form label span{font-weight:700;color:#344054}.mgs-cf-form input[type=text],.mgs-cf-form input[type=number],.mgs-cf-form select,.mgs-cf-form textarea{width:100%;border:1px solid #d0d5dd;border-radius:10px;padding:10px 12px;max-width:none}.mgs-cf-form textarea{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;min-height:120px}.mgs-cf-form small{color:#667085}.mgs-cf-full{grid-column:1/-1}.mgs-cf-check{border:1px solid #e4e7ec;border-radius:10px;padding:12px;background:#f9fafb}.mgs-cf-check input{margin-right:8px}.mgs-cf-check{display:block!important}.mgs-cf-check span{display:inline!important}.mgs-cf-sticky-save{position:sticky;bottom:0;background:rgba(255,255,255,.96);padding:14px;border-top:1px solid #e4e7ec;margin:0 -24px -24px}.mgs-cf-advanced{margin-top:22px;border:1px solid #e4e7ec;border-radius:12px;padding:14px;background:#fcfcfd}.mgs-cf-json{width:100%;min-height:520px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px;line-height:1.45;margin-top:12px}.mgs-cf-danger{margin-top:18px;border:1px solid #fecdca;background:#fffbfa;border-radius:12px;padding:16px}.mgs-cf-danger h3{color:#b42318;margin-top:0}.mgs-cf-report-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:18px 0}.mgs-cf-report-cards div{padding:20px;border-radius:14px;background:#eef4ff;border:1px solid #b2ccff}.mgs-cf-report-cards strong{display:block;font-size:34px;color:#155eef}.mgs-cf-report-cards span{color:#344054}.mgs-cf-report-table td{vertical-align:top}.mgs-cf-offer-editor{display:flex;flex-direction:column;gap:16px}.mgs-cf-offer-row{border:1px solid #e4e7ec;border-radius:14px;padding:16px;background:#f9fafb}.mgs-cf-offer-row.has-offer{background:#fff;border-color:#b2ccff}.mgs-cf-offer-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.mgs-cf-offer-head strong{font-size:15px;color:#111827}.mgs-cf-offer-head span{font-size:12px;font-weight:700;color:#155eef;background:#eef4ff;border-radius:999px;padding:4px 9px}.mgs-cf-mode-help{background:#f8fafc;border:1px solid #d0d5dd;border-radius:10px;padding:12px;color:#344054;line-height:1.45}.mgs-cf-template{display:none!important}.mgs-cf-remove-offer{font-weight:700}.mgs-cf-offer-head .button-link-delete{margin-left:auto}@media(max-width:1100px){.mgs-cf-admin-grid,.mgs-cf-meta,.mgs-cf-fields,.mgs-cf-fields-compact,.mgs-cf-report-cards{grid-template-columns:1fr}.mgs-cf-topbar{align-items:flex-start;flex-direction:column}.mgs-cf-main{padding:16px}.mgs-cf-sticky-save{margin:0 -16px -16px}}
        </style>';
    }
}

MGS_Chat_Funnels::instance();
