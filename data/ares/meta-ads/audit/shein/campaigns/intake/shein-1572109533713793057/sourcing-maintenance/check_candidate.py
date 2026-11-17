import sys,json,pathlib,copy,importlib.util
from unittest.mock import patch
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import reviewed_copy_targeting as rt
from ares_campaign_v3.shein_continuation import validate_descriptor,APPROVED_RESUME
from ares_campaign_v3.shein_single_clone import verify_readback
from ares_campaign_v3.creative_copy_policy import effective
HERE=pathlib.Path(__file__).parent
f=json.loads(pathlib.Path('/root/.hermes/profiles/ares/cache/scratch/shein-1572109533713793057-semantic-fixture.json').read_text());s=f['state'];cp=f['checkpoint'];tree=f['tree']
d=json.loads(pathlib.Path('/root/mgs-agent/data/ares/meta-ads/audit/shein/campaigns/intake/shein-1572109533713793057/targeting-continuation.json').read_text())
v=validate_descriptor(d,s,cp)
modspec=importlib.util.spec_from_file_location('ares_campaign_v3.targeting_candidate',HERE/'reviewed_copy_targeting.candidate.py');cand=importlib.util.module_from_spec(modspec);modspec.loader.exec_module(cand)
ctx={'descriptor':d,'state':s,'checkpoint':cp,'verified':v};marker=APPROVED_RESUME.set(ctx);count=0
try:
 for ad in tree['ads']['data']:
  slot=next(z for z in s['manifest']['campaigns'][0]['ads'] if z['source_ad_id']==ad['source_ad_id']);ex=effective(slot['creative_payload']);ac=ad['creative']
  assert rt.preserved_sourcing(ac,ex) is not True;count+=1
  assert cand.preserved_sourcing(ac,ex) is True;count+=1
  mutations={
   'hash':lambda a:a['media_sourcing_spec']['images'][0].update(hash='bad'),
   'enrollment':lambda a:a['media_sourcing_spec']['images'][0].update(opt_in_status='opt_out'),
   'source':lambda a:a['media_sourcing_spec']['images'][0].update(source='multi_media'),
   'extra_key':lambda a:a['media_sourcing_spec']['images'][0].update(crop='bad'),
   'extra_image':lambda a:a['media_sourcing_spec']['images'].append(copy.deepcopy(a['media_sourcing_spec']['images'][0])),
   'missing_image':lambda a:a['media_sourcing_spec']['images'].pop(),
   'primary':lambda a:a['object_story_spec']['link_data'].update(image_hash='bad'),
   'page':lambda a:a['object_story_spec'].update(page_id='bad'),
   'feed':lambda a:a['asset_feed_spec']['bodies'][0].update(text='bad'),
   'tracking':lambda a:a.update(url_tags='utm_campaign=bad'),
  }
  for name,mut in mutations.items():
   z=copy.deepcopy(ac);mut(z);assert cand.preserved_sourcing(z,ex) is False,name;count+=1
  z=copy.deepcopy(ex);z['name']='changed';assert cand.preserved_sourcing(ac,z) is False;count+=1
  APPROVED_RESUME.reset(marker);assert cand.preserved_sourcing(ac,ex) is None;count+=1;marker=APPROVED_RESUME.set(ctx)
 with patch.object(rt,'preserved_sourcing',cand.preserved_sourcing):
  result=verify_readback(s['manifest'],s['source'],tree);count+=1
 print(json.dumps({'baseline_reproduced':True,'checks_passed':count,'semantic_qa_passed':True,'warnings':result,'meta_writes':0},ensure_ascii=False))
finally:APPROVED_RESUME.reset(marker)
