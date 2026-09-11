import json,pathlib,re,decimal,collections,hashlib
D=decimal.Decimal;root=pathlib.Path('/root/mgs-agent/work/adops-revenue-1547811852405178460');months={'Ad Manager Report / Agosto':'2026-08','Ad Manager Report / 01 - 09':'2026-09'};rows=[]
def amount(v,network):
 if isinstance(v,(int,float)):return ('CAD' if network=='rede1' else 'USD'),D(str(v))
 s=str(v).strip();currency='CAD' if s.startswith('CA$') else 'USD' if s.startswith('$') else None;assert currency,s;s=s.replace('CA$','').replace('$','').replace(' ','').replace('.','').replace(',','.');return currency,D(s)
for network in ['rede1','rede2']:
 data=json.loads((root/(network+'-unformatted_value.json')).read_text())
 for vr in data['valueRanges']:
  title=vr['range'].split('!')[0].strip("'");vals=vr['values'];assert title in months and vals[0]==['Placement','utm_medium (utm_medium)','utm_source (utm_source)','Ad Exchange revenue']
  for i,r in enumerate(vals[1:],2):
   assert len(r)==4;currency,value=amount(r[3],network);assert (network,currency) in [('rede1','CAD'),('rede2','USD')];m=re.fullmatch(r'pl_digital-trust_([a-z0-9]+)_([a-z]{2})',r[0]);assert m,r[0];brand,country=m.groups();rows.append({'network':network,'month':months[title],'source_row':i,'placement':r[0],'brand':brand,'country':country.upper(),'medium':str(r[1]).strip(),'source':str(r[2]).strip(),'currency':currency,'revenue':str(value)})
assert len(rows)==(164+194+31+33);pk=[(x['network'],x['month'],x['placement'],x['medium'],x['source']) for x in rows];assert len(pk)==len(set(pk));totals=collections.defaultdict(D);nonzero=collections.Counter();zeros=collections.Counter();byplacement=collections.defaultdict(D);bymedium=collections.defaultdict(D)
for r in rows:
 k=(r['network'],r['month'],r['currency']);v=D(r['revenue']);totals[k]+=v;nonzero[(r['network'],r['month'])]+=v!=0;zeros[(r['network'],r['month'])]+=v==0;byplacement[(r['network'],r['month'],r['placement'])]+=v;bymedium[(r['network'],r['month'],r['medium'])]+=v
(root/'normalized-rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');summary={'pass':True,'rows':len(rows),'totals':{'|'.join(k):str(v) for k,v in sorted(totals.items())},'nonzero':{'|'.join(k):v for k,v in sorted(nonzero.items())},'zero':{'|'.join(k):v for k,v in sorted(zeros.items())},'placements':{'|'.join(k):str(v) for k,v in sorted(byplacement.items())},'mediums':{'|'.join(k):str(v) for k,v in sorted(bymedium.items())},'hashes':{'normalized_rows_sha256':hashlib.sha256((root/'normalized-rows.json').read_bytes()).hexdigest()}};(root/'normalized-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pass':True,'rows':len(rows),'totals':summary['totals'],'nonzero':summary['nonzero'],'zero':summary['zero'],'unique_placements':{n+'|'+m:len({r['placement'] for r in rows if r['network']==n and r['month']==m}) for n in ['rede1','rede2'] for m in ['2026-08','2026-09']}},ensure_ascii=False))
