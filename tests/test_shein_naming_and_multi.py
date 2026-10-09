"""Offline naming and Multi-advertiser preservation regressions."""
import copy,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_shein_general_runtime import case
from ares_campaign_v3 import shein_general as compiler
from ares_campaign_v3.creative_media import creative_body,matches

class NamingAndMultiTests(unittest.TestCase):
    def fixture(self):
        r,s,a,_=case(1)
        a['pure_clone_setup_policy']='PRESERVE_SOURCE_DEFINITION'
        a['shein_naming']={'enabled':True,'route_regex':r'^/quiz/us/sh([123])-g[0-9]{3}/$','layout_version_map':{'1':'v1','2':'v2','3':'v3'}}
        cr=s['ads'][0]['creative'];cr['instagram_user_id']='ig-source';cr['contextual_multi_ads']={'enroll_status':'OPT_OUT'}
        return r,s,a

    def test_exact_layout_and_source_opt_out_preserved(self):
        r,s,a=self.fixture();p=compiler.build(r,s,120,a);c=p['campaigns'][0]
        self.assertEqual(c['name'],'120 - 08/10 - v2 - PRODUCT - MAXVOL - (b01fb02c120) - COPY C110 - event_add_to_wishlist')
        cp=c['ads'][0]['creative_payload'];self.assertEqual(cp['contextual_multi_ads'],{'enroll_status':'OPT_OUT'})
        self.assertIn('contextual_multi_ads',creative_body(cp))
        actual=copy.deepcopy(cp);actual['instagram_user_id']='ig-source';self.assertTrue(matches(actual,cp))
        actual.pop('contextual_multi_ads');self.assertFalse(matches(actual,cp))

    def test_new_style_source_does_not_duplicate_quiz_bid_date(self):
        r,s,a=self.fixture();s['campaign']['name']='110 - 07/10 - v2 - PRODUCT - MAXVOL - (b01fb02c110) - event_add_to_wishlist'
        c=compiler.build(r,s,120,a)['campaigns'][0]
        self.assertEqual(c['name'],'120 - 08/10 - v2 - PRODUCT - MAXVOL - (b01fb02c120) - COPY C110 - event_add_to_wishlist')

    def test_bid_cap_name_never_contains_cap_amount(self):
        r,s,a=self.fixture();s['campaign']['bid_strategy']='LOWEST_COST_WITH_BID_CAP';s['campaign']['name']=s['campaign']['name'].replace('PRODUCT','PRODUCT BID 1.10 [LP NORMAL]')
        self.assertEqual(compiler.build(r,s,120,a)['campaigns'][0]['name'],'120 - 08/10 - v2 - PRODUCT - BIDCAP - (b01fb02c120) - COPY C110 - event_add_to_wishlist')

    def test_unknown_quiz_route_blocks_instead_of_guessing(self):
        r,s,a=self.fixture();a['shein_naming']['route_regex']=r'^/quiz/us/verified-other-route/$'
        with self.assertRaises(ValueError):compiler.build(r,s,120,a)

if __name__=='__main__':unittest.main()
