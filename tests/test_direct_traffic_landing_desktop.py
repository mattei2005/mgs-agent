"""Offline desktop fixtures, not real PC1 observations or timings."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3.landing_desktop import close_owned,open_owned

BASE={'pid':1,'window_id':10,'app_name':'chrome.exe'}
OWN={'pid':1,'window_id':20,'app_name':'chrome.exe'}
URL='https://example.invalid/rec-test/?utm_campaign=offline-fixture'


class Desktop:
    def __init__(self):self.items=[BASE.copy()];self.calls=[];self.typed=False;self.closed=False;self.refuse_close=False
    def __call__(self,args):
        self.calls.append(args.copy());action=args['action']
        if action=='list_windows':return {'windows':list(self.items)}
        if action=='capture':
            if args.get('app')=='screen':return {'screenshot_path':'OFFLINE-FIXTURE.png'}
            elements=[{'index':2,'role':'Button','label':'Close','bounds':[2514,0,46,40]}, {'index':8,'role':'Button','label':'Incognito','bounds':[0,50,90,30]}]
            if self.typed:elements.append({'index':9,'role':'Text','label':URL,'bounds':[0,60,600,30]})
            return {'elements':elements,'screenshot_path':'OFFLINE-OPEN.png'}
        if action=='key' and args['keys']=='ctrl+shift+n':
            if args.get('delivery_mode')!='foreground':return {'code':'background_unavailable'}
            self.items.append(OWN.copy());return {'effect':'unverifiable'}
        if action=='type':self.typed=True;return {'effect':'unverifiable'}
        if action=='key':return {'effect':'unverifiable'}
        if action=='click':
            if not self.refuse_close:self.items=[BASE.copy()];self.closed=True
            return {'effect':'unverifiable'}
        raise AssertionError(action)


class DesktopTests(unittest.TestCase):
    def proof(self):return {'new_window_created':True,'target':OWN.copy(),'baseline':[BASE.copy()]}
    def test_open_is_one_new_window_and_one_submission_after_real_readback(self):
        d=Desktop();saved=[];r=open_owned(d,URL,on_owned=lambda p:saved.append(p.copy()))
        self.assertEqual(r['state'],'OPENED_NOT_VISUALLY_VALIDATED')
        self.assertEqual(r['target']['window_id'],20);self.assertEqual(len(d.items),2)
        self.assertEqual(len([a for a in d.calls if a.get('keys')=='return']),1)
        self.assertEqual(len([a for a in d.calls if a.get('action')=='type']),1)
        self.assertTrue(saved[-1]['url_submission_attempted'])
        self.assertNotIn('network_ad_confirmed',r)
    def test_close_uses_one_fresh_native_caption_and_preserves_original(self):
        d=Desktop();d.items=[BASE.copy(),OWN.copy()];r=close_owned(d,self.proof(),True)
        self.assertEqual(r['state'],'CLOSED_NOT_PASS');self.assertEqual(d.items,[BASE])
        self.assertEqual([x for x in d.calls if x['action']=='click'],[{'action':'click','element':2}])
        self.assertTrue(r['tab_closed_verified']);self.assertNotIn('network_ad_confirmed',r)
    def test_baseline_window_never_closed(self):
        d=Desktop();p=self.proof();p['target']=BASE.copy()
        with self.assertRaisesRegex(ValueError,'baseline'):close_owned(d,p,True)
        self.assertFalse(any(x['action']=='click' for x in d.calls))
    def test_no_exclusive_review_no_close(self):
        d=Desktop()
        with self.assertRaisesRegex(ValueError,'review'):close_owned(d,self.proof())
        self.assertFalse(d.calls)
    def test_uncertain_close_has_no_retry(self):
        d=Desktop();d.items=[BASE.copy(),OWN.copy()];d.refuse_close=True
        with self.assertRaisesRegex(ValueError,'uncertain'):close_owned(d,self.proof(),True)
        self.assertEqual(len([x for x in d.calls if x['action']=='click']),1)
    def test_already_absent_is_readback_not_new_close_success(self):
        d=Desktop();r=close_owned(d,self.proof(),True)
        self.assertEqual(r['state'],'ALREADY_ABSENT_REVIEW_REQUIRED');self.assertFalse(r['close_input_sent'])
        self.assertFalse(any(x['action']=='click' for x in d.calls))
    def test_wrong_browser_cannot_be_closed(self):
        d=Desktop();d.items=[BASE.copy(),{**OWN,'app_name':'other.exe'}]
        with self.assertRaisesRegex(ValueError,'mismatch'):close_owned(d,self.proof(),True)
        self.assertFalse(any(x['action']=='click' for x in d.calls))
    def test_missing_native_close_fails_without_input(self):
        d=Desktop();d.items=[BASE.copy(),OWN.copy()]
        def call(a):
            if a['action']=='capture':return {'elements':[]}
            return d(a)
        with self.assertRaisesRegex(ValueError,'unique native'):close_owned(call,self.proof(),True)
        self.assertFalse(any(x['action']=='click' for x in d.calls))


if __name__=='__main__':unittest.main()
