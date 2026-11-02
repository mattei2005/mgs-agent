import sys,json,re
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT));import discord_audit as d
modes=sys.argv[1:]
bases=json.loads((ROOT/'delivery-baselines.json').read_text())
results=[]
def moneyrows(text):
 rows=[]
 for line in text.splitlines():
  cells=tuple(s.strip() for s in line.split('|'))
  if len(cells)==6 and cells[0]!='BOT EMAIL':
   assert all(s=='n/d' or re.fullmatch(r'-?R\$ [\d.]+,\d{2}',s) for s in cells[4:]),cells
   rows.append(cells)
 return rows
for mode in modes:
 observed=json.loads((ROOT/(mode+'-native-observed.json')).read_text())
 apps=sorted(set(x['app'] for x in observed if x['kind']=='embed'))
 for app in apps:
  base=next(x for x in bases if x['app']==app);channel=base['channel_id']
  expected=[x for x in observed if x['app']==app]
  cards=[x['embed'] for x in expected if x['kind']=='embed'];assert len(cards)==1,(app,'unexpected card count')
  messages=d.get('channels/'+channel+'/messages?limit=100&after='+base['before_id']);messages=sorted(messages,key=lambda x:int(x['id']))
  matches=[m for m in messages if any(e.get('title')==cards[0]['title'] and e.get('description')==cards[0].get('description') for e in m.get('embeds',[]))]
  assert len(matches)==1,(app,'expected one logical live card',len(matches))
  card=matches[0];start=messages.index(card);family=[card]
  for m in messages[start+1:]:
   if m.get('embeds'):break
   family.append(m)
  exact=[d.get('channels/'+channel+'/messages/'+m['id']) for m in family]
  actual_embed=exact[0]['embeds'][0]
  for key in ['title','description','fields']:
   assert actual_embed.get(key)==cards[0].get(key),(app,'embed mismatch',key)
  exp_rows=[r for x in expected if x['kind']=='table' for r in moneyrows(x['text'])]
  actual_rows=[r for m in exact[1:] for r in moneyrows(m.get('content',''))]
  assert Counter(exp_rows)==Counter(actual_rows),(app,'table mismatch',len(exp_rows),len(actual_rows))
  expected_headings=[line.strip() for x in expected if x['kind']=='table' for line in x['text'].splitlines() if any(s in line for s in ['USUÁRIOS ATUAIS','REMOVIDOS AGORA','ADICIONADOS AGORA','REMOVIDOS ACUMULADOS','REMOVIDOS CONFIRMADOS'])]
  actual_text='\n'.join(m.get('content','') for m in exact[1:])
  assert all(h in actual_text for h in expected_headings),(app,'missing heading')
  result={'app':app,'channel_id':channel,'embed_id':card['id'],'message_ids':[m['id'] for m in exact],'rows':len(actual_rows),'numeric':sum(r[4]!='n/d' and r[5]!='n/d' for r in actual_rows),'unmatched':sum(r[4]=='n/d' or r[5]=='n/d' for r in actual_rows),'verified':True}
  results.append(result)
  (ROOT/(app+'-delivery-readback.json')).write_text(json.dumps({'receipt':result,'messages':exact},ensure_ascii=False,indent=2))
  print(json.dumps(result),flush=True)
 (ROOT/(mode+'-delivery-verification.json')).write_text(json.dumps([x for x in results if (x['app'].startswith('B013'))==(mode=='b013')],indent=2))
print('VERIFIED_CHANNELS',len(results),'ROWS',sum(x['rows'] for x in results))
