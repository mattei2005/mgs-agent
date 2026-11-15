#!/usr/bin/env python3
"""Joe's finite, read-only CPR + adjusted-SB ROI updates."""
import argparse, fcntl, importlib.util, json, sys, subprocess
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal, DecimalException
HOME=Path('/root/.hermes/profiles/ares'); BASE=Path('/root/mgs-agent')
REQUEST='1571247080448720938'; AID='781612907182683'; TID='1558147211026501643'; USER='1214246869484576890'
ROOT=BASE/'data/ares/meta-ads/state/cpr-roi-updates'/REQUEST
DAY='2026-11-14'; NY=ZoneInfo('America/New_York')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
core=module('cpr_roi_core',HOME/'scripts/shein-g004-cpr-updates-20261111.py')
load=core.load
def save(path,value):
    return core.save(path,json.loads(json.dumps(value,default=str)))
finance=module('cpr_roi_finance',HOME/'scripts/shein_financial_source.py')
def applicable(m,at):
    return at.astimezone(NY).date().isoformat()==m['date'] and at<datetime.fromisoformat(m['expires_at'])
def slot(m,at):
    xs=[datetime.fromisoformat(s) for s in m['slots'] if datetime.fromisoformat(s)<=at<datetime.fromisoformat(s)+timedelta(minutes=10)]
    return xs[-1].strftime('%H%M') if xs and applicable(m,at) else None
def candidates(rows,at):
    out={}
    for c in rows:
        assert c['account_id']==AID,'Discovery identity mismatch'
        created=datetime.fromisoformat(c['created_time']).astimezone(NY)
        if created.date().isoformat()!=DAY or created>at:continue
        number=c['name'].split(' - ')[0];assert number.isdigit()
        assert c['id'] not in out
        out[c['id']]={**c,'number':number,'membership_source':'created_today'}
    return out
