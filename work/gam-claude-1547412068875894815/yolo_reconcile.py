import json,re
from pathlib import Path
from collections import defaultdict
from decimal import Decimal as D
P=Path(__file__).parent
raw=[r for r in json.loads((P/'raw.json').read_text()) if r['placement']=='pl_digital-trust_yolokfx_us']
sb=json.loads((P/'sb-yolo-queries.json').read_text())[0]['data'];ver=json.loads((P/'sb-yolo-verification.json').read_text());domain=next(x['data'] for x in ver if x['type']=='domain')
by=defaultdict(lambda:D(0));mapping=defaultdict(set);proof=[]
for r in sb:
 name=r['ACCOUNT_NAME'];m=re.search(r'-(G00[1-6])$',name,re.I);manager=m.group(1).upper() if m else 'SEM_CONTA'
 by[(r['DATE'],manager)]+=D(str(r['REVENUE']))
 if manager=='SEM_CONTA':continue
 match=re.fullmatch(r'(b\d+fb\d+c\d+)g\d+',r['UTM_ADGROUP'])
 if match:
  code=match.group(1);namecodes=re.findall(r'\((b\d+fb\d+c\d+)\)',r['CAMPAIGN_NAME']);assert not namecodes or code in namecodes,(code,namecodes)
  mapping[(r['DATE'],code)].add((r['CUSTOMER_ID'],name,manager))
assert all(len(v)==1 for v in mapping.values())
gam_by=defaultdict(lambda:D(0));unmapped=[]
for r in raw:
 hit=mapping.get((r['date'],r['campaign']));manager=next(iter(hit))[2] if hit else 'SEM_ATRIBUICAO';gam_by[(r['date'],manager)]+=D(r['revenue']);proof.append({'file':r['file'],'row':r['row'],'date':r['date'],'campaign':r['campaign'],'amount':r['revenue'],'account_matches':list(hit or []),'manager':manager})
 if not hit:unmapped.append({'date':r['date'],'campaign':r['campaign'],'amount':r['revenue']})
summary=[]
for day in ['2026-09-07','2026-09-08']:
 gam=sum(D(r['revenue']) for r in raw if r['date']==day);ad=sum(v for k,v in by.items() if k[0]==day);dom=sum(D(str(r['REVENUE'])) for r in domain if r['DATE']==day);raw_unknown=sum(D(r['revenue']) for r in raw if r['date']==day and r['campaign']=='-')
 summary.append({'date':day,'gam_original':str(gam),'adgroup_gross_CAD':str(ad),'domain_gross_CAD':str(dom),'gam_minus_adgroup':str(gam-ad),'gam_minus_domain':str(gam-dom),'gam_missing_campaign':str(raw_unknown),'gam_identified_minus_adgroup':str(gam-raw_unknown-ad)})
out={'scope':'Read-only Yolo Sep7/8, CAD gross REVENUE; no extrapolation to Sep1-6/9; no allocation of residual','adgroup_rows':len(sb),'same_single_day_reads':True,'accounts':sorted(set((r['CUSTOMER_ID'],r['ACCOUNT_NAME']) for r in sb if r['ACCOUNT_NAME'])),'dashboard_by_manager':[{'date':k[0],'manager':k[1],'gross_CAD':str(v)} for k,v in sorted(by.items())],'gam_by_exact_campaign_join':[{'date':k[0],'manager':k[1],'gross_CAD':str(v)} for k,v in sorted(gam_by.items())],'unmapped_gam':unmapped,'comparisons':summary}
(P/'yolo-reconciliation.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));(P/'yolo-campaign-lineage.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False));print(json.dumps(out,indent=2,ensure_ascii=False))
