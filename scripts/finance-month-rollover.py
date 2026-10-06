#!/usr/bin/env python3
"""Last-day configuration carry, first-import verification; no financial fact copying."""
import argparse,datetime,fcntl,json,pathlib,shlex,sys,time
from zoneinfo import ZoneInfo
REPO=pathlib.Path('/root/mgs-agent');APP=REPO/'apps/finance-system';sys.path.insert(0,str(APP))
from finance_release_guard import lease
import finance_gam_revenue_sync as transport
AUTH='1555579357651537931';TZ=ZoneInfo('America/New_York');STATE=REPO/'data/finance-month-rollover-state.json'
def previous(p):
 d=datetime.date.fromisoformat(p+'-01')-datetime.timedelta(days=1);return d.strftime('%Y-%m')
def selection(now,scheduled=False,ensure=None):
 tomorrow=now.date()+datetime.timedelta(days=1)
 if scheduled:return (now.strftime('%Y-%m'),tomorrow.strftime('%Y-%m')) if tomorrow.month!=now.month else None
 if ensure:
  assert ensure in {now.strftime('%Y-%m'),(now.date()-datetime.timedelta(days=1)).strftime('%Y-%m')},'ensure must target report month';return previous(ensure),ensure
 return None
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scheduled',action='store_true');ap.add_argument('--ensure-period');ap.add_argument('--from-period');ap.add_argument('--to-period');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--recalc',action='store_true');ap.add_argument('--stage',action='store_true');a=ap.parse_args();now=datetime.datetime.now(TZ)
 if a.scheduled or a.ensure_period:
  assert not(a.from_period or a.to_period or a.recalc or a.stage);pair=selection(now,a.scheduled,a.ensure_period)
  if pair is None:print(json.dumps({'pass':True,'status':'not_last_day','writes':0}));return 0
 else:
  assert a.from_period and a.to_period;pair=(a.from_period,a.to_period)
 source,target=pair;assert target>='2026-10';assert datetime.date.fromisoformat(source+'-01')<datetime.date.fromisoformat(target+'-01')
 mode='plan' if a.dry_run else ('recalc' if a.recalc else 'apply');db='mgs_finance_monthroll_'+AUTH if a.stage else 'mgs_finance';root='/var/tmp/mgs-finance-monthroll-'+AUTH if a.stage else transport.TARGET;node=root+'/node' if a.stage else transport.NODE;user='mgs_pg' if a.stage else 'mgsfinance'
 code=(REPO/'scripts/finance-month-rollover-core.mjs').read_text().replace('export ','')+'\n'+(REPO/'scripts/finance-month-rollover-remote.mjs').read_text();payload={'mode':mode,'from':source,'to':target,'database':db}
 cmd='sudo -n -u '+user+' /bin/sh -c '+shlex.quote('cd '+shlex.quote(root)+' && '+shlex.quote(node)+' --input-type=module -e '+shlex.quote(code))
 folder=APP/'private/month-rollover-runs'/now.strftime('%Y%m%dT%H%M%S%f%z');folder.mkdir(parents=True,mode=0o700)
 with lease(APP,timeout=120),(APP/'private/month-rollover.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  with transport.QUOTE_LOCK.open('a') as qlock:
   fcntl.flock(qlock,fcntl.LOCK_EX);out=None
   for attempt in range(2):
    try:out=json.loads(transport.ssh(cmd,json.dumps(payload).encode(),timeout=360));break
    except Exception as exc:
     transport.atomic_json(folder/('failure-'+str(attempt)+'.json'),{'type':type(exc).__name__,'detail':str(exc)[:1500]})
     if attempt:raise
     time.sleep(1)
  transport.atomic_json(folder/'result.json',out);assert out is not None;st={}
  if not(a.dry_run or a.stage):
   st=json.loads(STATE.read_text()) if STATE.exists() else {'version':1,'months':{}};bucket='sms_basis_recalculation' if a.recalc else 'months';st.setdefault(bucket,{})[target]={'status':'ok' if out['pass'] else 'blocked','from':source,'verified_at':now.isoformat(),'result':str(folder/'result.json'),'audit_id':out.get('audit_id'),'authority':'1556898264878419969' if target>='2026-11' and not a.recalc else AUTH};transport.atomic_json(STATE,st)
  if not out['pass'] and a.scheduled and not(a.dry_run or a.stage):
   signature=transport.digest({'target':target,'blocked':out.get('blocked',[])})
   if st.get('last_blocked_signature')!=signature:
    items=['Não transportei configurações ambíguas de '+source+' para '+target+'. Os dados existentes foram preservados.']
    for i,x in enumerate(out.get('blocked',[]),1):items.append(str(i)+'. '+str(x.get('name',x.get('id')))+': '+str(x.get('reason'))+'. Falta confirmar o destino correto dessa conta.')
    proof=transport.notice(json.loads(transport.CONTRACT.read_text()),'Virada financeira — vínculo a confirmar','\n'.join(items),attention=True,signature=signature);st.update(last_blocked_signature=signature,last_notice=proof);transport.atomic_json(STATE,st)
  print(json.dumps({**out,'evidence':str(folder)},ensure_ascii=False));return 0 if out['pass'] else 2
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as exc:
  # Recovery cannot invent mappings, change permissions or bypass revision guards.
  diagnostic={'pass':False,'error':type(exc).__name__,'detail':str(exc)[:1400]};print(json.dumps(diagnostic,ensure_ascii=False))
  if '--scheduled' in sys.argv and '--dry-run' not in sys.argv:
   contract=json.loads(transport.CONTRACT.read_text());transport.notice(contract,'Virada financeira — intervenção necessária','A conferência de fim de mês não concluiu após nova tentativa segura. Nenhum vínculo ambíguo foi escolhido. Diagnóstico: '+type(exc).__name__+'. Zeus deve conferir a evidência em private/month-rollover-runs antes de retomar.',attention=True,signature=transport.digest(diagnostic))
  sys.exit(1)
