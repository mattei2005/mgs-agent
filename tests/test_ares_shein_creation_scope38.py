"""Scope38, multi-account cells and validation side-effect regressions."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_ares_shein_creation_daily as base


class Scope38Tests(unittest.TestCase):
    def test_extra_accounts_sum_into_existing_cells(self):
        s=base.snapshot()
        for a in s['accounts']: a['campaigns']=[{'id':a['account_id']}]
        c=base.m.aggregate(s,base.policy)
        self.assertEqual(c['observed_total'],38)
        self.assertEqual(next(r for r in c['rows'] if r['code']=='G002')['cells']['Yolokfx'],2)
        self.assertEqual(next(r for r in c['rows'] if r['code']=='G006')['cells']['Yolokfx'],2)
        self.assertEqual(c['site_totals']['Yolokfx'],8)
        self.assertIn('38/38 contas',base.m.render(s,base.policy))

    def test_extra_account_incomplete_makes_entire_cell_unknown(self):
        s=base.snapshot()
        next(a for a in s['accounts'] if a['account_id']=='1492168699397108')['complete']=False
        c=base.m.aggregate(s,base.policy)
        self.assertIsNone(next(r for r in c['rows'] if r['code']=='G002')['cells']['Yolokfx'])
        self.assertIsNone(c['site_totals']['Yolokfx'])
        self.assertIn('37/38',base.m.render(s,base.policy))

    def test_missing_snapshot_account_is_not_zero(self):
        s=base.snapshot();s['accounts'].pop()
        with self.assertRaisesRegex(AssertionError,'INCOMPLETE_SNAPSHOT_SCOPE'): base.m.aggregate(s,base.policy)

    def test_duplicate_account_rejected(self):
        s=base.snapshot();s['accounts'][-1]=copy.deepcopy(s['accounts'][0])
        with self.assertRaisesRegex(AssertionError,'DUPLICATE_SNAPSHOT_ACCOUNT'): base.m.aggregate(s,base.policy)

    def test_duplicate_campaign_rejected(self):
        s=base.snapshot()
        s['accounts'][0]['campaigns']=[{'id':'duplicate'}];s['accounts'][1]['campaigns']=[{'id':'duplicate'}]
        with self.assertRaisesRegex(AssertionError,'DUPLICATE_CAMPAIGN_ID'): base.m.aggregate(s,base.policy)

    def resolve_with_catalog(self, transform):
        real=base.m.load
        catalog=base.m.BASE/base.policy['catalog']
        changed=copy.deepcopy(real(catalog));transform(changed['accounts'])
        def load(p):return changed if Path(p)==catalog else real(p)
        with patch.object(base.m,'load',side_effect=load),patch.object(base.m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{"allowed":true}')):
            return base.m.resolve(base.policy)

    def test_exact_approved_selection_passes(self):
        self.assertEqual(len(self.resolve_with_catalog(lambda a:None)),38)

    def test_same_count_replacement_fails_closed(self):
        def change(a):a[0]['account_id']='9999999999999999'
        with self.assertRaisesRegex(AssertionError,'UNAPPROVED_CATALOG_DRIFT'):self.resolve_with_catalog(change)

    def test_new_39th_account_fails_closed(self):
        def change(a):a.append(dict(a[0],account_id='9999999999999999'))
        with self.assertRaisesRegex(AssertionError,'CATALOG_CARDINALITY_DRIFT'):self.resolve_with_catalog(change)

    def test_rebinding_manager_fails_closed(self):
        def change(a):a[0]['manager_code']='G006'
        with self.assertRaisesRegex(AssertionError,'UNAPPROVED_CATALOG_DRIFT'):self.resolve_with_catalog(change)

    def test_validate_live_never_calls_sheet_or_discord_post(self):
        m=base.m;s=base.snapshot()
        transport=SimpleNamespace(Discord=lambda:SimpleNamespace(verify=lambda x:{'ok':True}))
        collector=SimpleNamespace(collect=lambda:s)
        args=SimpleNamespace(scheduled=False,publish_test=False,validate_live=True)
        with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/zeus/cache/scratch') as temp:
            with patch.object(m,'STATE',Path(temp)),patch.object(m,'load',return_value=base.policy),patch.object(m,'resolve',return_value=[]),patch.object(m,'module',return_value=transport),patch.object(m,'Collector',return_value=collector),patch.object(m,'update_creation_sheet') as sheet,patch.object(m,'deliver') as deliver,patch('builtins.print'):
                self.assertEqual(m.main(args),0)
                sheet.assert_not_called();deliver.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
