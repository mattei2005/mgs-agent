"""Offline regression: visible SHEIN sequence has three digits."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3.shein_naming import campaign_name,product_label
from ares_campaign_v3 import shein_general
from ares_campaign_v3.prevalidation import validate_account_policy
from ares_campaign_v3.schema import Manifest
from test_shein_general_runtime import case
POLICY={'enabled':True,'route_regex':r'^/quiz/us/sh([123])-g[0-9]{3}/$','layout_version_map':{'1':'v1','2':'v2','3':'v3'}}

class PaddingTests(unittest.TestCase):
    def test_formatter_three_digits_preserves_remainder(self):
        for n,head in [(1,'001'),(7,'007'),(99,'099'),(100,'100'),(999,'999')]:
            with self.subTest(number=n):
                got=campaign_name(n,'2030-10-09T00:00:00-04:00','America/New_York','https://vizioid.com/quiz/us/sh3-g002/','FREE CLOTHES','COST_CAP','b01fb02c007',POLICY,copy_source_number=6)
                self.assertEqual(got,head+' - 09/10 - v3 - FREE CLOTHES - COCAP - (b01fb02c007) - COPY C6 - event_add_to_wishlist')

    def test_all_modes_use_padded_target_and_leave_source_untouched(self):
        for mode in ['pure_clone','clone_prestaged','from_zero_prestaged']:
            with self.subTest(mode=mode):
                r,s,a,_=case(1,mode=mode);a['shein_naming']=POLICY;before=copy.deepcopy(s)
                p=shein_general.build(r,s,7,a)
                self.assertTrue(p['campaigns'][0]['name'].startswith('007 - '));self.assertEqual(s,before)

    def test_legacy_short_source_still_parses(self):
        source='7 - 09/10 - v3 - FREE CLOTHES - COCAP - (b01fb02c007) - COPY C6 - event_add_to_wishlist'
        self.assertEqual(product_label(source),'FREE CLOTHES')
        self.assertEqual(product_label('00'+source),'FREE CLOTHES')

    def test_number_outside_three_digit_positive_range_rejected(self):
        for n in [0,-1,1000]:
            with self.subTest(number=n),self.assertRaises(ValueError):
                campaign_name(n,'2030-10-09T00:00:00-04:00','America/New_York','https://vizioid.com/quiz/us/sh3-g002/','FREE CLOTHES','COST_CAP','b01fb02c007',POLICY)

    def test_output_policy_rejects_unpadded_new_name(self):
        r,s,a,_=case(1);a['shein_naming']=POLICY
        a['campaign_policy']['name_regex']=r'[0-9]{3} - [0-9]{2}/[0-9]{2} - v[123] - .+ - (?:MAXVOL|COCAP|BIDCAP) - \(b[0-9]+fb[0-9]+c[0-9]+\)(?: - COPY C[0-9]+)? - event_add_to_wishlist'
        p=shein_general.build(r,s,7,a);validate_account_policy(Manifest.from_dict(p),{'accounts':{a['shein_profile']['account_id']:a}})
        p['campaigns'][0]['name']=p['campaigns'][0]['name'].replace('007 - ','7 - ',1)
        with self.assertRaises(ValueError):validate_account_policy(Manifest.from_dict(p),{'accounts':{a['shein_profile']['account_id']:a}})

if __name__=='__main__':unittest.main()
