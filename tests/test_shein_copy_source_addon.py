"""COPY source label is an add-on before the event, not product text."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3.shein_naming import campaign_name,product_label

POLICY={'route_regex':r'^/quiz/us/sh([123])-g[0-9]{3}/$','layout_version_map':{'1':'v1','2':'v2','3':'v3'}}

class CopyAddonTests(unittest.TestCase):
    def test_copy_source_before_event(self):
        got=campaign_name(120,'2030-10-09T00:00:00-04:00','America/New_York','https://yolokfx.com/quiz/us/sh2-g002/','FREE CLOTHES','LOWEST_COST_WITHOUT_CAP','b01fb01c120',POLICY,copy_source_number=67)
        self.assertEqual(got,'120 - 09/10 - v2 - FREE CLOTHES - MAXVOL - (b01fb01c120) - COPY C67 - add_to_wishlist')
        self.assertEqual(product_label(got),'FREE CLOTHES')

    def test_from_zero_without_copy_source_keeps_base_format(self):
        got=campaign_name(125,'2030-10-09T00:00:00-04:00','America/New_York','https://yolokfx.com/quiz/us/sh3-g002/','FREE CLOTHES','COST_CAP','b01fb01c125',POLICY)
        self.assertNotIn('COPY',got)

if __name__=='__main__':unittest.main()
