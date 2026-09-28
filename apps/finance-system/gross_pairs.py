"""Native CAD/USD amounts; calculation-only bridge, never source writes."""
from decimal import Decimal as D
from calc import Workbook,num
import re

def currencies(data,model):
    out={k:x.get('currency') for k,x in model['inputs'].items() if x.get('metric')=='gross'}
    records={c['id']:c for c in data['cells']}
    for block in data['blocks']:
        for metric,column in block['metrics'].items():
            if not (metric.startswith('GROSS_USD_') or metric=='GROSS_BR'):continue
            for day in range(31):
                key=f"principal|Agosto 2026|{column}{block['sr']+day}"
                c=records.get(key,{})
                if key in out and not c.get('formula'):out[key]='USD'
                if c.get('formula','').startswith('=SUM('):
                    for cell in re.findall(r'[A-Z]+[0-9]+',c['formula']):
                        leaf='principal|Agosto 2026|'+cell
                        if leaf in out:out[leaf]='USD'
                m=re.fullmatch(r'=IF\(([A-Z]+\d+)="","",\1/\$H\$1\)',c.get('formula',''))
                if m and 'principal|Agosto 2026|'+m[1] in out:out['principal|Agosto 2026|'+m[1]]='CAD'
    return out

def index(additions,period):
    result={}
    for a in additions:
        if a.get('kind')!='gross_pair':continue
        if a.get('period')!=period or a.get('target_type') not in ['input','entry']:raise ValueError('Invalid revenue pair scope')
        key=(a['target_type'],a['target'])
        if key in result:raise ValueError('Duplicate revenue pair')
        for k in ['cad','usd']:
            if a.get(k) not in ('',None):
                value=D(str(a[k]))
                if not value.is_finite():raise ValueError('Invalid revenue amount')
        result[key]=a
    return result

def total(pair,rate):
    if pair.get('cad') in ('',None) and pair.get('usd') in ('',None):return ''
    if num(rate)<=0:raise ValueError('Invalid USD/CAD quote')
    return num(pair.get('cad'))/num(rate)+num(pair.get('usd'))

def prepare(data,overrides,model,additions,period,as_of=None):
    pairs=index(additions,period)
    if not pairs:return overrides,pairs,{}
    cur=currencies(data,model);w=Workbook(data,overrides,as_of);rate=w.get('principal','Agosto 2026','H1');out=dict(overrides)
    entries={a['id'] for a in additions if a.get('id') and a.get('kind') in (None,'native_day')}
    for (kind,key),pair in pairs.items():
        if kind=='entry':
            if key not in entries:raise ValueError('Revenue entry no longer exists')
            continue
        if key not in cur or cur[key] not in ['CAD','USD','GBP']:raise ValueError('Unsupported revenue input')
        if cur[key]=='GBP' and num(overrides.get(key,w.get(*key.split('|',2))))!=0:raise ValueError('Existing GBP cannot be relabelled CAD/USD')
        value=total(pair,rate);out[key]=value if value=='' or cur[key]=='USD' else value*num(rate) if cur[key]=='CAD' else value/num(w.get('principal','Agosto 2026','I1'))
    return out,pairs,cur

def legacy_origins(facts,model,pairs,cur,w):
    grouped={};seen=set()
    for f in facts:
        for k in model.get('facts',{}).get(f['id'],{}).get('gross',[]):
            if k in seen:continue
            seen.add(k);owners=model['inputs'][k].get('managers',[])
            if len(owners)!=1:continue
            p=pairs.get(('input',k));values={c:num(p[field]) for c,field in [('CAD','cad'),('USD','usd')] if p.get(field) not in ('',None)} if p else {cur[k]:num(w.get(*k.split('|',2)))}
            for currency,value in values.items():
                key=(owners[0],f['site'],f['country'],f['date'],currency);grouped[key]=grouped.get(key,D(0))+value
    return [dict(zip(['manager','site','country','date','currency'],key),gross=value) for key,value in grouped.items()]

def annotate(facts,model,pairs,cur,w):
    for f in facts:
        keys=model.get('facts',{}).get(f['id'],{}).get('gross',[])
        if not any(('input',k) in pairs for k in keys):continue
        native={}
        for k in keys:
            p=pairs.get(('input',k))
            if p:
                for c,field in [('CAD','cad'),('USD','usd')]:
                    if p.get(field) not in ('',None):native[c]=native.get(c,D(0))+num(p[field])
            else:
                value=w.get(*k.split('|',2))
                if value not in ('',None):native[cur[k]]=native.get(cur[k],D(0))+num(value)
        f['gross_origins']=native
