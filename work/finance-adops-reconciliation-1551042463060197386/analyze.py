import json,collections,datetime,re
from decimal import Decimal as D
from pathlib import Path
W=Path(__file__).parent
load=lambda n:json.loads((W/n).read_text())
rows=lambda sid:load(str(sid)+'.json')['values']
def z(x):
 if x in ('',None):return D(0)
 if isinstance(x,str) and re.fullmatch(r'\$\d{1,3}(?:,\d{3})+,\d{2}',x):
  # Explicit interpretation, original text retained in source snapshot.
  parts=x[1:].split(',');return D(''.join(parts[:-1])+'.'+parts[-1])
 return D(str(x))
save=lambda n,d:(W/n).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=str))
db=load('dashboard-db.json');s=next(x for x in db if x['id']=='workspace-2026-08');ad=next(x for x in db if x['id']=='master-ad-accounts');m=load('ui-model.json');src=load('source.json');lookup={x['id']:x for x in src['cells']}
val=lambda k:z(s['overrides'].get(k,lookup.get(k,{}).get('input','')))
iso=lambda n:(datetime.date(1899,12,30)+datetime.timedelta(days=n)).isoformat()
facts={f['id']:f for f in s['result']['domain']['facts']}
keyfacts=collections.defaultdict(list)
for fid,mm in m['facts'].items():
 for metric,keys in mm.items():
  for k in keys:keyfacts[k].append((fid,metric))
# Facebook exact-name monthly and day reconciliation.
fb=collections.defaultdict(lambda:collections.defaultdict(D)); dup=collections.Counter()
for name,day,cur,amount,*_ in rows(374431172)[1:]:
 assert cur=='USD';fb[name][iso(day)]+=z(amount);dup[(name,day,cur)]+=1
out=[];used=set()
for a in ad['additions']:
 if a.get('platform','meta')!='meta':continue
 dd=collections.defaultdict(D)
 for k in a.get('source_links',[]):
  fs=keyfacts.get(k,[])
  if val(k):assert len(set(facts[f]['date'] for f,metric in fs))==1,(k,fs)
  if fs:dd[facts[fs[0][0]]['date']]+=val(k)
 for add in s['additions']:
  if add.get('kind')=='account_spend' and add['account_id']==a['id']:dd[add['date']]+=z(add['amount'])
 name=a['name'];source=fb.get(name,{})
 if name in fb:used.add(name)
 diffs=[{'date':d,'sheet':source.get(d,D(0)),'dash':dd.get(d,D(0)),'delta':source.get(d,D(0))-dd.get(d,D(0))} for d in sorted(set(source)|set(dd)) if abs(source.get(d,D(0))-dd.get(d,D(0)))>=D('.005')]
 if source or sum(dd.values()):out.append({'name':name,'id':a['id'],'sheet_present':name in fb,'sheet':sum(source.values()),'dash':sum(dd.values()),'delta':sum(source.values())-sum(dd.values()),'diff_days':len(diffs),'days':diffs})
for name in sorted(set(fb)-used):out.append({'name':name,'id':None,'sheet_present':True,'sheet':sum(fb[name].values()),'dash':None,'delta':None,'diff_days':None,'days':dict(fb[name])})
# Unbound nonzero spending source slots.
linked={k for a in ad['additions'] for k in a.get('source_links',[])}
unbound=collections.defaultdict(lambda:{'amount':D(0),'keys':[]})
for k,x in m['inputs'].items():
 if x['metric']=='spend' and k not in linked and val(k):
  fs=keyfacts[k];site=facts[fs[0][0]]['site'];group=(site,x['label'])
  unbound[group]['amount']+=val(k);unbound[group]['keys'].append(k)
