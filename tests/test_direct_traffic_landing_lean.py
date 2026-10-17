import sys,json,unittest
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3.landing_lean import open_normal,close_normal,structured_visual
BASE={'pid':1,'window_id':10,'app_name':'chrome.exe'}
NEW={'pid':1,'window_id':11,'app_name':'chrome.exe'}
class Fake:
 def __init__(self,incognito=False,unloaded=False):self.calls=[];self.new=False;self.typed='';self.loaded=False;self.incognito=incognito;self.unloaded=unloaded
 def __call__(self,a):
  self.calls.append(a)
  if a['action']=='list_windows':return {'windows':[BASE]+([NEW] if self.new else [])}
  if a['action']=='key' and a['keys']=='ctrl+n':self.new=True
  if a['action']=='type':self.typed=a['text']
  if a['action']=='key' and a['keys']=='return':self.loaded=not self.unloaded
  if a['action']=='click':self.new=False
  if a['action']=='capture':return {'elements':[{'role':'Edit','label':self.typed},{'role':'Document','label':'Landing rendered' if self.loaded else 'New Tab'},{'role':'Button','label':'Incognito' if self.incognito else 'Profile'},{'index':1,'role':'Button','label':'Minimize','bounds':[100,0,40,40]},{'index':2,'role':'Button','label':'Restore','bounds':[140,0,40,40]},{'index':3,'role':'Button','label':'Close','bounds':[180,0,40,40]}]}
  return {'ok':True,'effect':'confirmed','elements':[{'index':40,'role':'Document','label':'Rendered landing','bounds':[0,121,2560,1271]}]}
