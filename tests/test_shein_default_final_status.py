"""Default final status is corporate SHEIN policy; no real Meta writes."""
import unittest
from unittest.mock import patch
import test_shein_single_clone_route as legacy
from ares_campaign_v3 import shein_single_clone as route

POLICY={'operation_id':'SHEIN-US-DIRECT','request_defaults':{'final_status':'ACTIVE','authority':'344196393512075265','scope':'new_creation_requests_only'}}

class DefaultStatusTests(unittest.TestCase):
    def test_missing_status_uses_approved_active_default_without_mutating_input(self):
        r={'request_id':'example'};resolved=route.apply_request_defaults(r,POLICY)
        self.assertEqual(resolved['status'],'ACTIVE');self.assertNotIn('status',r)

    def test_explicit_paused_keeps_pause(self):
        self.assertEqual(route.apply_request_defaults({'status':'PAUSED'},POLICY)['status'],'PAUSED')

    def test_missing_policy_never_implies_active(self):
        with self.assertRaises(ValueError):route.apply_request_defaults({}, {'operation_id':'SHEIN-US-DIRECT'})

class EntryPointTests(legacy.PipelineTests):
    def test_omitted_status_is_resolved_at_real_entrypoint_before_internal_validation(self):
        self.request.pop('status')
        op=self.root/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json'
        import json
        op.write_text(json.dumps(POLICY))
        with patch.object(route,'_run_bound_request',return_value={'status':'OFFLINE_CAPTURE'}) as bound:
            route.run_request(self.request)
        self.assertEqual(bound.call_args.args[0]['status'],'ACTIVE')
        self.engine.execute.assert_not_called()

for name in legacy.PipelineTests.__dict__:
    if name.startswith('test_'):setattr(EntryPointTests,name,None)

if __name__=='__main__':unittest.main()
