import json,re
from pathlib import Path
from datetime import datetime
R=Path(__file__).parent
load=lambda p:json.loads(p.read_text())
q=load(R/'request.json');cap=load(R/'sb-visible-rps-capture.json')
assert cap['complete'] and cap['identity_Ares_visible'] and cap['currency']=='USD' and cap['data_date']==q['date'] and cap['pages'][-1]['end']==cap['pages'][-1]['total']
ui={(x['ACCOUNT_ID'].removeprefix('act_'),x['CAMPAIGN_ID']) for x in cap['rows']}
ids=[];checks=[]
for b in q['bindings']:
 p=R/b['account_id'];m=load(p/'model.json');parts=load(p/'report.parts.json');selected=load(p/'selected.json')
 assert set(selected)=={x['id'] for x in m['rows']} and len(selected)==len(m['rows']);ids+=selected
 assert m['account']['name']==b['account_name'] and m['account']['currency']=='USD'
 assert datetime.fromisoformat(m['source_timestamps']['financial'])>=datetime.fromisoformat(q['started_at'])
 must={str(x['CAMPAIGN_ID']) for x in load(p/'sb.json') if str(x['DATE'])[:10]==q['date']} & set(selected)
 assert all((b['account_id'],cid) in ui for cid in must)
 assert all(len(x.encode('utf-16-le'))//2<=2000 for x in parts)
 hs=[h for part in parts for h in re.finditer(r'^\*\*Histórico ROI real — 7 dias[^\n]*\n```text\n(.*?)```',part,re.M|re.S)]
 assert hs
 if selected: assert any(len(h[1].splitlines())>=2 for h in hs)
 for h in hs:
  for dt in m['history_dates']:assert dt[8:10]+'/'+dt[5:7] in h[1].splitlines()[0]
 for row in m['rows']:
  assert len(row['history'])==7 and [h['date'] for h in row['history']]==m['history_dates']
  assert [h['partial'] for h in row['history']]==[False]*6+[True]
  assert row['roi']==row['history'][-1]['roi'] and row['spend']==row['history'][-1]['spend']
 print('\n###',b['account_name'],'campaigns',len(selected),'parts',len(parts))
 principals=[h for part in parts for h in re.finditer(r'^\*\*SHEIN — principal[^\n]*\n```text\n(.*?)```',part,re.M|re.S)]
 assert principals
 if selected:assert any(len(h[1].splitlines())>=2 for h in principals)
 principal=next((h for h in principals if len(h[1].splitlines())>=2),principals[0])
 print('CABECALHO\n'+'\n'.join(parts[0].splitlines()[:15]))
 print('PRINCIPAL_REAL\n'+principal[0].splitlines()[0]+'\n'+'\n'.join(principal[1].splitlines()[:4]))
 h=next((h for h in hs if len(h[1].splitlines())>=2),hs[0]);print('HISTORICO_REAL\n'+h[0].splitlines()[0]+'\n'+'\n'.join(h[1].splitlines()[:4]))
 tail='\n'.join(parts)[sum(len(x)+1 for x in parts[:-1]):]
 print('LIMITACOES\n'+parts[-1])
 checks.append({'account_id':b['account_id'],'thread_id':b['thread_id'],'campaigns':len(selected),'parts':len(parts),'ui_covered':len(must),'history_checked':True})
assert len(ids)==len(set(ids))
result={'status':'PASS','accounts':checks,'campaigns':len(ids),'parts':sum(x['parts'] for x in checks)}
(R/'prepublication-qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('QA_PREPUBLICACAO_OK',json.dumps(result))