class LeanTests(unittest.TestCase):
 def visual(self,**kw):
  d=dict(network_ad_visible=True,active_normal_chrome=True,unobstructed=True,landing_loaded=True,description='Capital One rendered artwork');d.update(kw);return {'success':True,'analysis':json.dumps(d)}
 def test_normal_not_incognito(self):
  f=Fake();p=open_normal(f,'https://example.invalid/x');self.assertEqual(p['browser_mode'],'NORMAL');self.assertIn({'action':'key','keys':'ctrl+n'},f.calls);self.assertFalse(any(a.get('keys')=='ctrl+shift+n' for a in f.calls))
 def test_close_has_no_capture_series(self):
  f=Fake();p=open_normal(f,'https://example.invalid/x');c=close_normal(f,p);self.assertTrue(c['tab_closed_verified']);self.assertFalse(any(a.get('mode')=='vision' for a in f.calls))
 def test_no_close_baseline(self):
  f=Fake();p=open_normal(f,'https://example.invalid/x');p['target']=BASE
  with self.assertRaises(AssertionError):close_normal(f,p)
 def test_reject_incognito(self):
  with self.assertRaises(ValueError):open_normal(Fake(incognito=True),'https://example.invalid/x')
 def test_newtab_not_noad(self):
  with self.assertRaisesRegex(ValueError,'technical failure'):open_normal(Fake(unloaded=True),'https://example.invalid/x')
 def test_typed_url_lag_rereads_without_duplicate_input(self):
  class Delayed(Fake):
   def __init__(self):super().__init__();self.pending_reads=0
   def __call__(self,a):
    out=super().__call__(a)
    if a['action']=='type':self.pending_reads=2
    if a['action']=='capture' and self.pending_reads:
     self.pending_reads-=1;out['elements'][0]['label']=self.typed[:-1]
    return out
  f=Delayed()
  with patch('ares_campaign_v3.landing_lean.time.sleep'):p=open_normal(f,'https://example.invalid/x?nocache')
  self.assertEqual(p['state'],'OPENED_NORMAL')
  self.assertEqual(sum(a['action']=='type' for a in f.calls),1)
  self.assertEqual(sum(a.get('keys')=='return' for a in f.calls),1)
 def test_typed_url_missing_never_submits(self):
  class Missing(Fake):
   def __call__(self,a):
    out=super().__call__(a)
    if a['action']=='capture':out['elements'][0]['label']='Address and search bar'
    return out
  f=Missing()
  with patch('ares_campaign_v3.landing_lean.time.sleep'):
   with self.assertRaisesRegex(ValueError,'Typed URL unverified'):open_normal(f,'https://example.invalid/x')
  self.assertFalse(any(a.get('keys')=='return' for a in f.calls))
 def test_navigation_loading_rereads_same_tab_without_more_enter(self):
  class Delayed(Fake):
   def __init__(self):super().__init__();self.pending_reads=0
   def __call__(self,a):
    out=super().__call__(a)
    if a.get('keys')=='return':self.pending_reads=2
    if a['action']=='capture' and self.pending_reads:
     self.pending_reads-=1;out['elements'][1]['label']='New Tab'
     out['elements'].append({'role':'Document','label':'Search icon'})
     out['elements'].append({'role':'Document','label':'chrome-untrusted://new-tab-page/'})
    return out
  f=Delayed()
  with patch('ares_campaign_v3.landing_lean.time.sleep'):p=open_normal(f,'https://example.invalid/x')
  self.assertEqual(p['state'],'OPENED_NORMAL')
  self.assertEqual(sum(a.get('keys')=='return' for a in f.calls),1)
 def test_native_close_lag_rereads_without_duplicate_click(self):
  class Delayed(Fake):
   def __init__(self):super().__init__();self.pending_close=0
   def __call__(self,a):
    out=super().__call__(a)
    if a['action']=='click':self.new=True;self.pending_close=2
    if a['action']=='list_windows' and self.pending_close:
     self.pending_close-=1
     if not self.pending_close:self.new=False;out={'windows':[BASE]}
    return out
  f=Delayed();p=open_normal(f,'https://example.invalid/x')
  with patch('ares_campaign_v3.landing_lean.time.sleep'):e=close_normal(f,p)
  self.assertTrue(e['tab_closed_verified'])
  self.assertEqual(sum(a['action']=='click' for a in f.calls),1)
 def test_native_close_never_repeats_input_when_window_stays(self):
  class Stuck(Fake):
   def __call__(self,a):
    out=super().__call__(a)
    if a['action']=='click':self.new=True
    return out
  f=Stuck();p=open_normal(f,'https://example.invalid/x')
  with patch('ares_campaign_v3.landing_lean.time.sleep'):
   with self.assertRaisesRegex(ValueError,'Closure uncertain'):close_normal(f,p)
  self.assertEqual(sum(a['action']=='click' for a in f.calls),1)
 def test_strict_visual_bools(self):
  with self.assertRaises(ValueError):structured_visual(self.visual(network_ad_visible='yes'))
 def test_visual_real_negative(self):self.assertFalse(structured_visual(self.visual(network_ad_visible=False,description='Loaded landing; no rendered ad'))['network_ad_visible'])
 def test_scroll_retargets_after_visual(self):
  from ares_campaign_v3.landing_lean import scroll_owned
  calls=[]
  def call(a):
   calls.append(a)
   if a['action']=='scroll':self.assertEqual(calls[-2]['action'],'capture');self.assertEqual(calls[-2]['window_id'],11)
   return {'ok':True,'effect':'confirmed','elements':[{'index':40,'role':'Document','label':'Rendered landing','bounds':[0,121,2560,1271]}]}
  scroll_owned(call,NEW);self.assertEqual([a['action'] for a in calls],['capture','scroll'])
 def test_scroll_escalates_only_after_refusal(self):
  from ares_campaign_v3.landing_lean import scroll_owned
  calls=[]
  def call(a):
   calls.append(a)
   if a['action']=='scroll' and 'delivery_mode' not in a:return {'ok':False,'code':'background_unavailable'}
   return {'ok':True,'effect':'confirmed','elements':[{'index':40,'role':'Document','label':'Rendered landing','bounds':[0,121,2560,1271]}]}
  scroll_owned(call,NEW);self.assertEqual(calls[-1]['delivery_mode'],'foreground');self.assertEqual(calls[-2]['action'],'capture')
 def test_scroll_never_masks_error(self):
  from ares_campaign_v3.landing_lean import scroll_owned
  with self.assertRaises(ValueError):scroll_owned(lambda a:{'ok':False},NEW)
 def test_visual_positive(self):self.assertTrue(structured_visual(self.visual())['network_ad_visible'])
