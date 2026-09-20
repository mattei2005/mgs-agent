import json,collections,datetime,copy,re,hashlib
from decimal import Decimal as D
from pathlib import Path
W=Path(__file__).parent
load=lambda n:json.loads((W/n).read_text())
rows=lambda sid:load(str(sid)+'-UNFORMATTED_VALUE.json')['values']
s=next(x for x in load('dashboard-db.json') if x['id']=='workspace-2026-08');ad=next(x for x in load('dashboard-db.json') if x['id']=='master-ad-accounts');model=load('ui-model.json');src={x['id']:x for x in load('source.json')['cells']};facts={x['id']:x for x in s['result']['domain']['facts']}
z=lambda v:D(str(v or 0))
val=lambda k:z(s['overrides'].get(k,src.get(k,{}).get('input','')))
iso=lambda n:(datetime.date(1899,12,30)+datetime.timedelta(days=n)).isoformat()
keyfacts=collections.defaultdict(list)
for fid,mm in model['facts'].items():
 for metric,keys in mm.items():
  for k in keys:keyfacts[k].append((fid,metric))
new=copy.deepcopy(s);accounts=copy.deepcopy(ad['additions']);changes={};spend_checks=[]
def put(k,value,reason):
 value=str(value)
 if val(k)==z(value):return
 assert k in model['inputs'];assert k not in changes or changes[k]['after']==value
 changes[k]={'before':str(val(k)),'after':value,'reason':reason};new['overrides'][k]=value
# Explicit typo correction changes display name, not numeric identity or verified Meta name.
ly=next(x for x in accounts if x['id']=='1818460511984988');assert ly['name']=='LyzmoFinanzas-US-CC-ES-01';ly['name']='LyzmoFinanzas-US-CC-ES-02';ly['name_correction_authority']='1551275920671776839'
fb=collections.defaultdict(dict)
for name,day,cur,amount,*_ in rows(374431172)[1:]:
 assert cur=='USD';date=iso(day);assert date not in fb[name];fb[name][date]=z(amount)
assert len(fb)==48
for name,dd in fb.items():
 aa=[x for x in accounts if x['name']==name];assert len(aa)==1,name;a=aa[0]
 keys=a['source_links'];bydate=collections.defaultdict(list)
 for k in keys:
  dates={facts[f]['date'] for f,metric in keyfacts[k]};assert len(dates)==1,(name,k,dates);bydate[next(iter(dates))].append(k)
 assert len(bydate)==31,(name,len(bydate))
 for date,ks in bydate.items():
  amount=dd.get(date,D(0));before=sum(val(k) for k in ks)
  if name=='Infinitynexx-MX-CC-ES-01':
   targets=[k for k in ks if int(re.search(r'\d+$',k).group())<100];assert len(targets)==1
  elif len(ks)==1:targets=ks
  else:
   targets=[k for k in ks if val(k)]
   assert amount==0 or len(targets)==1,('ambiguous_spend',name,date,ks,targets)
  target=targets[0] if targets else None
  for k in ks:put(k,amount if k==target else D(0),'Facebook '+name+' '+date)
  spend_checks.append({'platform':'meta','name':name,'id':a['id'],'date':date,'keys':ks,'expected':str(amount),'before':str(before)})
# Report dates were explicitly confirmed as the complete August interval.
for name,column in [('Gamingadx-US-01','AIE'),('Mattei 1','AIW')]:
 rr=[r for r in rows(1132083250)[4:] if len(r)>3 and r[1]==name];assert len(rr)==31
 for r in rr:
  literal=r[0];date=(f'2026-08-{datetime.date.fromisoformat(iso(literal)).month:02d}' if isinstance(literal,int) else datetime.datetime.strptime(literal,'%m/%d/%Y').date().isoformat());assert date.startswith('2026-08-')
  key=f'principal|Agosto 2026|{column}{45+int(date[-2:])}';put(key,z(r[3]),'Google '+name+' '+date);spend_checks.append({'platform':'google','name':name,'date':date,'keys':[key],'expected':str(z(r[3])),'before':str(val(key))})
# Five residual sites explicitly authorized for G002 and no expense participation.
residuals={'boostingecon':('Boostingecon','US'),'cephyric':('Cephyric','FR'),'dicasfinancas':('DicasFinancas','BR'),'escalatepower':('Escalatepower','US'),'mavroa':('Mavroa','US')}
res_entries=[]
quotes={name:str(z(s['result']['results']['principal|Agosto 2026|'+cell]['actual'])) for name,cell in [('USDBRL','F1'),('USDCAD','H1'),('GBPUSD','I1')]}
for key,(site,country) in residuals.items():
 assert not any(x.get('kind')=='site' and x.get('name')==site for x in new['additions'])
 new['additions'].append({'kind':'site','id':'site-'+key+'-adops-2026-08','new':True,'name':site,'status':'INATIVO','manager':'SEM_COMISSAO','owner':'MGS','countries':[country],'network':'SB Rede1','partner':'SB Rede1','currency':'CAD','authorization':'1551275920671776839'})
 for i,r in enumerate(rows(565588781)[1:],2):
  if r[1]!=f'pl_digital-trust_{key}_{country.lower()}':continue
  assert r[2]=='g002-d';entry={'id':f'adops-1551275920671776839-sb1-row-{i}','site':site,'country':country,'manager':'SEM_COMISSAO','partner':'SB Rede1','date':iso(r[0]),'currency':'CAD','gross':str(z(r[4])),'spend':'0','quotes':quotes,'invalid_rate':s['result']['results']['principal|Agosto 2026|L1']['actual'],'share_rate':s['result']['results']['principal|Agosto 2026|D1']['actual'],'tax_rate':s['result']['results']['principal|Agosto 2026|C1']['actual'],'authorization':'1551275920671776839','source_import_type':'adops_august_reconciliation','source_row':i,'source_placement':r[1],'source_manager_tag':r[2]}
  new['additions'].append(entry);res_entries.append(entry)
# Correct the confirmed August network label, without changing rate parameters.
finc=next(x for x in new['additions'] if x.get('kind')=='site' and x['name']=='Fincgriffin');finc.update(network='SB Rede2',partner='SB Rede2',invalid_source='XFD1',network_correction_authority='1551275920671776839')
# Retain all other revenue pending exact AV monthly adjustment presentation.
plan={'authorization':'1551275920671776839','period':'2026-08','expected_revision':s['revision'],'expected_account_revision':ad['revision'],'overrides':new['overrides'],'additions':new['additions'],'accounts':accounts,'changes':changes,'spend_checks':spend_checks,'residual_entries':res_entries,'preserved_revenue_inputs':True,'revenue_followup':'Complete source data retained. AV monthly-to-daily/country adjustment and M2 country split require explicit presentation decision; SB non-residual remains in the same open scope.'}
(W/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
summary={'changes':len(changes),'fb_accounts':len(fb),'fb_total':str(sum(sum(dd.values()) for dd in fb.values())),'google_total':str(sum(z(x['expected']) for x in spend_checks if x['platform']=='google')),'residual_sites':len(residuals),'residual_rows':len(res_entries),'residual_CAD':str(sum(z(x['gross']) for x in res_entries)),'fb_changed_accounts':len(set(x['reason'].split(' 2026')[0] for x in changes.values() if x['reason'].startswith('Facebook'))),'spend_changed_days':len(changes)}
(W/'plan-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
