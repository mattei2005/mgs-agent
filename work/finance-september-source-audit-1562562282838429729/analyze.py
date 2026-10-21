import json,re,datetime,collections
from decimal import Decimal
from pathlib import Path
P=Path(__file__).parent
D=lambda x:Decimal(str(x))
def load(sid,month='september'):
 return json.loads((P/f'{month}-{sid}.json').read_text())['sheets'][0]
def cells(s):
 return [r.get('values',[]) for r in s['data'][0].get('rowData',[])]
def v(c):
 e=c.get('effectiveValue',{});return e.get('numberValue',e.get('stringValue',e.get('boolValue','')))
def vals(r):return [v(c) for c in r]
def date(x):
 if isinstance(x,(int,float)):return (datetime.date(1899,12,30)+datetime.timedelta(days=x)).isoformat()
 if re.fullmatch(r'\d{4}-\d\d-\d\d',str(x)):return x
 return None
out={'tabs':[]}
for m in json.loads((P/'september-manifest.json').read_text()):
 s=load(m['sheetId']); rows=cells(s)
 errors=[]; formulas=[]
 for i,r in enumerate(rows,1):
  for j,c in enumerate(r,1):
   if 'errorValue' in c.get('effectiveValue',{}):errors.append([i,j,c['effectiveValue']])
   if 'formulaValue' in c.get('userEnteredValue',{}):formulas.append([i,j,c['userEnteredValue']['formulaValue'],v(c)])
 out['tabs'].append({'title':m['title'],'errors':errors,'formulas':formulas})
for sid in [565588781,869925501]:
 s=load(sid); records=[]; excluded=[]; money_text=[]; formats=collections.Counter()
 for i,r in enumerate(cells(s),1):
  a=vals(r); a+=['']*(7-len(a))
  if i==1:continue
  if a[1] and date(a[0]):
   records.append({'row':i,'date':date(a[0]),'placement':a[1],'medium':a[2],'source':a[3],'revenue':a[4]})
   if not isinstance(a[4],(int,float)):money_text.append([i,a[4]])
   formats[r[4].get('effectiveFormat',{}).get('numberFormat',{}).get('pattern','')]+=1
  elif any(x!='' for x in a):excluded.append({'row':i,'values':a,'cellE':r[4] if len(r)>4 else {}})
 total=sum((D(r['revenue']) for r in records),D(0))
 groups=collections.defaultdict(lambda:D(0)); meds=collections.defaultdict(lambda:D(0)); keys=collections.defaultdict(list); exact=collections.defaultdict(list)
 for r in records:
  groups[r['placement']]+=D(r['revenue']);meds[r['medium']]+=D(r['revenue'])
  key=tuple(r[k] for k in ['date','placement','medium','source']); keys[key].append(r['row']); exact[key+(str(r['revenue']),)].append(r['row'])
 data={'rows':len(records),'total':str(total),'dates':sorted(set(r['date'] for r in records)),'placements':{k:str(v) for k,v in groups.items()},'mediums':{k:str(v) for k,v in meds.items()},'money_text':money_text,'negative_rows':[r for r in records if D(r['revenue'])<0],'zero_rows':sum(D(r['revenue'])==0 for r in records),'duplicate_keys':[{'key':k,'rows':a} for k,a in keys.items() if len(a)>1],'exact_duplicates':[{'key':k,'rows':a} for k,a in exact.items() if len(a)>1],'formats':dict(formats),'excluded':excluded}
 out[s['properties']['title']]=data
 (P/f'sb-{sid}-records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
fb=[]
for i,r in enumerate(cells(load(374431172)),1):
 a=vals(r)
 if i>1 and len(a)>=3 and a[0] and a[1]=='USD':fb.append({'row':i,'account':a[0],'amount':str(a[2]),'numeric':isinstance(a[2],(int,float))})
out['facebook']={'records':fb,'accounts':len(set(r['account'] for r in fb)),'sum_numeric':str(sum((D(r['amount']) for r in fb if r['numeric']),D(0))),'sum_including_explicit_decimal_text':str(sum((D(r['amount']) for r in fb),D(0)))}
go=[]
for i,r in enumerate(cells(load(1132083250)),1):
 a=vals(r)
 if len(a)>=4 and a[2]=='BRL':
  intended=datetime.datetime.strptime(r[0]['formattedValue'],'%m/%d/%Y').date().isoformat()
  go.append({'row':i,'raw_date':a[0],'stored_date':date(a[0]),'display':r[0]['formattedValue'],'intended_US_date':intended,'account':a[1],'amount':str(a[3])})
by={}
for acc in sorted(set(r['account'] for r in go)):
 rs=[r for r in go if r['account']==acc];by[acc]={'rows':len(rs),'total':str(sum((D(r['amount']) for r in rs),D(0))),'intended_dates':[r['intended_US_date'] for r in rs]}
out['google']={'rows':go,'by_account':by,'total':str(sum((D(r['amount']) for r in go),D(0))),'numeric_dates':sum(isinstance(r['raw_date'],(int,float)) for r in go),'numeric_outside_september':sum(bool(r['stored_date']) and not r['stored_date'].startswith('2026-09') for r in go)}
site=None;m2=collections.defaultdict(list)
for i,r in enumerate(cells(load(1868178333)),1):
 a=vals(r)
 if len(a)>1 and isinstance(a[1],str) and a[1].endswith('.com:'):site=a[1][:-1]
 elif len(a)>1 and date(a[0]):m2[site].append({'row':i,'date':date(a[0]),'revenue':a[1]})
out['m2']={k:{'rows':len(rs),'total':str(sum((D(r['revenue']) for r in rs),D(0))),'dates':[r['date'] for r in rs]} for k,rs in m2.items()}
out['m2_total']=str(sum((D(r['revenue']) for rs in m2.values() for r in rs),D(0)))
# Exact cross-network and prior-month overlap of fact tuples
r1=json.loads((P/'sb-565588781-records.json').read_text());r2=json.loads((P/'sb-869925501-records.json').read_text())
f=lambda r:tuple(r[k] for k in ['date','placement','medium','source','revenue'])
out['sb_cross_network_exact_overlap']=len(set(map(f,r1))&set(map(f,r2)))
(P/'analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
summary={}
for k,vv in out.items():
 if k=='tabs':summary[k]=vv
 elif k.startswith('rede '):summary[k]={a:b for a,b in vv.items() if a not in ['duplicate_keys','exact_duplicates']}; summary[k]['duplicate_keys_count']=len(vv['duplicate_keys']);summary[k]['exact_duplicates_count']=len(vv['exact_duplicates']);summary[k]['duplicate_examples']=vv['duplicate_keys'][:5]
 elif k=='facebook':summary[k]={a:b for a,b in vv.items() if a!='records'};summary[k]['text_records']=[r for r in vv['records'] if not r['numeric']]
 elif k=='google':summary[k]={a:b for a,b in vv.items() if a!='rows'}
 else:summary[k]=vv
print(json.dumps(summary,ensure_ascii=False,indent=2))
