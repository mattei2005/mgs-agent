import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path('/root/mgs-agent/plugins/mgs-direct-quiz')


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


class DirectQuizContractTests(unittest.TestCase):
    def test_plugin_contract_files_exist(self):
        required = [
            'mgs-direct-quiz.php',
            'includes/class-mgs-direct-quiz.php',
            'templates/landing.php',
            'assets/direct-quiz.css',
            'assets/direct-quiz.js',
            'assets/admin.css',
            'assets/admin.js',
            'index.php',
        ]
        self.assertTrue(all((ROOT / p).is_file() for p in required))

    def test_nested_manager_route_and_two_models_exist(self):
        php = read('includes/class-mgs-direct-quiz.php')
        self.assertIn(r'^quiz/([a-z]{2})/(sh[12]-g[0-9]{3,})/?$', php)
        self.assertIn("'lp1'", php)
        self.assertIn("'lp2'", php)
        self.assertIn('admin_post_mgs_dq_duplicate', php)
        self.assertIn('admin_post_mgs_dq_save', php)

    def test_admin_writes_are_capability_and_nonce_protected(self):
        php = read('includes/class-mgs-direct-quiz.php')
        self.assertGreaterEqual(php.count("current_user_can( 'manage_options' )"), 2)
        self.assertIn("check_admin_referer( 'mgs_dq_save' )", php)
        self.assertIn("check_admin_referer( 'mgs_dq_duplicate_'", php)
        self.assertNotIn('admin_post_mgs_dq_delete', php)

    def test_public_surface_has_no_lead_sms_or_tracking_logic(self):
        public = '\n'.join([
            read('templates/landing.php'),
            read('assets/direct-quiz.js'),
        ]).lower()
        forbidden = ['<form', 'fetch(', 'xmlhttprequest', 'smsfunnel', 'phone', 'fbq(', 'datalayer', 'gtag(']
        self.assertEqual([], [x for x in forbidden if x in public])
        self.assertIn('data-mgs-dq-cta', public)

    def test_query_merge_preserves_direct_traffic_params_exactly_once(self):
        js = ROOT / 'assets/direct-quiz.js'
        code = r'''
const m = require(process.argv[1]);
const source = 'https://yolokfx.com/quiz/us/sh2-g002/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b02fb02c27&utm_adgroup=b02fb02c27g01&fbclid=TEST&custom_x=abc&page_id=99&p=5';
const dest = m.mergeUrl('https://yolokfx.com/rec-us-app-shein-circle-of-style/?utm_source=fixed', source);
console.log(JSON.stringify({dest}));
'''
        out = subprocess.check_output(['node', '-e', code, str(js)], text=True)
        dest = json.loads(out)['dest']
        self.assertTrue(dest.startswith('https://yolokfx.com/rec-us-app-shein-circle-of-style/'))
        self.assertEqual(1, dest.count('utm_source='))
        self.assertIn('utm_source=fixed', dest)
        for pair in [
            'utm_medium=g002-s',
            'utm_campaign=b02fb02c27',
            'utm_adgroup=b02fb02c27g01',
            'fbclid=TEST',
            'custom_x=abc',
        ]:
            self.assertIn(pair, dest)
            self.assertEqual(1, dest.count(pair))
        self.assertNotIn('page_id=', dest)
        self.assertIsNone(re.search(r'[?&]p=', dest))

    def test_mobile_card_has_explicit_viewport_safe_width(self):
        css = read('assets/direct-quiz.css')
        self.assertIn('width:calc(100vw - 28px)!important', css)
        self.assertIn('max-width:400px!important', css)

    def test_shein_slug_matches_selected_layout(self):
        php = read('includes/class-mgs-direct-quiz.php')
        self.assertIn("$expected_slug = 'sh' . substr( $layout, 2 ) . '-' . strtolower( $manager )", php)
        self.assertIn("'/^sh[12]-g[0-9]{3,}$/'", php)
        self.assertIn('sh2-g002', php)
        self.assertIn('sh1-g002', php)
        self.assertNotIn('quiz-v2-g002', php)

    def test_unknown_manager_route_is_forced_to_real_404(self):
        php = read('includes/class-mgs-direct-quiz.php')
        self.assertIn("$wp_query->set_404()", php)
        self.assertIn("get_404_template()", php)
        self.assertIn("status_header( 404 )", php)

    def test_admin_interface_has_scoped_polished_components(self):
        php = read('includes/class-mgs-direct-quiz.php')
        css = read('assets/admin.css')
        self.assertIn("add_action( 'admin_enqueue_scripts'", php)
        self.assertIn("wp_enqueue_style( 'mgs-dq-admin'", php)
        for marker in [
            'mgs-dq-admin',
            'mgs-dq-hero',
            'mgs-dq-stats',
            'mgs-dq-panel',
            'mgs-dq-badge',
            'mgs-dq-form-grid',
            'mgs-dq-form-card',
            'mgs-dq-actions',
        ]:
            self.assertIn(marker, php)
            self.assertIn('.' + marker, css)
        self.assertIn('Landing Pages SHEIN', php)
        self.assertIn('Duplicar', php)
        self.assertIn("wp_enqueue_media()", php)
        self.assertIn("wp_enqueue_script( 'mgs-dq-admin'", php)
        self.assertIn('mgs-dq-logo-picker', php)
        self.assertIn('mgs-dq-logo-preview', php)
        admin_js = read('assets/admin.js')
        self.assertIn('wp.media', admin_js)
        self.assertIn('mgs-dq-select-logo', admin_js)
        self.assertIn('mgs-dq-remove-logo', admin_js)
        self.assertIn('@media (max-width: 782px)', css)

    def test_php_lint_all_plugin_files(self):
        for php in ROOT.rglob('*.php'):
            subprocess.check_call(['php', '-l', str(php)], stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    unittest.main()