# Google date cells are locale-inverted, so compare monthly and separately proposed intended day.
google=[]
for name,col in [('Gamingadx-US-01','AIE'),('Mattei 1','AIW')]:
 rr=[r for r in rows(1132083250)[4:] if len(r)>3 and r[1]==name];dd=[]
 for r in rr:
  raw=r[0]
  if isinstance(raw,int):
   literal=iso(raw);date=datetime.date.fromisoformat(literal);intended=f'2026-08-{date.month:02}'
  else:literal=raw;intended=datetime.datetime.strptime(raw,'%m/%d/%Y').date().isoformat()
  key=f'principal|Agosto 2026|{col}{45+int(intended[-2:])}';dd.append({'literal':literal,'intended':intended,'source':z(r[3]),'dash':val(key),'delta':z(r[3])-val(key)})
 google.append({'name':name,'sheet':sum(x['source'] for x in dd),'dash':sum(x['dash'] for x in dd),'delta':sum(x['delta'] for x in dd),'days':dd})
save('spend-reconciliation.json',{'fb':out,'fb_duplicate_keys':[str(k) for k,v in dup.items() if v>1],'fb_total':sum(sum(v.values()) for v in fb.values()),'unbound':[{'site':k[0],'label':k[1],**v} for k,v in unbound.items()],'google':google})
# Revenue sources grouped with currency kept native.
sb={};sbday={}
for label,sid in [('sb1',565588781),('sb2',869925501)]:
 agg=collections.defaultdict(D);daily=collections.defaultdict(D)
 for r in rows(sid)[1:]:
  if len(r)<5:continue
  agg[r[1]]+=z(r[4]);daily[iso(r[0])]+=z(r[4])
 sb[label]=dict(agg);sbday[label]=dict(daily)
a=rows(565588781);b=rows(869925501);equal=[i for i in range(1,min(len(a),len(b))) if a[i]==b[i]]
contam={'rows':len(equal),'first_sheet_row':min(equal)+1,'last_sheet_row':max(equal)+1,'total':sum(z(b[i][4]) for i in equal),'all_tail_equal':all(a[i]==b[i] for i in range(min(equal),len(b))),'clean_first_rows':min(equal)-1,'clean_first_total':sum(z(r[4]) for r in b[1:min(equal)])}
avc={r[1]:z(r[2]) for r in rows(1839542079)[1:] if len(r)>2 and r[0]};avd=collections.defaultdict(D);avdays=collections.defaultdict(D)
for r in rows(1938914193)[1:]:
 if len(r)==7 and isinstance(r[0],int):avd[r[1]]+=z(r[6]);avdays[iso(r[0])]+=z(r[6])
av=[{'domain':k,'consolidated':avc.get(k,D(0)),'detailed':avd.get(k,D(0)),'delta':avc.get(k,D(0))-avd.get(k,D(0))} for k in sorted(set(avc)|set(avd))]
m2c=collections.defaultdict(D);m2d=collections.defaultdict(lambda:collections.defaultdict(D));domain=None
for i,r in enumerate(rows(1868178333)):
 if r and r[0]=='USD':domain=r[1]
 elif r and isinstance(r[0],int):m2c[domain]+=z(r[1])
for r in rows(1039066222)[1:]:m2d[r[1]]['direct' if r[2].strip().lower().startswith('b01') else 'bot']+=z(r[3])
save('revenue-source-reconciliation.json',{'sb':sb,'sbday':sbday,'sb2_duplicated_tail':contam,'av':av,'avdaily':avdays,'m2consolidated':m2c,'m2detailed':m2d})
print('FB TOTAL',sum(sum(v.values()) for v in fb.values()),'accounts',len(fb),'rows',sum(dup.values()),'dup',sum(v>1 for v in dup.values()))
for x in out:print('FB',x['name'],x['sheet'],x['dash'],x['delta'],'different days',x['diff_days'])
print('UNBOUND',[(k,v['amount']) for k,v in unbound.items()])
for x in google:print('GOOGLE',x['name'],x['sheet'],x['dash'],x['delta'],'days different',sum(abs(y['delta'])>=D('.005') for y in x['days']))
print('SB TOTAL',{k:sum(v.values()) for k,v in sb.items()},'CONTAM',contam)
print('AV',av,'totals',sum(avc.values()),sum(avd.values()))
print('M2',dict(m2c),{k:dict(v) for k,v in m2d.items()})
