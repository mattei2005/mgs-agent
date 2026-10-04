"""Native monitor source tests, synthetic HTTP only; never close real incidents."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('ack_monitor', Path('/root/mgs-agent/scripts/monitor-sb-messenger-token-invalid.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class AckAuthorizationTests(unittest.TestCase):
    def run_source(self, users, members=None, reaction=True, failure=None):
        calls = []
        members = members or {}
        def request(method, path, body=None, allow_404=False):
            calls.append(path)
            if '/reactions/' in path:
                if failure:
                    return failure, {}
                return 200, users
            if '/members/' in path:
                return 200, members.get(path.rsplit('/', 1)[-1], {'roles': []})
            return 200, {'id': '111', 'channel_id': '123', 'reactions': [{'emoji': {'name': '✅'}, 'count': len(users)}] if reaction else []}
        with patch.object(mod, 'discord_request', request):
            result = mod.message_has_resolution_reaction('123', '111')
        return result, calls
    def test_unknown_person_does_not_ack(self):
        self.assertFalse(self.run_source([{'id':'900','bot':False}])[0])
    def test_bot_does_not_ack(self):
        self.assertFalse(self.run_source([{'id':mod.RODOLFO_ID,'bot':True}])[0])
    def test_rodolfo_can_ack(self):
        self.assertTrue(self.run_source([{'id':mod.RODOLFO_ID,'bot':False}])[0])
    def test_existing_team_role_can_ack(self):
        self.assertTrue(self.run_source([{'id':'900','bot':False}], {'900': {'roles':[mod.TEAM_ROLE_IDS[0]]}})[0])
    def test_unrelated_role_cannot_ack(self):
        self.assertFalse(self.run_source([{'id':'900','bot':False}], {'900': {'roles':['1234']}})[0])
    def test_no_reaction_does_not_request_reactors(self):
        result, calls = self.run_source([], reaction=False)
        self.assertFalse(result)
        self.assertEqual(len(calls), 1)
    def test_reactor_http_failure_does_not_ack(self):
        with self.assertRaises(RuntimeError):
            self.run_source([{'id':'900','bot':False}], failure=503)
    def test_rodolfo_on_later_page(self):
        calls=[]
        first=[{'id':str(1000+i),'bot':False} for i in range(100)]
        def request(method,path,body=None,allow_404=False):
            calls.append(path)
            if '/reactions/' in path:
                return 200, [{'id':mod.RODOLFO_ID,'bot':False}] if 'after=' in path else first
            if '/members/' in path:
                return 200, {'roles':[]}
            return 200, {'id':'111','channel_id':'123','reactions':[{'emoji':{'name':'✅'},'count':101}]}
        with patch.object(mod,'discord_request',request):
            self.assertTrue(mod.message_has_resolution_reaction('123','111'))
        self.assertTrue(any('after=1099' in x for x in calls))

if __name__ == '__main__': unittest.main()