class LeanValidationTests(unittest.TestCase):
 def setUp(self):
  self.patch=patch('ares_campaign_v3.landing_lean.lean_enabled',return_value=True);self.patch.start()
  self.scope=patch('ares_campaign_v3.landing_followup.scope',return_value=True);self.scope.start()
  self.e:dict=dict(observation_mode='LEAN_NORMAL_NEW_TAB',normal_opening=dict(browser_mode='NORMAL',new_tab_created=True,target=NEW,baseline=[BASE]),new_tab_identity=NEW,before_windows=[BASE,NEW],after_windows=[BASE],tab_closed_verified=True,other_tabs_preserved=True,opened_at=1,closed_at=30,observation_started_at=10,observation_ended_at=20,visible_seconds=10,observed_url='https://example.invalid/landing?utm_campaign=b01fb02c151&utm_adgroup=b01fb02c151g01',resolved_landing_url='https://example.invalid/landing?utm_campaign=b01fb02c151&utm_adgroup=b01fb02c151g01',mapping_source='offline unit fixture',network_ad_confirmed=True,visual=dict(network_ad_visible=True,active_normal_chrome=True,unobstructed=True,landing_loaded=True,description='Rendered network artwork'))
  self.e['normal_opening'].update(state='OPENED_NORMAL',url_submission_attempted=True,url=self.e['observed_url'])
  self.link=dict(effective_campaign_url='https://example.invalid/quiz/?utm_campaign=b01fb02c151&utm_adgroup=b01fb02c151g01')
 def tearDown(self):self.patch.stop();self.scope.stop()
 def validate(self):
  from ares_campaign_v3.landing_followup import validate_observation
  return validate_observation(self.e,self.link)
 def test_lean_pass_without_images(self):self.validate();self.assertNotIn('samples',self.e);self.assertNotIn('closed_screenshot',self.e)
 def test_reject_incognito(self):
  self.e['normal_opening']['browser_mode']='INCOGNITO'
  with self.assertRaises(ValueError):self.validate()
 def test_reject_reused_window(self):
  self.e['normal_opening']['baseline'].append(NEW)
  with self.assertRaises(ValueError):self.validate()
 def test_reject_unclosed(self):
  self.e['after_windows'].append(NEW)
  with self.assertRaises(ValueError):self.validate()
 def test_reject_short_dwell(self):
  self.e['visible_seconds']=9.99
  with self.assertRaises(ValueError):self.validate()
 def test_reject_nan_dwell(self):
  self.e['visible_seconds']=float('nan')
  with self.assertRaises(ValueError):self.validate()
 def test_loading_not_noad(self):
  self.e['visual']['landing_loaded']=False
  with self.assertRaises(ValueError):self.validate()
 def test_query_immutable(self):
  self.e['observed_url']=self.e['resolved_landing_url']=self.e['observed_url']+'&extra=mutated'
  with self.assertRaises(ValueError):self.validate()
 def test_negative_requires_actual_absence(self):
  from ares_campaign_v3.landing_lean import validate_lean_observation
  with self.assertRaises(ValueError):validate_lean_observation(self.e,self.link,negative=True)
  self.e['visual']['network_ad_visible']=False;self.e['network_ad_confirmed']=False
  validate_lean_observation(self.e,self.link,negative=True)
 def test_nocache_preserves_query_bytes(self):
  from ares_campaign_v3.landing_lean import observation_url
  u='https://example.invalid/landing?utm_campaign=b01fb02c151&x=%2F&utm_adgroup=b01fb02c151g01'
  self.assertEqual(observation_url(u),u+'&nocache');self.assertEqual(observation_url(u+'&nocache'),u+'&nocache')
 def test_nocache_separator_without_query(self):
  from ares_campaign_v3.landing_lean import observation_url
  self.assertEqual(observation_url('https://example.invalid/landing'),'https://example.invalid/landing?nocache')
 def test_nocache_not_last_utm_value(self):
  from ares_campaign_v3.landing_lean import tracking_query_matches
  q='utm_campaign=b01fb02c151&utm_adgroup=b01fb02c151g01'
  self.assertFalse(tracking_query_matches(q+'?nocache',q));self.assertFalse(tracking_query_matches(q+'&nocache=1',q));self.assertTrue(tracking_query_matches(q+'&nocache',q))
 def test_lean_pass_with_authorized_nocache(self):
  from ares_campaign_v3.landing_lean import observation_url
  original=self.link['effective_campaign_url'];self.e['observed_url']=self.e['resolved_landing_url']=observation_url(self.e['observed_url']);self.e['normal_opening']['url']=self.e['observed_url'];self.validate();self.assertEqual(self.link['effective_campaign_url'],original)
 def test_worker_active_route(self):
  from ares_campaign_v3.landing_followup import worker_prompt
  p=worker_prompt('key','owner',0,dict(state='RUNNING',payload={},links=[]))
  self.assertIn('ares-direct-traffic-lean-observe.py',p);self.assertNotIn('use-captured-samples',p)
if __name__=='__main__':unittest.main()
