import json,re,unicodedata,sys
from decimal import Decimal
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).parent))
from preflight import load,ROOT
# Imported module only defines loaders; CLI branch is not run with mode audit.
def norm(value):
 s=unicodedata.normalize('NFKD',str(value).casefold());s=''.join(c for c in s if not unicodedata.combining(c));return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9]+',' ',s)).strip()
def money(value):
 if value is None:return 'n/d'
 return ('-' if value<0 else '')+'R$ '+f'{abs(value):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
def expected(names,source):
 keys=set()
 for name in names:
  keys.add(norm(name));keys.update(norm(x) for x in str(name).split('/'))
 vals=[Decimal(source[k]) for k in keys if k in source]
 return sum(vals,Decimal(0)) if vals else None
allrows=[]
phase=sys.argv[2] if len(sys.argv)>2 else 'before'
for mode,name,marker,stop in [('generic','meta-app-roles-watch.sh','import importlib.util\n','\nstate = load_state()'),('b013','b013-dtr-link-watch.sh','import asyncio\n',None)]:
 ns=load(name,marker,stop);ns['DRY_RUN']=True
 sourcefile=(mode+'-native-invest.json') if phase=='native' else (name+'.invest-after.json')
 data=json.loads((ROOT/sourcefile).read_text())['data'];ns['INVEST_3D_DATA']=data
 if mode=='generic':
  ns['load_sheet_users']()
  entries=[]
  if phase=='native':
   final=json.loads((ROOT/'generic-native-final-state.json').read_text())
   apps=[{**final['apps'][key], 'sheet_removed':ns['sheet_removed_roles_for_app'](key)} for key in ns['ACTIVE_APP_CONFIGS']]
  else:apps=json.loads((ROOT/'generic-preflight.json').read_text())
  for app in apps:
   for section in ['operational_roles','sheet_removed']:
    for role in app[section]:entries.append((app['app_name'],role['name'],ns['invest_profile_names'](role['name'],app['app_name']),section))
 else:
  state=json.loads((ROOT/('b013-native-final-state.json' if phase=='native' else 'b013-scheduled-audit.json')).read_text());entries=[]
  for row in state['accounts'].values():
   entries.append(('B013-7',row['segurador'],row.get('invest_profile_names') or [row['segurador']],'current' if row.get('linked') else 'removed'))
 for app,profile,names,section in entries:
  amounts={};actual={}
  for field,method in [('by_profile_today','format_invest_today'),('by_profile','format_invest_3d')]:
   value=expected(names,data[field]);exp=money(value)
   if mode=='generic':got=ns[method](profile,app_key=app)
   else:got=ns[method](profile,profile_names=names)
   assert got==exp,(app,profile,field,got,exp)
   amounts[field]=str(value) if value is not None else None;actual[field]=got
  allrows.append({'app':app,'name':profile,'aliases':names,'section':section,'amounts':amounts,'rendered':actual})
(ROOT/('investment-'+phase+'-row-audit.json')).write_text(json.dumps(allrows,ensure_ascii=False,indent=2))
summary={'rows':len(allrows),'by_app':dict(Counter(r['app'] for r in allrows)), 'numeric':sum(r['amounts']['by_profile'] is not None for r in allrows),'unmatched':[{'app':r['app'],'name':r['name']} for r in allrows if r['amounts']['by_profile'] is None]}
(ROOT/('investment-'+phase+'-row-summary.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