def scope(m):
    assert (m['request_id'],m['account_id'],m['thread_id'],m['date'],m['requester_discord_id'])==(REQUEST,AID,TID,DAY,USER)
    assert m['mode']=='finite_read_only_periodic_cpr_roi' and not m['meta_writes']
    for cmd in [[sys.executable,str(BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',AID,'--json'],[sys.executable,str(BASE/'scripts/mgs-domain-scope.py'),'check','--agent','ares','yolokfx.com']]:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=30);assert p.returncode==0
        if '--json' in cmd:assert json.loads(p.stdout)['allowed']
    assert USER in load(BASE/'data/authorized-users.json')['agents']['ares']['authorized_user_discord_ids']
    b=next(x for x in load(BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if x['thread_id']==TID)
    assert b['account_id']==AID and b['channel_id']==m['parent_id']
    return b
def helpers():return core.helpers()
def collect(d,m,run,b):
    r=d.Runner({'policy_id':REQUEST},run,[b],DAY)
    a=r.source(run,'account',lambda:r.graph('act_'+AID,{'fields':'id,name,currency,timezone_name'}))
    assert (a['id'].removeprefix('act_'),a['name'],a['currency'],a['timezone_name'])==(AID,m['account_name'],'USD',str(NY))
    cs=r.source(run,'discovery-campaigns',lambda:r.paged('act_'+AID+'/campaigns',{'fields':'id,name,account_id,created_time,status,configured_status,effective_status','filtering':json.dumps([{'field':'effective_status','operator':'IN','value':['ACTIVE','PAUSED','DELETED','ARCHIVED','IN_PROCESS','WITH_ISSUES']}]),'limit':500}))
    stamp=load(run/'discovery-campaigns-observed-at.json')['observed_at']
    fresh=candidates(cs,datetime.fromisoformat(stamp))
    members={c['id']:dict(c) for c in m.get('campaigns',[])};members.update(fresh)
    for c in m['edited_campaigns']:members.setdefault(c['id'],dict(c))
    cm={c['id']:c for c in cs};ids=sorted(members)
    for cid in set(ids)-set(cm):
        try:obj=r.source(run,'recover-'+cid,lambda cid=cid:r.graph(cid,{'fields':'id,name,account_id,created_time,status,configured_status,effective_status'}))
        except RuntimeError:continue
        assert obj['id']==cid and obj['account_id']==AID;cm[cid]=obj
    assert all(c['account_id']==AID for c in members.values())
    filt=json.dumps([{'field':'campaign.id','operator':'IN','value':ids}])
    sets=r.source(run,'adsets',lambda:r.paged('act_'+AID+'/adsets',{'fields':'id,account_id,campaign_id,optimization_goal,promoted_object','filtering':filt,'limit':500})) if ids else []
    assert all(s['account_id']==AID and s['campaign_id'] in ids for s in sets)
    pending={};valid=[]
    for cid in ids:
        ss=[s for s in sets if s['campaign_id']==cid]
        if cid not in cm:pending[cid]='campanha temporariamente indisponível'
        elif not ss:pending[cid]='estrutura indisponível'
        elif not all(s.get('optimization_goal')=='OFFSITE_CONVERSIONS' and s.get('promoted_object',{}).get('custom_event_type')=='ADD_TO_WISHLIST' for s in ss):pending[cid]='evento não confirmado'
        else:valid.append(cid)
    insights=r.source(run,'insights',lambda:r.paged('act_'+AID+'/insights',{'level':'campaign','time_range':json.dumps({'since':DAY,'until':DAY}),'use_unified_attribution_setting':'true','fields':'campaign_id,spend,impressions,actions,cost_per_action_type','filtering':json.dumps([{'field':'campaign.id','operator':'IN','value':valid}]),'limit':500})) if valid else []
    im={x['campaign_id']:x for x in insights};assert len(im)==len(insights) and set(im)<=set(valid)
    assert all(x['date_start']==x['date_stop']==DAY for x in insights)
    rows={}
    for cid,c in members.items():
        values={'spend':None,'results':None,'cpr':None}
        if cid in valid:
            try:values=core.metric(im.get(cid,{}))
            except (AssertionError,ValueError,TypeError,DecimalException):pending[cid]='métrica pendente de reconciliação'
        rows[cid]={'id':cid,'number':c['number'],'status':cm.get(cid,{}).get('status','n/d'),'pending':pending.get(cid),**values,'roi':None}
    sb_at=None;financial_error=None;delay=None
    if ids:
        try:
            r.publishers();pub=r.pub['yolokfx.com'];assert pub['publisherId']=='digital-trust_yolokfx'
            def sbrows():
                data=r.sbquery('/report/performance_per_campaigns',{'initialDate':DAY+'T00:00:00.000Z','finalDate':DAY+'T23:59:59.999Z','publishers':[pub['publisherId']],'currency':'USD'})
                assert isinstance(data,list)
                return finance.scoped_evidence([x for x in data if str(x.get('CUSTOMER_ID','')).removeprefix('act_')==AID and str(x.get('CAMPAIGN_ID','')) in ids and str(x.get('DATE',''))[:10]==DAY and x.get('PUBLISHER')==pub['publisherId'] and x.get('DOMAIN') in (pub['name'],'yolokfx.com')],AID,[DAY])
            sb=r.source(run,'sb',sbrows);sb_at=load(run/'sb-observed-at.json')['observed_at']
            model={'account':a,'date':DAY,'history_dates':[DAY],'source_timestamps':{'sb':sb_at,'insights':load(run/'insights-observed-at.json')['observed_at'] if valid else stamp},'rows':[{'id':cid,'number':c['number'],'spend':im.get(cid,{}).get('spend','0'),'history':[]} for cid,c in members.items()]}
            cfg=r.layout.policy();finance.apply_financial_source(model,sb,cfg);assert finance.validate_financial_source(model,cfg)
            save(run/'financial-model.json',model)
            for x in model['rows']:
                rows[x['id']].update(roi=str(x['roi']) if x['roi'] is not None else None,financial_spend=str(x['spend']) if x['spend'] is not None else None,net_revenue=str(x['net_revenue']) if x['net_revenue'] is not None else None)
        except (RuntimeError,AssertionError,ValueError) as exc:
            financial_error=type(exc).__name__;save(run/'financial-pending.json',{'error_class':financial_error,'recoverable':True})
        try:delay=r.source(run,'delay',lambda:r.sbquery('/estimated/delay',{'publisherIds':['digital-trust_yolokfx'],'currency':'USD'}))
        except (RuntimeError,AssertionError):pass
    snap={'rows':rows,'observed_at':load(run/'insights-observed-at.json')['observed_at'] if valid else stamp,'sb_at':sb_at,'campaigns':list(members.values()),'pending':pending,'financial_error':financial_error,'delay':delay}
    save(run/'snapshot.json',snap);return snap
def text(snap):
    at=datetime.fromisoformat(snap['observed_at']).astimezone(NY).strftime('%H:%M %Z')
    sbat=datetime.fromisoformat(snap['sb_at']).astimezone(NY).strftime('%H:%M %Z') if snap.get('sb_at') else 'n/d'
    lines=['**CPR e ROI — Yolokfx Conta 04 · G004**',f'14/11/2026 · Meta até {at} · SB até {sbat} · USD · acumulado do dia']
    fmt=lambda v:format(Decimal(v),'.2f').replace('.',',')
    for row in sorted(snap['rows'].values(),key=lambda x:int(x['number'])):
        cpr='US$ '+fmt(row['cpr']) if row['cpr'] is not None else 'n/d'
        roi=fmt(row['roi'])+'%' if row['roi'] is not None else 'n/d'
        qty=row.get('results') or '0';spend='US$ '+fmt(row['spend']) if row['spend'] is not None else 'n/d'
        lines.append(f"- **C{row['number']}** · CPR **{cpr}** · ROI **{roi}** · gasto Meta {spend} · resultados {qty if not row['pending'] else 'n/d'} · {row['status']}"+(f" · {row['pending']}" if row['pending'] else ''))
    if not snap['rows']:lines.append('Nenhuma campanha elegível encontrada neste corte; descoberta futura mantida.')
    delay=snap.get('delay') or {};mins=delay.get('totalMinutes');delaystr=str(mins)+' min' if mins is not None and not (mins==0 and not delay.get('currentFillTime') and not delay.get('confident')) else 'n/d'
    lines+=['**Fontes:** CPR = gasto Meta ÷ adições à lista de desejos no site; ROI real = (receita líquida SB ÷ investimento SB já ajustado − 1) × 100.',f'Subidas hoje, incluindo próximas publicações, e alterações de hoje confirmadas até o pedido. Pausadas permanecem no acompanhamento. Atraso GAM/SB: {delaystr}.','CPR sem resultados e ROI sem base financeira válida = n/d. Parciais sujeitos à atribuição/atraso de receita; não isolam o efeito da alteração. Somente leitura.']
    return core.w.split_parts(['\n'.join(lines)])
def execute(args,at=None):
    m=load(ROOT/'manifest.json');at=at or datetime.now(NY)
    if not applicable(m,at):return {'status':'EXPIRED','api_calls':0}
    key='initial' if args.initial else slot(m,at)
    if args.dry_run:key='dry-'+at.strftime('%H%M%S')
    if not key:return {'status':'NOT_DUE','api_calls':0}
    run=ROOT/'runs'/key;run.mkdir(parents=True,exist_ok=True,mode=0o700)
    if (run/'complete.json').exists():return load(run/'complete.json')
    b=scope(m);d,delivery=helpers()
    snap=load(run/'snapshot.json') if (run/'snapshot.json').exists() else collect(d,m,run,b)
    parts=text(snap);save(run/'update-parts.json',parts)
    result={'status':'LIVE_DRY_RUN_OK' if args.dry_run else 'COMPLETE_GET_VERIFIED','campaigns':len(snap['rows']),'observed_at':snap['observed_at'],'sb_at':snap['sb_at'],'pending':snap['pending'],'financial_error':snap['financial_error'],'meta_writes':0,'posted':False,'rows':snap['rows']}
    if args.dry_run:save(run/'preflight.json',result);return result
    m.update(campaigns=snap['campaigns'],last_discovery_at=snap['observed_at']);save(ROOT/'manifest.json',m)
    delivery.deliver(d,m,run,parts);result['posted']=True
    save(run/'complete.json',result);save(ROOT/'state.json',{'last_run':key,'observed_at':snap['observed_at'],'expires_at':m['expires_at']});return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--initial',action='store_true');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (ROOT/'run.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        try:
            result=execute(a)
            if a.initial or a.dry_run:print(json.dumps(result,ensure_ascii=False))
        except Exception as exc:
            save(ROOT/'last-error.json',{'at':datetime.now(NY).isoformat(),'error_class':type(exc).__name__,'resumable':True})
            if not a.dry_run:
                m=load(ROOT/'manifest.json')
                if applicable(m,datetime.now(NY)):
                    d,delivery=helpers();run=ROOT/'errors'/datetime.now(NY).strftime('%H%M');run.mkdir(parents=True,exist_ok=True)
                    delivery.deliver(d,m,run,['⚠️ Yolokfx Conta 04: atualização de CPR/ROI temporariamente indisponível; leitura pendente de recuperação, sem valores presumidos e sem alterações nas campanhas.'])
            raise SystemExit('Atualização pendente; diagnóstico protegido registrado.') from None
if __name__=='__main__':main()
