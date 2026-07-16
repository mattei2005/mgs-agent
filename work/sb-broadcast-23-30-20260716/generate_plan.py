#!/usr/bin/env python3
import csv,datetime as dt,hashlib,importlib.util,json,re,unicodedata
from collections import Counter,defaultdict
from copy import deepcopy
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path('/root/mgs-agent')
RUN=BASE/'work/sb-broadcast-23-30-20260716'
LIVE=Path('/tmp/sb-ares-full-live-20260716.json')
TXT=Path('/root/.hermes/profiles/zeus/cache/documents/doc_774f3f843098_templates_links.txt')
BANK=BASE/'data/utility-message-bank.json'
FR=RUN/'ca-cc-fr-translations.json'
SPECIAL='Financeadx - CA-CC-FR/FR-SR - g006-d Nicolas'
TZ=ZoneInfo('America/New_York')
STATUS_KEYS=('APPROVED','INVALID_FORMAT','REJECTED','ERROR','REJECTED_REASON','key')
CSV_FIELDS=['MESSAGE ID','TEXT','DESCRIPTION','IMAGE','CTA 1','LINK 1','CTA 2','LINK 2','TEXT 2','APPROVAL']

spec=importlib.util.spec_from_file_location('canary',BASE/'scripts/utility-canary-approval-loop.py')
assert spec is not None and spec.loader is not None
canary=importlib.util.module_from_spec(spec);spec.loader.exec_module(canary)

def now():return dt.datetime.now(TZ).isoformat(timespec='seconds')
def norm_name(s):
 s=unicodedata.normalize('NFKC',s).casefold().strip();s=re.sub(r'\s+',' ',s);s=re.sub(r'\s*-\s*',' - ',s);return s
def visible(s):return re.sub('[\u200b\u200c\u200d\ufeff\u2060]','',s or '')
def norm_text(s):return re.sub(r'\s+',' ',visible(s).strip().lower())
def vertical(name):
 m=re.search(r'\b([A-Z]{2})[-_ ]([A-Z0-9]{2,8})[-_ ]([A-Z]{2})\b',name.upper());return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ''
def parse_msgs(r):
 x=r.get('MESSAGES') or [];return json.loads(x) if isinstance(x,str) else x
def color(m):
 if int(m.get('INVALID_FORMAT') or 0)>0 or int(m.get('ERROR') or 0)>0:return 'purple'
 if int(m.get('REJECTED') or 0)>0:return 'red'
 if int(m.get('APPROVED') or 0)>0:return 'green'
 return 'gray'
