import json
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path('/root/.hermes/profiles/zeus/scripts/b013-dtr-link-watch.sh')


def load_monitor_module():
    text = SCRIPT.read_text(encoding='utf-8')
    start = text.index('import asyncio\n')
    end = text.rindex('\nPY\n')
    namespace = {'__name__': 'b013_monitor_test'}
    exec(compile(text[start:end], str(SCRIPT), 'exec'), namespace)
    return SimpleNamespace(**namespace)


class B013ProfileRemovalAlertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_monitor_module()

    def missing(self, user='one@example.com', consecutive=1):
        return {
            'user': user,
            'segurador': user.split('@')[0],
            'verdict': 'unknown',
            'link_status': 'not_found_in_dtr_switcher',
            'error': 'account_not_found_in_dtr_switcher',
            'consecutive_unknown': consecutive,
        }

    def technical(self, user, consecutive=2):
        return {
            'user': user,
            'segurador': user.split('@')[0],
            'verdict': 'unknown',
            'link_status': 'debug_token_check_failed',
            'error': {'code': 190, 'message': 'Invalid OAuth access token'},
            'consecutive_unknown': consecutive,
        }

    def technical_deleted(self, user, consecutive=2):
        row = self.technical(user, consecutive=consecutive)
        row['error'] = {
            'code': 190,
            'type': 'OAuthException',
            'message': 'Error validating application. Application has been deleted.',
        }
        return row

    def test_first_verified_absence_stays_inconclusive_without_restriction(self):
        current = self.missing(consecutive=0)
        previous = {'link_status': 'linked', 'consecutive_unknown': 0}
        result = self.mod.classify_account_result(current, previous)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertEqual(result['link_status'], 'not_found_in_dtr_switcher')
        self.assertEqual(result['consecutive_profile_absent'], 1)
        self.assertEqual(self.mod.restriction_unknown_candidates([result]), [])

    def test_second_verified_absence_becomes_normal_profile_removal(self):
        current = self.missing(consecutive=0)
        previous = {
            'link_status': 'not_found_in_dtr_switcher',
            'verdict': 'unknown',
            'consecutive_profile_absent': 1,
            'consecutive_unknown': 1,
        }
        result = self.mod.classify_account_result(current, previous)
        self.assertEqual(result['verdict'], 'unlinked_confirmed')
        self.assertEqual(result['link_status'], 'profile_removed_from_dtr')
        self.assertEqual(result['consecutive_profile_absent'], 2)
        self.assertEqual(result['consecutive_unknown'], 0)

    def test_legacy_missing_counter_migrates_without_extra_delay(self):
        current = self.missing(consecutive=0)
        previous = {
            'link_status': 'not_found_in_dtr_switcher',
            'verdict': 'unknown',
            'consecutive_unknown': 2,
        }
        result = self.mod.classify_account_result(current, previous)
        self.assertEqual(result['verdict'], 'unlinked_confirmed')
        self.assertEqual(result['consecutive_profile_absent'], 3)

    def test_missing_profiles_never_form_restriction_candidate(self):
        rows = [self.missing(f'{i}@example.com', consecutive=4) for i in range(5)]
        self.assertEqual(self.mod.restriction_unknown_candidates(rows), [])

    def test_restriction_candidate_requires_three_independent_logins(self):
        two = [self.technical(f'{i}@example.com') for i in range(2)]
        three = [self.technical(f'{i}@example.com') for i in range(3)]
        self.assertEqual(self.mod.restriction_unknown_candidates(two), [])
        self.assertEqual(len(self.mod.restriction_unknown_candidates(three)), 3)

    def test_duplicate_login_does_not_satisfy_app_wide_floor(self):
        rows = [self.technical('same@example.com') for _ in range(3)]
        self.assertEqual(self.mod.restriction_unknown_candidates(rows), [])

    def test_sheet_scope_removal_retires_state_silently(self):
        accounts = {
            'kept': {'user': 'kept@example.com'},
            'planned': {'user': 'planned@example.com'},
        }
        retired = self.mod.retire_out_of_scope_accounts(accounts, {'kept'})
        self.assertEqual([row['user'] for row in retired], ['planned@example.com'])
        self.assertEqual(set(accounts), {'kept'})

    def test_source_replaces_account_snapshot_and_classifies_downstream(self):
        source = SCRIPT.read_text(encoding='utf-8')
        self.assertNotIn('prev.update(r)', source)
        self.assertIn("accounts_state[key] = {**r, 'last_seen_at': now_iso()}", source)
        append_at = source.index('classified_results.append(r)')
        replace_at = source.index('results = classified_results')
        summarize_at = source.index('summary = summarize(results)')
        self.assertLess(append_at, replace_at)
        self.assertLess(replace_at, summarize_at)

    def test_automatic_alert_keeps_current_sheet_scoped_confirmed_removals(self):
        changes = [{
            'user': 'new@example.com',
            'segurador': 'New',
            'old': 'not_monitored',
            'new': 'linked',
            'kind': 'added',
        }]
        current_failure = {
            'user': 'old@example.com',
            'segurador': 'Old',
            'profile_id': 'old.profile',
            'pages': '2',
            'verdict': 'unlinked_confirmed',
        }
        without_current_removal = '\n'.join(
            self.mod.automatic_movement_sections(changes, [], [])
        )
        self.assertNotIn('REMOVIDOS CONFIRMADOS', without_current_removal)
        self.assertNotIn('Old', without_current_removal)

        with_current_removal = '\n'.join(
            self.mod.automatic_movement_sections(changes, [current_failure], [])
        )
        self.assertIn('REMOVIDOS CONFIRMADOS', with_current_removal)
        self.assertEqual(with_current_removal.count('Old'), 1)

    def test_reassigned_removal_is_absent_from_later_report(self):
        accounts = {
            'kept': {'user': 'kept@example.com', 'verdict': 'unlinked_confirmed'},
            'reassigned': {'user': 'moved@example.com', 'verdict': 'unlinked_confirmed'},
        }
        self.mod.retire_out_of_scope_accounts(accounts, {'kept'})
        current_failures = [row for row in accounts.values() if row.get('verdict') == 'unlinked_confirmed']
        rendered = '\n'.join(self.mod.automatic_movement_sections([], current_failures, []))
        self.assertIn('kept', rendered)
        self.assertNotIn('moved', rendered)

    def test_confirmation_probe_requires_two_fresh_app_deleted_responses(self):
        rows = [self.technical_deleted(f'{i}@example.com') for i in range(3)]
        calls = []

        def fake_graph(path, params, token):
            calls.append((path, params, token))
            return 400, {}, {
                'error': {
                    'code': 190,
                    'type': 'OAuthException',
                    'message': 'Error validating application. Application has been deleted.',
                }
            }

        result = self.mod.restriction_confirmation_probe(
            {'app_id': '123', 'app_secret': 'test-secret'}, rows, graph_call=fake_graph
        )
        self.assertEqual(result['status'], 'confirmed_not_false_positive')
        self.assertEqual(result['independent_bot_logins'], 3)
        self.assertEqual([c[0] for c in calls], ['/123', '/123/roles'])
        self.assertTrue(all(c['application_deleted'] for c in result['checks']))

    def test_confirmation_probe_stays_inconclusive_if_one_route_recovers(self):
        rows = [self.technical_deleted(f'{i}@example.com') for i in range(3)]

        def fake_graph(path, params, token):
            if path.endswith('/roles'):
                return 200, {}, {'data': []}
            return 400, {}, {
                'error': {
                    'code': 190,
                    'message': 'Error validating application. Application has been deleted.',
                }
            }

        result = self.mod.restriction_confirmation_probe(
            {'app_id': '123', 'app_secret': 'test-secret'}, rows, graph_call=fake_graph
        )
        self.assertEqual(result['status'], 'inconclusive')

    def test_confirmation_probe_requires_independent_bot_logins(self):
        rows = [self.technical_deleted('same@example.com') for _ in range(3)]
        result = self.mod.restriction_confirmation_probe(
            {'app_id': '123', 'app_secret': 'test-secret'}, rows,
            graph_call=lambda *args: self.fail('Graph must not run below the evidence floor'),
        )
        self.assertEqual(result['status'], 'inconclusive')
        self.assertEqual(result['independent_bot_logins'], 1)

    def test_confirmation_embed_states_not_false_positive(self):
        embed = self.mod.confirmed_restriction_embed(
            'B013-4', {'independent_bot_logins': 20}
        )
        rendered = json.dumps(embed, ensure_ascii=False)
        self.assertIn('Não é falso positivo', rendered)
        self.assertIn('ALERTA CONFIRMADO', embed['title'])

    def test_possible_alert_precedes_automatic_confirmation_in_source(self):
        source = SCRIPT.read_text(encoding='utf-8')
        possible_post = source.index("embed = possible_restriction_embed(config['app_name']")
        confirmation_probe = source.index('confirmation = restriction_confirmation_probe(config, restriction_unknowns)')
        self.assertLess(possible_post, confirmation_probe)


if __name__ == '__main__':
    unittest.main()
