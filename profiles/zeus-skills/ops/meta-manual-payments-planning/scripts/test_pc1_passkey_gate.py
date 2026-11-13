#!/usr/bin/env python3
"""Offline gate tests: never import or execute a PC1 worker's side effects."""
import ast
from pathlib import Path
import re
import unittest

S = Path(__file__).resolve().parent


class PasskeyGateTests(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse((S / 'read_pc1_accounts_list.py').read_text())
        fn = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'gate')
        self.ns = {'re': re}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<gate-only>', 'exec'), self.ns)

    def check(self, text):
        self.ns['text'] = text
        return self.ns['gate']()

    def test_real_ax_passkey_copy_without_heading(self):
        with self.assertRaisesRegex(RuntimeError, 'facebook_passkey_reauthentication_required'):
            self.check("Rodolfo Mattei • Facebook\nIf you don't have a passkey for Facebook on this device, you can try another way.\nTry another way\nContinue")

    def test_reauth_route(self):
        with self.assertRaisesRegex(RuntimeError, 'facebook_passkey_reauthentication_required'):
            self.check('business.facebook.com/security/twofactor/reauth/')

    def test_accounts_remains_allowed(self):
        self.check('Billing & payments\nAccounts\nSearch\nOutstanding balance')

    def test_native_gate_remains_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'native_auth_surface_conflict'):
            self.check('Windows Security')

    def test_provider_gate_remains_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'provider_or_auth_gate'):
            self.check('You are temporarily blocked')

    def test_history_preinput_and_wait_gates_match_passkey(self):
        tree = ast.parse((S / 'read_pc1_billing_history.py').read_text())
        patterns = [n.args[0].value for n in ast.walk(tree)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'search' and n.args
                    and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, str)
                    and 'If you don.t have a passkey for Facebook' in n.args[0].value]
        self.assertEqual(len(patterns), 2)
        for pattern in patterns:
            self.assertRegex("If you don't have a passkey for Facebook on this device", re.compile(pattern, re.I))
            self.assertRegex('business.facebook.com/security/twofactor/reauth/', re.compile(pattern, re.I))


if __name__ == '__main__':
    unittest.main()
