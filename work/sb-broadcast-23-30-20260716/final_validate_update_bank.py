#!/usr/bin/env python3
import argparse,datetime as dt,json,re,shutil,unicodedata
from collections import Counter
from pathlib import Path
from zoneinfo import ZoneInfo
BASE=Path('/root/mgs-agent');RUN=BASE/'work/sb-broadcast-23-30-20260716';PLAN=RUN/'plan.json';GEN=RUN/'generated-candidates.json';BANK=BASE/'data/utility-message-bank.json';TZ=ZoneInfo('America/New_York');ROLLOUT='sb-broadcast-23-30-20260716'
def now():return dt.datetime.now(TZ).isoformat(timespec='seconds')
def visible(s):return re.sub('[\u200b\u200c\u200d\ufeff\u2060]','',s or '')
def nt(s):return re.sub(r'\s+',' ',visible(s).strip().lower())
def msgs(r):
 x=r.get('MESSAGES') or [];return json.loads(x) if isinstance(x,str) else x
def core(z):return [{'MESSAGE_ID':int(q.get('MESSAGE_ID') or 0),'TEXT':q.get('TEXT') or '','CTA_1':q.get('CTA_1') or q.get('CTA 1') or '','LINK_1':q.get('LINK_1') or q.get('LINK 1') or ''} for q in z]
def color(m):
 if int(m.get('INVALID_FORMAT') or 0)>0 or int(m.get('ERROR') or 0)>0:return 'purple'
 if int(m.get('REJECTED') or 0)>0:return 'red'
 if int(m.get('APPROVED') or 0)>0:return 'green'
 return 'gray'
def status_name(c):return {'green':'APPROVED','red':'REJECTED','purple':'INVALID_OR_ERROR','gray':'GRAY'}[c]
def color_pt(c):return {'green':'verde','red':'vermelho','purple':'roxo','gray':'cinza'}[c]
ap=argparse.ArgumentParser();ap.add_argument('--live',required=True);ap.add_argument('--apply-bank',action='store_true');a=ap.parse_args()
plan=json.loads(PLAN.read_text(encoding='utf-8'))['templates'];live=json.loads(Path(a.live).read_text(encoding='utf-8'));rows=live.get('rows') or live.get('templates') or live
byid={r.get('ID'):r for r in rows};errors=[];statuses=Counter();linked_status=Counter();unlinked_status=Counter();observations=[]
for x in plan:
 r=byid.get(x['id'])
 if not r:errors.append(f"missing {x['name']}");continue
 lm=sorted(msgs(r),key=lambda m:int(m.get('MESSAGE_ID') or 0));expected=core(x['messages']);actual=core(lm)
 if actual!=expected:errors.append(f"core mismatch {x['name']}: live={len(actual)} expected={len(expected)}");continue
 if len({nt(m['TEXT']) for m in lm})!=len(lm):errors.append(f"duplicate text {x['name']}")
 for m in lm:
  c=color(m);statuses[c]+=1;(linked_status if x['requires_approval'] else unlinked_status)[c]+=1
 sources={int(s['message_id']):s for s in x['sources']}
 for m in lm:
  s=sources.get(int(m.get('MESSAGE_ID') or 0))
  if s and not s['source'].startswith('preserved_'):
   observations.append({'hash':s['hash'],'source':s['source'],'vertical':x['vertical'],'template':x['name'],'message_id':int(m['MESSAGE_ID']),'pages':x['pages'],'color':color(m)})
report={'status':'OK' if not errors else 'BLOCKED','validated_templates':len(plan)-len(errors),'planned_templates':len(plan),'linked_templates':sum(x['requires_approval'] for x in plan),'unlinked_templates':sum(not x['requires_approval'] for x in plan),'message_status_total':dict(statuses),'linked_status':dict(linked_status),'unlinked_status':dict(unlinked_status),'observations_for_bank':len(observations),'errors':errors}
if errors:
 print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(2)
if a.apply_bank:
 # Final fresh snapshot closes any per-template readbacks that were stale in the long-lived UI session.
 journal_path=RUN/'journal.jsonl';jr=[json.loads(s) for s in journal_path.read_text(encoding='utf-8').splitlines() if s.strip()] if journal_path.exists() else [];validated={r.get('template') for r in jr if r.get('status')=='validated'};journal_added=0
 with journal_path.open('a',encoding='utf-8') as jf:
  for x in plan:
   if x['name'] not in validated:
    jf.write(json.dumps({'at_et':now(),'template':x['name'],'id':x['id'],'status':'validated','target':x['target_count'],'pages':x['pages'],'approval_clicked':x['requires_approval'],'verification':'final fresh Ares API core readback matched plan'},ensure_ascii=False)+'\n');journal_added+=1
 report['journal_final_validations_added']=journal_added
 bank=json.loads(BANK.read_text(encoding='utf-8'));gen=json.loads(GEN.read_text(encoding='utf-8'))['records'];records=bank.setdefault('records',{});ts=now();added=0;updated=0;new_obs=0
 backup=RUN/f'utility-message-bank.before-{ts.replace(":","").replace("-","")}.json';shutil.copy2(BANK,backup)
 for o in observations:
  h=o['hash'];rec=records.get(h)
  if rec is None:
   if h not in gen:errors.append(f'missing generated bank source {h}');continue
   rec=json.loads(json.dumps(gen[h]));rec['usage']=[];rec['seen_in']=[];records[h]=rec;added+=1
  else:updated+=1
  usage=rec.setdefault('usage',[]);seen=rec.setdefault('seen_in',[])
  key=(ROLLOUT,o['template'],o['message_id'])
  exists=any((u.get('rollout'),u.get('template'),int(u.get('message_id') or 0))==key for u in usage)
  if exists:continue
  c=o['color'];usage.append({'rollout':ROLLOUT,'template':o['template'],'message_id':o['message_id'],'installed_at':ts,'mode':'broadcast_23_30_rollout','source':o['source']})
  seen.append({'rollout':ROLLOUT,'template':o['template'],'message_id':o['message_id'],'observed_color':color_pt(c),'observed_status':status_name(c),'observed_at':ts})
  field={'green':'approved_count','red':'rejected_count','gray':'gray_count','purple':'purple_count'}[c];rec[field]=int(rec.get(field) or 0)+1;rec['last_seen_at']=ts
  if c=='green':
   rec['last_approved_at']=ts;rec['first_approved_at']=rec.get('first_approved_at') or ts;rec['status']='approved'
  elif rec.get('status')!='approved':rec['status']={'red':'rejected','purple':'purple','gray':'testing'}[c]
  new_obs+=1
 if errors:
  print(json.dumps({**report,'status':'BLOCKED_BANK','errors':errors},ensure_ascii=False,indent=2));raise SystemExit(3)
 bank.setdefault('_meta',{})['updated_at']=ts;bank['_meta']['last_rollout']=ROLLOUT
 tmp=RUN/'utility-message-bank.after.json';tmp.write_text(json.dumps(bank,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');json.loads(tmp.read_text(encoding='utf-8'));shutil.copy2(tmp,BANK)
 reread=json.loads(BANK.read_text(encoding='utf-8'))
 if reread.get('_meta',{}).get('last_rollout')!=ROLLOUT:raise SystemExit('bank readback failed')
 report['bank_update']={'added_records':added,'existing_records_touched':updated,'new_observations':new_obs,'backup':str(backup),'records_after':len(reread.get('records',{})),'readback':True}
(RUN/'final-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
