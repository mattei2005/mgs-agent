import json,sys,asyncio,os
from pathlib import Path
ROOT=Path('/root/.hermes/profiles/zeus/cache/scratch/meta-fleet-20261102')
mode=sys.argv[1];name='meta-app-roles-watch.sh' if mode=='generic' else 'b013-dtr-link-watch.sh'
s=(Path('/root/.hermes/profiles/zeus/scripts')/name).read_text()
marker='import importlib.util\n' if mode=='generic' else 'import asyncio\n'
body=s[s.index(marker):s.rindex('\nPY\n')]
if mode=='generic':prefix,tail=body.split('\nstate = load_state()',1)
else:prefix,tail=body,None
ns={'__name__':'native_observer'};exec(compile(prefix,name,'exec'),ns)
assert not ns['DRY_RUN']
assert ns['FORCE_LIVE_ALERT']
observed=[]
def save_observation():
 (ROOT/(mode+'-native-observed.json')).write_text(json.dumps(observed,ensure_ascii=False,indent=2))
original_loader=ns['load_invest_3d']
def loader():
 payload=original_loader()
 (ROOT/(mode+'-native-invest.json')).write_text(json.dumps({'data':payload,'error':ns['INVEST_3D_ERROR'],'attempts':ns['INVEST_3D_ATTEMPTS']},ensure_ascii=False,indent=2))
 return payload
ns['load_invest_3d']=loader
original_blocks=ns['post_code_blocks']
def blocks(*args,**kwargs):
 if mode=='generic':app=kwargs.get('app_name');text=args[0]
 else:app=args[0]['app_name'];text=args[1]
 observed.append({'kind':'table','app':app,'text':text});save_observation()
 return original_blocks(*args,**kwargs)
ns['post_code_blocks']=blocks
original_card=ns['post_webhook'] if mode=='generic' else ns['post_discord']
def card(*args,**kwargs):
 if mode=='generic':app=kwargs.get('app_name');embed=args[1] if len(args)>1 else kwargs.get('embed')
 else:app=args[0]['app_name'];embed=args[2] if len(args)>2 else kwargs.get('embed')
 if embed:observed.append({'kind':'embed','app':app,'embed':embed});save_observation()
 return original_card(*args,**kwargs)
ns['post_webhook' if mode=='generic' else 'post_discord']=card
original_save=ns['save_state']
def save(state):
 original_save(state)
 (ROOT/(mode+'-native-final-state.json')).write_text(json.dumps(state,ensure_ascii=False,indent=2))
 print(json.dumps({'mode':mode,'updated_at':state.get('_updated_at'),'summary':state.get('_last_run_summary')},ensure_ascii=False),flush=True)
ns['save_state']=save
if mode=='generic':exec(compile('\nstate = load_state()'+tail,name,'exec'),ns)
else:asyncio.run(ns['main']())
(ROOT/(mode+'-native-completed.json')).write_text(json.dumps({'status':'completed','observed_calls':len(observed)}))