def safe(s):return re.sub(r'[^a-z0-9._-]+','-',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip('-')[:120]
def text_hash(text,cta):return hashlib.sha256(json.dumps([norm_text(text),norm_text(cta)],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def core_hash(msgs):
 core=[{'MESSAGE_ID':m['MESSAGE_ID'],'TEXT':m['TEXT'],'CTA_1':m['CTA_1'],'LINK_1':m['LINK_1']} for m in msgs]
 return hashlib.sha256(json.dumps(core,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def parse_links():
 blocks=[];cur=None
 for line,raw in enumerate(TXT.read_text(encoding='utf-8-sig').splitlines(),1):
  s=raw.strip()
  if not s:continue
  if s.lower().startswith(('http://','https://')):
   if cur:cur['links'].append(s)
  elif norm_name(s).startswith('link unico para'):continue
  else:cur={'name':s,'line':line,'links':[]};blocks.append(cur)
 for b in blocks:
  if norm_name(b['name'])==norm_name('Conecta - US-CC-EN/EN-SR - g001-d Icaro') and b['links'] and 'finance.ducapes.com' in b['links'][0]:
   b['name']='Ducapes Finance - US-CC-EN/EN-SR - g001-d Icaro'
 by=defaultdict(list)
 for b in blocks:by[norm_name(b['name'])].append(b)
 return by

def zw(s):return canary.zw_text(s)

JOB_EN={
 'heads':['💼 JOB APPLICATION UPDATE','📋 APPLICATION STATUS READY','🔎 JOB OPTIONS AVAILABLE','✅ REVIEW STEP OPEN','📌 PROFILE CONFIRMATION','💬 JOB MATCH UPDATE','📄 APPLICATION DETAILS','🔔 EMPLOYMENT PROFILE UPDATE','💼 JOB OPTION NOTICE','📋 STATUS CHECK READY','🔎 PROFILE MATCH READY','✅ JOB REVIEW OPEN','📌 APPLICATION REVIEW','💬 DETAILS AVAILABLE','📄 OPTIONS READY','🔔 PROFILE REVIEW','💼 POSITION REVIEW STEP','📋 INFORMATION CONFIRMATION','🔎 JOB RESULT NOTICE','✅ NEXT STEP READY'],
 'bodies':['Your job application has a review step ready. Open the page to continue with the available options.','A status check is available for your employment profile. Review the details before moving forward.','Your job options are ready to compare. Open the update and confirm the next step.','The job recommendation flow has new details available. Check the page to continue.','Your profile review is ready for confirmation. Open the job update to see the result.','A position review step is available now. Review the page and continue from there.','Your application moved to the next review point. Open the status page for details.','The job option summary is ready. Confirm the information on the review page.','A new employment profile update is available. Check the options and continue safely.','Your job match has an available result. Open the update to review the details.','The application review page is ready. Continue there to confirm your profile information.','A job status update is waiting. Open the page and check the available path.'],
 'cta':['💼 REVIEW JOB','✅ CHECK STATUS','📋 SEE OPTIONS','➡️ CONTINUE','🔎 OPEN REVIEW','📌 VIEW DETAILS','✅ CONFIRM DETAILS','📄 SEE RESULT','💼 VIEW PROFILE','🔔 OPEN STATUS','📋 REVIEW RESULT','➡️ NEXT STEP']}
TR_CC={
 'heads':['💳 KART BAŞVURUSU GÜNCELLEMESİ','📋 BAŞVURU DURUMU HAZIR','🔎 KART SEÇENEKLERİ HAZIR','✅ İNCELEME ADIMI AÇIK','📌 PROFİL ONAYI HAZIR','💬 KART EŞLEŞME GÜNCELLEMESİ','📄 BAŞVURU DETAYLARI','🔔 KART PROFİLİ GÜNCELLEMESİ','💳 KART SEÇENEĞİ BİLDİRİMİ','📋 DURUM KONTROLÜ HAZIR','🔎 PROFİL EŞLEŞMESİ HAZIR','✅ KART İNCELEMESİ AÇIK','📌 BAŞVURU İNCELEMESİ','💬 DETAYLAR HAZIR','📄 SEÇENEKLER HAZIR','🔔 PROFİL İNCELEMESİ','💳 KART SEÇİM ADIMI','📋 BİLGİ ONAYI','🔎 KART SONUCU BİLDİRİMİ','✅ SONRAKİ ADIM HAZIR'],
 'bodies':['Kart başvurunuz için bir inceleme adımı hazır. Mevcut seçeneklerle devam etmek için sayfayı açın.','Kart profiliniz için bir durum kontrolü mevcut. Devam etmeden önce detayları inceleyin.','Kart seçenekleriniz karşılaştırmaya hazır. Güncellemeyi açın ve sonraki adımı onaylayın.','Kart öneri sürecinde yeni detaylar mevcut. Devam etmek için sayfayı kontrol edin.','Profil incelemeniz onaya hazır. Sonucu görmek için kart güncellemesini açın.','Şimdi bir kart seçim adımı mevcut. Sayfayı inceleyin ve buradan devam edin.','Kart başvurunuz bir sonraki inceleme noktasına geçti. Detaylar için durum sayfasını açın.','Kart seçeneklerinin özeti hazır. İnceleme sayfasındaki bilgileri onaylayın.','Kart profiliniz için yeni bir güncelleme mevcut. Seçenekleri kontrol edin ve güvenle devam edin.','Kart eşleşmeniz için bir sonuç mevcut. Detayları incelemek için güncellemeyi açın.','Başvuru inceleme sayfası hazır. Kart bilgilerinizi onaylamak için buradan devam edin.','Bir kart durumu güncellemesi bekliyor. Sayfayı açın ve mevcut adımı kontrol edin.'],
 'cta':['💳 KARTI İNCELE','✅ DURUMU KONTROL ET','📋 SEÇENEKLERİ GÖR','➡️ DEVAM ET','🔎 İNCELEMEYİ AÇ','📌 DETAYLARI GÖR','✅ BİLGİLERİ ONAYLA','📄 SONUCU GÖR','💳 KART SEÇENEKLERİ','🔔 DURUMU AÇ','📋 PROFİLİ İNCELE','➡️ SONRAKİ ADIM']}

def generated(vertical_code,idx):
 if vertical_code=='US-JOB-EN':cfg=JOB_EN
 elif vertical_code=='TR-CC-TR':cfg=TR_CC
 else:return canary.generated_copy(vertical_code,idx)
 head=cfg['heads'][idx%len(cfg['heads'])];body=cfg['bodies'][(idx//len(cfg['heads'])+idx)%len(cfg['bodies'])];cta=cfg['cta'][idx%len(cfg['cta'])]
 return f'{head}\n\n{body}',cta

def blank_slot(mid,text,cta,link,base=None):
 base=base or {}
 out={'MESSAGE_ID':mid,'TEXT':text,'DESCRIPTION':base.get('DESCRIPTION',''),'IMAGE':base.get('IMAGE',''),'CTA_1':cta,'LINK_1':link,'CTA_2':base.get('CTA_2',''),'LINK_2':base.get('LINK_2',''),'TEXT_2':base.get('TEXT_2','')}
 return out

def csv_row(m):return {'MESSAGE ID':m['MESSAGE_ID'],'TEXT':m['TEXT'],'DESCRIPTION':m.get('DESCRIPTION',''),'IMAGE':m.get('IMAGE',''),'CTA 1':m['CTA_1'],'LINK 1':m['LINK_1'],'CTA 2':m.get('CTA_2',''),'LINK 2':m.get('LINK_2',''),'TEXT 2':m.get('TEXT_2',''),'APPROVAL':''}

links_by=parse_links();live=json.loads(LIVE.read_text(encoding='utf-8'))['rows'];bank=json.loads(BANK.read_text(encoding='utf-8'));fr=json.loads(FR.read_text(encoding='utf-8'))
prod=[r for r in live if not re.match(r'(?i)^teste[- ]',str(r.get('NAME') or '')) and not re.match(r'(?i)^n[aã]o usar',str(r.get('NAME') or ''))]
approved=defaultdict(list)
for h,rec in bank.get('records',{}).items():
 if rec.get('status')=='approved' and rec.get('text') and rec.get('cta_1'):approved[rec.get('vertical','')].append((h,rec))
for v in approved:approved[v].sort(key=lambda x:(-int(x[1].get('approved_count') or 0),x[1].get('text','')))

(RUN/'csv').mkdir(parents=True,exist_ok=True);(RUN/'backups').mkdir(parents=True,exist_ok=True)
plan=[];generated_records={};errors=[]
for row in sorted(prod,key=lambda r:r['NAME']):
 name=row['NAME'];v=vertical(name);old=sorted(parse_msgs(row),key=lambda m:int(m.get('MESSAGE_ID') or 0));pages=int(row.get('PAGES') or 0);target=30 if pages>0 or name==SPECIAL else 23
 blocks=links_by.get(norm_name(name),[])
 if len(blocks)!=1:errors.append(f'{name}: link blocks {len(blocks)}');continue
 raw_links=blocks[0]['links']
 if len(raw_links)==1:slot_links=[raw_links[0]]*target
 elif len(raw_links)==23:slot_links=[raw_links[i%23] for i in range(target)]
 else:errors.append(f'{name}: links {len(raw_links)}');continue
 used_old={norm_text(m.get('TEXT') or '') for m in old};used=set();final=[];sources=[];gen_counter=[0]
 def get_candidate(mid):
  for h,rec in approved.get(v,[]):
   nt=norm_text(rec['text'])
   if nt and nt not in used and nt not in used_old:
    used.add(nt);return rec['text'],rec['cta_1'],'approved_bank',h
  for _ in range(2000):
   text,cta=generated(v,gen_counter[0]);gen_counter[0]+=1;nt=norm_text(text)
   if nt and nt not in used and nt not in used_old:
    used.add(nt);h=text_hash(text,cta)
    generated_records.setdefault(h,{'text_cta_hash':h,'vertical':v,'country':v.split('-')[0],'language':v.split('-')[-1],'text':text,'cta_1':cta,'first_seen_at':now(),'last_seen_at':now(),'first_approved_at':None,'last_approved_at':None,'approved_count':0,'rejected_count':0,'gray_count':0,'purple_count':0,'status':'testing','seen_in':[],'usage':[]})
    return text,cta,'generated',h
  raise RuntimeError(f'{name}: no unique candidate')
 if name==SPECIAL:
  if len(fr)!=30:raise RuntimeError('French translation count != 30')
  for i,x in enumerate(fr,1):
   nt=norm_text(x['text'])
   if nt in used:raise RuntimeError(f'{name}: duplicate French text')
   used.add(nt);h=text_hash(x['text'],x['cta_1']);generated_records.setdefault(h,{'text_cta_hash':h,'vertical':v,'country':'CA','language':'FR','text':x['text'],'cta_1':x['cta_1'],'first_seen_at':now(),'last_seen_at':now(),'first_approved_at':None,'last_approved_at':None,'approved_count':0,'rejected_count':0,'gray_count':0,'purple_count':0,'status':'testing','seen_in':[],'usage':[]})
   final.append(blank_slot(i,x['text'],x['cta_1'],slot_links[i-1]));sources.append({'message_id':i,'source':'translated_CA-CC-EN','hash':h,'old_color':color(old[0]) if i==1 and old else None})
 else:
  for idx,m in enumerate(old,1):
   mid=int(m.get('MESSAGE_ID') or idx)
   keep=(pages==0 or color(m)=='green')
   if keep:
    text=m.get('TEXT') or '';cta=m.get('CTA_1') or m.get('CTA 1') or '';nt=norm_text(text)
    if nt in used:errors.append(f'{name}: duplicate existing kept text mid {mid}')
    used.add(nt);h=text_hash(text,cta);src='preserved_'+color(m)
   else:text,cta,src,h=get_candidate(mid)
   final.append(blank_slot(mid,text,cta,slot_links[mid-1],m));sources.append({'message_id':mid,'source':src,'hash':h,'old_color':color(m)})
  for mid in range(len(old)+1,target+1):
   text,cta,src,h=get_candidate(mid);final.append(blank_slot(mid,text,cta,slot_links[mid-1]));sources.append({'message_id':mid,'source':src,'hash':h,'old_color':None})
 if len(final)!=target:errors.append(f'{name}: final count {len(final)} != {target}');continue
 ids=[m['MESSAGE_ID'] for m in final]
 if ids!=list(range(1,target+1)):errors.append(f'{name}: nonsequential ids');continue
 texts=[norm_text(m['TEXT']) for m in final]
 if len(texts)!=len(set(texts)):errors.append(f'{name}: final duplicate visible text');continue
 if any(not m['TEXT'] or not m['CTA_1'] or not m['LINK_1'] for m in final):errors.append(f'{name}: empty required field');continue
 if [m['LINK_1'] for m in final]!=slot_links:errors.append(f'{name}: link order mismatch');continue
 slug=safe(name);backup=RUN/'backups'/f'{slug}.json';backup.write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 csvp=RUN/'csv'/f'{slug}.csv'
 with csvp.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=CSV_FIELDS,lineterminator='\r\n',quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(csv_row(m) for m in final)
 counts=Counter(color(m) for m in old);source_counts=Counter(s['source'] for s in sources)
 plan.append({'name':name,'id':row['ID'],'company':row.get('COMPANY'),'pages':pages,'vertical':v,'before_count':len(old),'target_count':target,'before_colors':dict(counts),'replace_ids':[s['message_id'] for s in sources if s['old_color'] in ('red','gray','purple') and not s['source'].startswith('preserved')],'append_ids':list(range(len(old)+1,target+1)),'source_counts':dict(source_counts),'raw_link_count':len(raw_links),'before_core_hash':core_hash([blank_slot(int(m.get('MESSAGE_ID') or i),m.get('TEXT') or '',m.get('CTA_1') or m.get('CTA 1') or '',m.get('LINK_1') or m.get('LINK 1') or '',m) for i,m in enumerate(old,1)]),'after_core_hash':core_hash(final),'backup':str(backup),'csv':str(csvp),'messages':final,'sources':sources,'requires_approval':pages>0})

if errors:
 print(json.dumps({'status':'BLOCKED','errors':errors},ensure_ascii=False,indent=2));raise SystemExit(2)
# Attach planned usage to generated records only; actual canonical bank update happens after validated apply.
for item in plan:
 for s in item['sources']:
  if s['hash'] in generated_records:
   generated_records[s['hash']]['usage'].append({'template':item['name'],'message_id':s['message_id'],'planned_at':now(),'mode':'sb_23_30_rollout'})
summary={'status':'READY','created_at_et':now(),'scope':{'templates':len(plan),'linked':sum(x['requires_approval'] for x in plan),'unlinked':sum(not x['requires_approval'] for x in plan),'target_30':sum(x['target_count']==30 for x in plan),'target_23':sum(x['target_count']==23 for x in plan)},'totals':{'replacements':sum(len(x['replace_ids']) for x in plan),'appended':sum(len(x['append_ids']) for x in plan),'generated_slot_uses':sum(x['source_counts'].get('generated',0)+x['source_counts'].get('translated_CA-CC-EN',0) for x in plan),'approved_bank_slot_uses':sum(x['source_counts'].get('approved_bank',0) for x in plan),'generated_unique_records':len(generated_records)},'errors':[]}
(RUN/'plan.json').write_text(json.dumps({'summary':summary,'templates':plan},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(RUN/'generated-candidates.json').write_text(json.dumps({'created_at_et':now(),'records':generated_records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
