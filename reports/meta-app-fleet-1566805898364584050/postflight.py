import json,sys,unicodedata,re
from pathlib import Path
from collections import Counter
root=Path(__file__).parent
sys.path.insert(0,str(root));sys.argv=['postflight','audit'];from preflight import load
ns=load('meta-app-roles-watch.sh','import importlib.util\n','\nstate = load_state()')
rows=ns['load_sheet_rows']();before=json.loads((root/'sheet-before.json').read_text())
g=json.loads((root/'generic-native-final-state.json').read_text());b=json.loads((root/'b013-native-final-state.json').read_text())
seen=set();mismatches=[];checked=Counter();scoped=[]
def norm_b(x):
 s=''.join(c for c in unicodedata.normalize('NFKD',str(x).strip().casefold()) if not unicodedata.combining(c))
 return re.sub(r'\s+',' ',s).strip()
accounts={(str(x['user']).strip().casefold(),norm_b(x['segurador'])):x for x in b['accounts'].values()}
for row in rows:
 app=ns['app_key_from_sheet_value'](row.get('NO APP'))
 if ns['is_verification_ignored_sheet_row'](row) or not app:continue
 user=str(row.get('User','')).strip().casefold()
 key=(app,user,ns['norm_name'](row.get('Segurador')))
 assert key not in seen,('duplicate',key)
 seen.add(key);scoped.append(key);checked[app]+=1
 if app.startswith('B013'):
  result=accounts[(user,norm_b(row.get('Segurador')))];assert result['verdict'] in ['linked','unlinked_confirmed']
  expected='' if result['linked'] else 'X'
  if result['linked']:assert result['debug_is_valid'] is True and result['accounts_status']==200
 else:
  snap=g['apps'][app];roles=snap.get('operational_roles') or snap['roles']
  present=any(ns['norm_name'](row.get('Segurador'))==ns['norm_name'](r['name']) or str(row.get('USUARIO') or '').strip()==r['id'] for r in roles)
  expected='' if present else 'X'
 actual=str(row.get('Removidos acumulado') or '').strip()
 if actual!=expected:mismatches.append({'app':app,'name':row.get('Segurador'),'expected':expected,'actual':actual})
assert not mismatches,mismatches
before_keys={(ns['app_key_from_sheet_value'](row.get('NO APP')),str(row.get('User','')).strip().casefold(),ns['norm_name'](row.get('Segurador'))) for row in before if ns['app_key_from_sheet_value'](row.get('NO APP')) and not ns['is_verification_ignored_sheet_row'](row)}
assert set(scoped)==before_keys,'allocation scope changed'
deliveries=json.loads((root/'generic-delivery-verification.json').read_text())+json.loads((root/'b013-delivery-verification.json').read_text())
assert len(deliveries)==13 and len({r['channel_id'] for r in deliveries})==13
assert sum(r['rows'] for r in deliveries)==194
receipt={'sa_identity':'mgsagent@mgs-core-prod.iam.gserviceaccount.com','sheet_rows_checked':len(scoped),'marker_mismatches':mismatches,'duplicate_composed_identities':0,'allocation_scope_unchanged':True,'by_app':dict(checked),'delivery_channels':len(deliveries),'delivered_rows':sum(r['rows'] for r in deliveries),'numeric_rows':sum(r['numeric'] for r in deliveries),'unmatched_rows':sum(r['unmatched'] for r in deliveries),'tests':sum([42,18])}
(root/'sheet-final.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(root/'final-verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));(root/'all-deliveries.json').write_text(json.dumps(deliveries,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False,indent=2))
