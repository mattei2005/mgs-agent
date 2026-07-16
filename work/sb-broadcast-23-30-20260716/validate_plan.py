#!/usr/bin/env python3
import csv,json,re,unicodedata
from collections import defaultdict
from pathlib import Path
BASE=Path('/root/mgs-agent');RUN=BASE/'work/sb-broadcast-23-30-20260716';PLAN=RUN/'plan.json';TXT=Path('/root/.hermes/profiles/zeus/cache/documents/doc_774f3f843098_templates_links.txt');SPECIAL='Financeadx - CA-CC-FR/FR-SR - g006-d Nicolas'
def norm_name(s):
 s=unicodedata.normalize('NFKC',s).casefold().strip();s=re.sub(r'\s+',' ',s);s=re.sub(r'\s*-\s*',' - ',s);return s
def visible(s):return re.sub('[\u200b\u200c\u200d\ufeff\u2060]','',s or '')
def nt(s):return re.sub(r'\s+',' ',visible(s).strip().lower())
def msgs(r):
 x=r.get('MESSAGES') or [];return json.loads(x) if isinstance(x,str) else x
def color(m):
 if int(m.get('INVALID_FORMAT') or 0)>0 or int(m.get('ERROR') or 0)>0:return 'purple'
 if int(m.get('REJECTED') or 0)>0:return 'red'
 if int(m.get('APPROVED') or 0)>0:return 'green'
 return 'gray'
def parse_links():
 blocks=[];cur=None
 for raw in TXT.read_text(encoding='utf-8-sig').splitlines():
  s=raw.strip()
  if not s:continue
  if s.lower().startswith(('http://','https://')):
   if cur:cur['links'].append(s)
  elif norm_name(s).startswith('link unico para'):continue
  else:cur={'name':s,'links':[]};blocks.append(cur)
 for b in blocks:
  if norm_name(b['name'])==norm_name('Conecta - US-CC-EN/EN-SR - g001-d Icaro') and b['links'] and 'finance.ducapes.com' in b['links'][0]:b['name']='Ducapes Finance - US-CC-EN/EN-SR - g001-d Icaro'
 return {norm_name(b['name']):b['links'] for b in blocks}
D=json.loads(PLAN.read_text(encoding='utf-8'));items=D['templates'];links=parse_links();errors=[]
if len(items)!=85:errors.append(f'plan count {len(items)}')
for x in items:
 name=x['name'];final=x['messages'];oldrow=json.loads(Path(x['backup']).read_text(encoding='utf-8'));old=sorted(msgs(oldrow),key=lambda m:int(m.get('MESSAGE_ID') or 0));target=x['target_count']
 if re.match(r'(?i)^(teste|n[aã]o usar)',name):errors.append(f'{name}: ignored prefix included')
 if len(final)!=target:errors.append(f'{name}: count')
 if [m['MESSAGE_ID'] for m in final]!=list(range(1,target+1)):errors.append(f'{name}: ids')
 if len({nt(m['TEXT']) for m in final})!=target:errors.append(f'{name}: duplicate text')
 raw=links.get(norm_name(name),[]);expected=[raw[0]]*target if len(raw)==1 else [raw[i%23] for i in range(target)]
 if [m['LINK_1'] for m in final]!=expected:errors.append(f'{name}: links')
 for i,m in enumerate(old):
  f=final[i];c=color(m)
  if name==SPECIAL:continue
  if x['requires_approval']:
   if c=='green' and (m.get('TEXT')!=f['TEXT'] or (m.get('CTA_1') or m.get('CTA 1') or '')!=f['CTA_1']):errors.append(f'{name}: green changed {i+1}')
   if c!='green' and nt(m.get('TEXT') or '')==nt(f['TEXT']):errors.append(f'{name}: non-green not replaced {i+1}')
  else:
   if m.get('TEXT')!=f['TEXT'] or (m.get('CTA_1') or m.get('CTA 1') or '')!=f['CTA_1']:errors.append(f'{name}: unlinked existing changed {i+1}')
 csvp=Path(x['csv']);rawbytes=csvp.read_bytes()
 if not rawbytes.startswith(b'\xef\xbb\xbf'):errors.append(f'{name}: no BOM')
 if b'\r\n' not in rawbytes:errors.append(f'{name}: no CRLF')
 with csvp.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 if len(rows)!=target:errors.append(f'{name}: csv count')
 else:
  for i,(r,m) in enumerate(zip(rows,final),1):
   if int(r['MESSAGE ID'])!=i or r['TEXT']!=m['TEXT'] or r['CTA 1']!=m['CTA_1'] or r['LINK 1']!=m['LINK_1']:errors.append(f'{name}: csv core {i}');break
 if name==SPECIAL:
  if target!=30 or any(re.search(r'\b(card|your|review|open|status ready)\b',visible(m['TEXT']),re.I) for m in final):errors.append(f'{name}: French validation')
print(json.dumps({'status':'OK' if not errors else 'BLOCKED','templates':len(items),'csv_files':len(list((RUN/'csv').glob('*.csv'))),'backups':len(list((RUN/'backups').glob('*.json'))),'errors':errors[:100],'error_count':len(errors)},ensure_ascii=False,indent=2))
raise SystemExit(1 if errors else 0)
