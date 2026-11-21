"""Offline boundary tests for isolated, authority-bound Page provisioning."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3.page_provisioning import ProvisioningBoundary, validate_grant, assignment_projection

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.grant = dict(enabled=True, account_id='2031917360813819', business_id='155263197283282', system_user_id='122095869861482193', approved_by='344196393512075265', source_message_id='1572711329905774673', source_channel_id='1548149654926135486', source_thread_id='1558131395451424890', initial_request_id='shein-1572705957413392539', approval_prompt_message_id='1572707253352538363')
        self.b = ProvisioningBoundary('571515486037700', self.grant)
    def test_valid_grant(self):
        validate_grant(self.grant, 'shein-1572705957413392539', '2031917360813819')
    def test_other_request(self):
        with self.assertRaises(ValueError): validate_grant(self.grant, 'other', '2031917360813819')
    def test_other_account(self):
        with self.assertRaises(ValueError): validate_grant(self.grant, 'shein-1572705957413392539', '99999')
    def test_disabled_grant(self):
        with self.assertRaises(ValueError): validate_grant({**self.grant, 'enabled':False}, 'shein-1572705957413392539', '2031917360813819')
    def test_read_page(self):
        self.b.check('GET', '571515486037700', {'fields':'id,name,business'})
    def test_other_page_denied(self):
        with self.assertRaises(ValueError): self.b.check('GET', '99999', {'fields':'id,name,business'})
    def test_discovery_denied(self):
        with self.assertRaises(ValueError): self.b.check('GET', 'me/accounts', {})
    def test_write_requires_fresh_intent(self):
        with self.assertRaises(ValueError): self.b.check('POST', '571515486037700/assigned_users', {'user':'122095869861482193','business':'155263197283282','tasks':'["ADVERTISE","ANALYZE"]'})
    def test_exact_union_only(self):
        self.b.arm([])
        self.b.check('POST', '571515486037700/assigned_users', {'user':'122095869861482193','business':'155263197283282','tasks':'["ADVERTISE","ANALYZE"]'})
        for change in [{'user':'99999'}, {'business':'99999'}, {'tasks':'["MANAGE"]'}, {'tasks':'["ADVERTISE"]'}, {'x':'1'}]:
            p={'user':'122095869861482193','business':'155263197283282','tasks':'["ADVERTISE","ANALYZE"]',**change}
            with self.assertRaises(ValueError): self.b.check('POST', '571515486037700/assigned_users', p)
    def test_existing_tasks_preserved(self):
        self.b.arm(['CREATE_CONTENT'])
        p={'user':'122095869861482193','business':'155263197283282','tasks':json.dumps(['ADVERTISE','ANALYZE','CREATE_CONTENT'])}
        self.b.check('POST', '571515486037700/assigned_users', p)
        p['tasks']='["ADVERTISE","ANALYZE"]'
        with self.assertRaises(ValueError): self.b.check('POST', '571515486037700/assigned_users', p)
    def test_paging_scope(self):
        self.b.check('GET', '571515486037700/assigned_users', {'business':'155263197283282','fields':'id,tasks','limit':100,'after':'cursor'})
        with self.assertRaises(ValueError): self.b.check('GET', '571515486037700/assigned_users', {'business':'99999','fields':'id,tasks','limit':100})
    def test_assignment_digest_order_and_privacy(self):
        rows=[{'id':'other','tasks':['MANAGE']},{'id':'122095869861482193','tasks':['ANALYZE','ADVERTISE']}]
        p=assignment_projection(rows,'122095869861482193')
        self.assertEqual(p['target_tasks'],['ADVERTISE','ANALYZE'])
        self.assertEqual(p,assignment_projection(rows[::-1],'122095869861482193'))
        self.assertNotIn('"other"',json.dumps(p))

if __name__=='__main__':unittest.main()
