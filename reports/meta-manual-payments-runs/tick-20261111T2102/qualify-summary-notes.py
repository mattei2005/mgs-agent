import sys,shutil,json,fcntl,os
from pathlib import Path
from datetime import datetime
B=Path(__file__).parent
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
sys.path.insert(0,'/root/mgs-agent/scripts');import mgs_google_workspace_auth as g
H=Path('/root/mgs-agent/data/meta-manual-payments')
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600)
c=json.loads((H/'digital-trust-workbook-contract.json').read_text());cl=json.loads((B/'closure-current.json').read_text());assert cl['fresh_h_count']==0 and cl['fresh_metrics_count']==47
with (H/'writer.lock').open('a')as f:
 fcntl.flock(f,fcntl.LOCK_EX)
 g.load_env();t=g.service_account_access_token();u='https://sheets.googleapis.com/v4/spreadsheets/'+c['spreadsheet_id']
 code,old=g.api_json('GET',u+'?includeGridData=true',t,quota_project='mgs-core-prod');assert code==200
 save(B/'notes-before.json',old)
 sh=next(s for s in old['sheets']if s['properties']['sheetId']==c['sheet_id']);req=[];changes=[]
 periods='; '.join(p['since']+' a '+p['until']for p in cl['average_period'])
 for i,row in enumerate(sh['data'][0]['rowData']):
  cs=row.get('values',[]);v=cs[0].get('userEnteredValue',{}).get('stringValue','')if cs else''
  if not v.startswith('TOTAL'):continue
  gn='Soma das médias diárias por conta. Três dias completos no fuso Meta de cada conta: '+periods+'. Atualização API '+cl['validated_metrics_at']+'. Não confundir com cobrança ou saldo.'
  hn='H mantém leituras históricas Accounts de '+cl['h_read_at_min']+' a '+cl['h_read_at_max']+'. Neste tick: 0 leituras novas; 36 preservadas por PC1 offline. Current balance da lista Accounts; não é modal Pay now nem limite do cartão. Fonte e hora individuais nas contas.'
  for col,note in [(6,gn),(7,hn)]:
   if col==7 and 'CARTÃO' in v:continue
   if len(cs)<=col:continue
   changes.append({'row':i,'col':col,'note':note})
   req.append({'updateCells':{'range':{'sheetId':c['sheet_id'],'startRowIndex':i,'endRowIndex':i+1,'startColumnIndex':col,'endColumnIndex':col+1},'rows':[{'values':[{'note':note}]}],'fields':'note'}})
 assert len(req)==5
 code,result=g.api_json('POST',u+':batchUpdate',t,{'requests':req},quota_project='mgs-core-prod');assert code==200
 code,new=g.api_json('GET',u+'?includeGridData=true',t,quota_project='mgs-core-prod');assert code==200;save(B/'notes-after.json',new)
 # Compare every authored cell and all sheet metadata, allowing only five planned notes.
 import copy
 expected=copy.deepcopy(old)
 es=next(s for s in expected['sheets']if s['properties']['sheetId']==c['sheet_id'])
 for x in changes:es['data'][0]['rowData'][x['row']]['values'][x['col']]['note']=x['note']
 def authored(book):
  out=copy.deepcopy(book)
  for s in out['sheets']:
   for grid in s.get('data',[]):
    for r in grid.get('rowData',[]):
     for cell in r.get('values',[]):
      for k in list(cell):
       if k not in ['userEnteredValue','note','userEnteredFormat','textFormatRuns']:cell.pop(k)
  return out
 assert authored(expected)==authored(new),'notes_only_parity_failed'
 save(B/'notes-receipt.json',{'status':'notes_only_exact_readback','changed_notes':changes,'values_formulas_formatting_preserved':True,'other_tabs_preserved':True,'payments':0,'meta_writes':0,'verified_at':datetime.now().astimezone().isoformat()})
 print(json.dumps({'status':'notes_only_exact_readback','notes_updated':len(changes),'values_formulas_formatting_preserved':True,'other_tabs_preserved':True}))
