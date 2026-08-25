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
            'index.php',
        ]
        self.assertTrue(all((ROOT / p).is_file() for p in required))

    def test_nested_manager_route_and_two_models_exist(self):
        php = read('includes/class-mgs-direct-quiz.php')
        self.assertIn(r'^quiz/([a-z]{2})/(quiz-g[0-9]{3,})/?$', php)
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
const source = 'https://yolokfx.com/quiz/us/quiz-g002/?utm_source=facebook&utm_medium=g002-s&utm_campaign=b02fb02c27&utm_adgroup=b02fb02c27g01&fbclid=TEST&custom_x=abc&page_id=99&p=5';
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

    def test_php_lint_all_plugin_files(self):
        for php in ROOT.rglob('*.php'):
            subprocess.check_call(['php', '-l', str(php)], stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    unittest.main()
