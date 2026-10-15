"""Offline desktop fixtures, not real PC1 observations or timings."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ares_campaign_v3.landing_desktop import close_owned,open_owned,open_blank_owned

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


    def test_delayed_window_discovery_does_not_repeat_hotkey(self):
        d=Desktop();pending=False;reads=0
        def call(a):
            nonlocal pending,reads
            if a['action']=='key' and a['keys']=='ctrl+shift+n':
                d.calls.append(a.copy());pending=True;return {'effect':'unverifiable'}
            if a['action']=='list_windows' and pending:
                reads+=1
                if reads==3:d.items.append(OWN.copy())
            return d(a)
        r=open_owned(call,URL)
        self.assertEqual(r['target']['window_id'],20)
        self.assertEqual(len([a for a in d.calls if a.get('keys')=='ctrl+shift+n']),1)

    def test_nested_background_refusal_uses_verified_foreground_fallback(self):
        d=Desktop()
        def call(a):
            r=d(a)
            return {'verdict':r} if r.get('code')=='background_unavailable' else r
        r=open_owned(call,URL);self.assertEqual(r['target']['window_id'],20)
        self.assertEqual(len([a for a in d.calls if a.get('keys')=='ctrl+shift+n']),2)

    def test_blank_probe_never_types_or_submits_url_and_closes_own_window(self):
        d=Desktop();r=open_blank_owned(d);closed=close_owned(d,r,True)
        self.assertEqual(closed['state'],'CLOSED_NOT_PASS');self.assertEqual(d.items,[BASE])
        self.assertFalse(any(a['action']=='type' or a.get('keys')=='return' for a in d.calls))

    def test_partial_url_is_selected_before_foreground_replacement(self):
        d=Desktop();first=True
        def call(a):
            nonlocal first
            if a['action']=='type' and first:
                first=False;d.calls.append(a.copy());return {'effect':'suspected_noop'}
            return d(a)
        open_owned(call,URL)
        keys=[a.get('keys') for a in d.calls if a['action']=='key']
        self.assertIn('ctrl+l',keys);self.assertIn('ctrl+a',keys)
        self.assertEqual(keys.count('return'),1)

    def test_blank_chrome_tab_close_is_not_confused_with_window_caption_close(self):
        d=Desktop();d.items=[BASE.copy(),OWN.copy()]
        def call(a):
            r=d(a)
            if a['action']=='capture' and a.get('app')!='screen':
                r['elements'].extend([{'index':0,'role':'Button','label':'Minimize','bounds':[2423,0,45,40]},{'index':1,'role':'Button','label':'Restore','bounds':[2468,0,46,40]},{'index':54,'role':'Button','label':'Close','bounds':[242,6,28,28]}])
            return r
        r=close_owned(call,self.proof(),True);self.assertEqual(r['state'],'CLOSED_NOT_PASS')
        self.assertEqual([a['element'] for a in d.calls if a['action']=='click'],[2])


if __name__=='__main__':unittest.main()
