"""OFFLINE: Meta destination fields are not site-administration targets."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_shein_cross_account_reference import fixture
from ares_campaign_v3 import shein_reference as ref, shein_single_clone as driver

class DestinationTests(unittest.TestCase):
    def test_external_destination_literal_not_required_to_match_account_site(self):
        r,s,a,assets,cfg=fixture(5,2)
        r['website_url']=r['website_url'].replace('escalatepower.com','destination.example')
        p=copy.deepcopy(a['shein_profile']);sp=a['shein_reference_profile'];before=copy.deepcopy(r)
        resolved=ref.target_profile(r,p,sp,{'enabled':True,'approved_by':ref.RODOLFO})
        self.assertEqual(r,before)
        self.assertEqual(resolved['destination_base'],r['website_url'].split('?',1)[0])

    def test_explicit_campaign_destination_never_calls_domain_checker(self):
        r,_,a,_,_=fixture(5,2)
        r['website_url']=r['website_url'].replace('escalatepower.com','destination.example')
        with patch('subprocess.run',side_effect=AssertionError('domain checker must not run')):
            driver.validate_request_destinations(r,a['shein_profile'])

    def test_malformed_or_embedded_credentials_rejected(self):
        for value in ('javascript:alert(1)','https:///missing','https://user:secret@destination.example/x','https://destination.example:bad/x','https://destination.example/\npath'):
            with self.subTest(value=value),self.assertRaises(ValueError):ref.validate_destination(value)

    def test_https_and_http_return_without_normalization(self):
        for value in ('https://destination.example/x/?utm_campaign=Exact001','http://destination.example:8080/x?x=One%2FTwo'):
            parsed=ref.validate_destination(value)
            self.assertEqual(parsed.hostname,'destination.example')

    def test_legacy_nonexplicit_destination_retains_domain_scope_gate(self):
        from types import SimpleNamespace
        with patch('subprocess.run',return_value=SimpleNamespace(returncode=3)) as checker:
            with self.assertRaises(driver.RouteBlocked):driver.validate_request_destinations({}, {'destination_base':'https://operation.example/'})
            self.assertEqual(checker.call_count,1)

if __name__=='__main__':unittest.main()
