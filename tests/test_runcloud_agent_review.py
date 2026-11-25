import copy
import datetime as dt
import importlib.util
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('review', '/root/mgs-agent/scripts/runcloud-agent-review.py')
assert spec is not None and spec.loader is not None
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.g = {'installed':'2.21.0','candidate':'2.21.0','services':{'nginx':'active'},'vendor_repository':True}
        self.a = {'online':True,'connected':True,'agentVersion':'2.21.0'}
    def test_current(self):
        self.assertEqual(r.classify(self.g,self.a),'current_validated')
    def test_update_is_critical_not_install(self):
        self.g['candidate']='2.22.0'
        self.assertEqual(r.classify(self.g,self.a),'update_pending_critical_confirmation')
    def test_disconnected_not_healthy(self):
        self.a['connected']=False
        self.assertEqual(r.classify(self.g,self.a),'provider_integration_unverified')
    def test_provider_unavailable(self):
        self.assertEqual(r.classify(self.g,None),'provider_integration_unverified')
    def test_service_failure(self):
        self.g['services']['nginx']='inactive'
        self.assertEqual(r.classify(self.g,self.a),'service_health_failure')
    def test_boundary_and_overdue(self):
        s={'next_review_date':'2026-12-10'}
        self.assertFalse(r.due(s,dt.date(2026,12,9)))
        self.assertTrue(r.due(s,dt.date(2026,12,10)))
        self.assertTrue(r.due(s,dt.date(2026,12,11)))
    def test_partial_hosts_preserved(self):
        def guest(t):
            if t[0]=='Inc02': raise TimeoutError()
            return copy.deepcopy(self.g)
        with patch.object(r,'guest',side_effect=guest),patch.object(r,'provider',return_value={t[0]:self.a for t in r.TARGETS}),patch.object(r.time,'sleep'):
            result=r.collect()
        self.assertFalse(result['overall'])
        self.assertEqual(result['targets']['Inc01']['status'],'current_validated')
        self.assertEqual(result['targets']['Inc02']['status'],'collection_unavailable')
        self.assertFalse(result['installs'])
    def test_embedded_payload_compiles(self):
        compile(r.PAYLOAD,'remote','exec')
    def test_not_due_has_no_external_reads(self):
        with patch.object(r,'credential',side_effect=AssertionError('unexpected credential')):
            self.assertFalse(r.due({'next_review_date':'2999-12-10'},dt.date(2026,11,25)))

if __name__=='__main__': unittest.main()
