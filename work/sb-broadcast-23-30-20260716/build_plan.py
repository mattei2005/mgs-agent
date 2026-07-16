#!/usr/bin/env python3
import json,re,unicodedata
from pathlib import Path
from collections import defaultdict,Counter

BASE=Path('/root/mgs-agent')
LIVE=Path('/tmp/sb-ares-full-live-20260716.json')
TXT=Path('/root/.hermes/profiles/zeus/cache/documents/doc_774f3f843098_templates_links.txt')
BANK=BASE/'data/utility-message-bank.json'
SPECIAL='Financeadx - CA-CC-FR/FR-SR - g006-d Nicolas'

def norm_name(s):
 s=unicodedata.normalize('NFKC',s).casefold().strip(); s=re.sub(r'\s+',' ',s); s=re.sub(r'\s*-\s*',' - ',s); return s

def visible(s): return re.sub('[\u200b\u200c\u200d\ufeff\u2060]','',s or '')
def norm_text(s): return re.sub(r'\s+',' ',visible(s).strip().lower())
def parse_msgs(r):
 x=r.get('MESSAGES') or []
 return json.loads(x) if isinstance(x,str) else x

def color(m):
 if int(m.get('INVALID_FORMAT') or 0)>0 or int(m.get('ERROR') or 0)>0:return 'purple'
 if int(m.get('REJECTED') or 0)>0:return 'red'
 if int(m.get('APPROVED') or 0)>0:return 'green'
 return 'gray'
def vertical(name):
 m=re.search(r'\b([A-Z]{2})[-_ ]([A-Z0-9]{2,8})[-_ ]([A-Z]{2})\b',name.upper())
 return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ''

def parse_links():
 blocks=[];cur=None
 for lineno,raw in enumerate(TXT.read_text(encoding='utf-8-sig').splitlines(),1):
  s=raw.strip()
  if not s:continue
  if s.lower().startswith(('http://','https://')):
   if cur:cur['links'].append(s)
  elif norm_name(s).startswith('link unico para'):
   continue
  else:
   cur={'name':s,'line':lineno,'links':[]};blocks.append(cur)
 # Correct only the Conecta block that clearly carries finance.ducapes links.
 for b in blocks:
  if norm_name(b['name'])==norm_name('Conecta - US-CC-EN/EN-SR - g001-d Icaro') and b['links'] and 'finance.ducapes.com' in b['links'][0]:
   b['name']='Ducapes Finance - US-CC-EN/EN-SR - g001-d Icaro'
 by=defaultdict(list)
 for b in blocks:by[norm_name(b['name'])].append(b)
 return blocks,by

live=json.loads(LIVE.read_text(encoding='utf-8'))['rows']
prod=[r for r in live if not re.match(r'(?i)^teste[- ]',str(r.get('NAME') or '')) and not re.match(r'(?i)^n[aã]o usar',str(r.get('NAME') or ''))]
blocks,links_by=parse_links()
bank=json.loads(BANK.read_text(encoding='utf-8'))
approved=defaultdict(list)
for rec in bank.get('records',{}).values():
 if rec.get('status')=='approved' and rec.get('text') and rec.get('cta_1'):
  approved[rec.get('vertical','')].append(rec)
for v in approved:
 approved[v].sort(key=lambda r:(-int(r.get('approved_count') or 0),r.get('text','')))

errors=[]; report=[]; needs_by_v=Counter()
for r in sorted(prod,key=lambda x:x.get('NAME','')):
 name=r['NAME']; n=norm_name(name)
 if len(links_by.get(n,[]))!=1:errors.append({'template':name,'error':'link_mapping_count','count':len(links_by.get(n,[]))});continue
 lcount=len(links_by[n][0]['links'])
 pages=int(r.get('PAGES') or 0); msgs=parse_msgs(r)
 target=30 if pages>0 or name==SPECIAL else 23
 if lcount not in (1,23):errors.append({'template':name,'error':'unexpected_link_count','links':lcount})
 if name==SPECIAL:
  required=30; kept=0; replaced=len(msgs); add=max(0,30-len(msgs))
 else:
  counts=Counter(color(m) for m in msgs)
  if pages>0:
   kept=counts['green']; replaced=len(msgs)-kept; add=max(0,target-len(msgs)); required=replaced+add
  else:
   kept=len(msgs);replaced=0;add=max(0,target-len(msgs));required=add
 needs_by_v[vertical(name)]+=required
 report.append({'template':name,'vertical':vertical(name),'pages':pages,'before':len(msgs),'target':target,'links':lcount,'kept':kept,'replaced':replaced,'added':add,'approved_bank_unique':len({norm_text(x['text']) for x in approved.get(vertical(name),[])})})

live_norm={norm_name(r['NAME']) for r in prod}; file_norm=set(links_by)
print(json.dumps({'scope':{'live_all':len(live),'production':len(prod),'ignored':len(live)-len(prod),'linked':sum(int(r.get('PAGES') or 0)>0 for r in prod),'unlinked':sum(int(r.get('PAGES') or 0)==0 for r in prod)},'mapping':{'blocks':len(blocks),'unique':len(links_by),'missing_live':[r['NAME'] for r in prod if norm_name(r['NAME']) not in file_norm],'file_only':[bs[0]['name'] for n,bs in links_by.items() if n not in live_norm]},'errors':errors,'needs_by_vertical':[{'vertical':v,'candidate_slots_needed_across_templates':n,'approved_bank_unique':len({norm_text(x['text']) for x in approved.get(v,[])})} for v,n in sorted(needs_by_v.items())],'templates':report},ensure_ascii=False,indent=2))
