#!/usr/bin/env python3
"""Joe's finite, read-only CPR + adjusted-SB ROI updates."""
import argparse, fcntl, importlib.util, json, sys, subprocess
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal, DecimalException
HOME=Path('/root/.hermes/profiles/ares'); BASE=Path('/root/mgs-agent')
REQUEST='1575977166632390947'; AID='781612907182683'; TID='1558147211026501643'; USER='1214246869484576890'
ROOT=BASE/'data/ares/meta-ads/state/cpr-roi-updates'/REQUEST
DAY='2026-11-27'; NY=ZoneInfo('America/New_York')
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
        if created.date().isoformat()!=DAY or created>at :continue
        number=c['name'].split(' - ')[0];assert number.isdigit()
        assert c['id'] not in out
        out[c['id']]={**c,'number':number,'membership_source':'created_today'}
    return out
def scope(m):
    assert (m['request_id'],m['account_id'],m['thread_id'],m['date'],m['requester_discord_id'])==(REQUEST,AID,TID,DAY,USER)
    assert m['mode']=='finite_read_only_periodic_cpr_roi' and not m['meta_writes']
    assert not m['dynamic_discovery']['enabled'] and not m['discover_future_edits']
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
    assert m['cohort_frozen'] and not m['dynamic_discovery']['enabled']
    members={c['id']:dict(c) for c in m.get('campaigns',[])}
    assert len(members)==len(m['campaigns'])
    ids=sorted(members)
    stamp=datetime.now(NY).isoformat()
    def current():
        out={}
        for offset in range(0,len(ids),50):
            chunk=ids[offset:offset+50]
            st,children,_=r.meta.graph_batch_get(r.token,[{'path':cid,'params':{'fields':'id,name,account_id,created_time,status,configured_status,effective_status'}} for cid in chunk])
            assert st==200 and len(children)==len(chunk)
            for cid,ch in zip(chunk,children):
                if ch['code']!=200:continue
                obj=json.loads(ch['body']) if isinstance(ch['body'],str) else ch['body']
                assert obj['id']==cid and obj['account_id']==AID
                assert datetime.fromisoformat(obj['created_time'])==datetime.fromisoformat(members[cid]['created_time'])
                member=members[cid]
                if member['membership_source']=='created_today':assert cid in candidates([obj],datetime.fromisoformat(m['request_time']))
                else:assert cid in {c['id'] for c in m['edited_campaigns']} and member.get('edit_evidence')
                out[cid]=obj
        return out
    cm=r.source(run,'frozen-campaigns',current) if ids else {}
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
    title=['**📊 Yolokfx Conta 04 · G004 — CPR + ROI**',f'27/11/2026 · Meta até {at} · SB até {sbat} · USD · acumulado do dia']
    fmt=lambda v:format(Decimal(str(v)),'.2f').replace('.',',')
    origins={str(c['id']):c.get('membership_source','explicitly_requested') for c in snap.get('campaigns',[])}
    statuses={'ACTIVE':'Ativa','PAUSED':'Paus.','DELETED':'Excl.','ARCHIVED':'Arq.'}
    groups=[];notes=[]
    for origin,label in [('explicitly_requested','📌 Campanhas solicitadas'),('created_today','🆕 Novas de hoje'),('edited_today','🔄 Alteradas hoje')]:
        cells=[]
        for cid,row in sorted(snap['rows'].items(),key=lambda pair:int(pair[1]['number'])):
            if origins.get(str(cid),'explicitly_requested')!=origin:continue
            cpr=fmt(row['cpr']) if row['cpr'] is not None else 'n/d'
            roi=format(Decimal(str(row['roi'])),'+.2f').replace('.',',')+'%' if row['roi'] is not None else 'n/d'
            qty=(row.get('results') or '0') if not row['pending'] else 'n/d';spend=fmt(row['spend']) if row['spend'] is not None else 'n/d'
            cells.append((f"C{row['number']}",statuses.get(row['status'],row['status']),cpr,spend,str(qty),roi))
            if row['pending']:notes.append(f"C{row['number']}: CPR pendente — {row['pending']}.")
        if cells:groups.append((label,cells))
    if not snap['rows']:notes.append('Nenhuma campanha elegível na seleção congelada do pedido.')
    delay=snap.get('delay') or {};mins=delay.get('totalMinutes');delaystr=str(mins)+' min' if mins is not None and not (mins==0 and not delay.get('currentFillTime') and not delay.get('confident')) else 'n/d'
    notes+=['**Fontes:** CPR = gasto Meta ÷ adições à lista de desejos no site; ROI real = (receita líquida SB ÷ investimento SB já ajustado − 1) × 100. Gasto = Meta; Res. = resultados atribuídos; valores monetários em USD.',f"Campanhas novas de hoje e alterações materiais registradas até {datetime.fromisoformat(load(ROOT/'manifest.json')['request_time']).astimezone(NY).strftime('%H:%M %Z')}, seleção congelada sem repetir IDs. Pausadas permanecem no acompanhamento. ⏱️ **Atraso GAM/SB: {delaystr}.**",'CPR sem resultados e ROI sem base financeira válida = n/d. Acumulado do dia, não apenas após a alteração. Histórico Meta comprova perfil/aplicativo, não a pessoa ao teclado. Parciais sujeitos à atribuição e ao atraso de receita. Somente leitura.']
    table=module('joe_custom_table_yolokfx',HOME/'scripts/joe_custom_report_table.py')
    table.len=lambda v:len(v.encode('utf-16-le'))//2 if isinstance(v,str) else len(v)
    parts=table.render(title,groups,notes)
    assert all(len(v.encode('utf-16-le'))//2<=2000 for v in parts)
    return parts
def execute(args,at=None):
    m=load(ROOT/'manifest.json');at=at or datetime.now(NY)
    if not applicable(m,at):return {'status':'EXPIRED','api_calls':0}
    key='initial' if args.initial else slot(m,at)
    if args.dry_run and not args.initial:key='dry-'+at.strftime('%H%M%S')
    if not key:return {'status':'NOT_DUE','api_calls':0}
    run=ROOT/'runs'/key;run.mkdir(parents=True,exist_ok=True,mode=0o700)
    if (run/'complete.json').exists():return load(run/'complete.json')
    for qa_name in ['tests.json','additional-tests.json']:
        qa=load(ROOT/qa_name);assert qa['pass'] and qa['tests_run']>0 and qa['failures']==qa['errors']==0, 'QA not approved'
    b=scope(m);d,delivery=helpers()
    dc=d.Discord();dc.verify([b])
    for mid,expected in [(REQUEST,m['request_text']),(m['confirmation_message_id'],'Sim')]:
        msg=dc.call('GET','/channels/'+TID+'/messages/'+mid)
        assert msg['author']['id']==USER and msg['channel_id']==TID and msg['content']==expected
    snap=load(run/'snapshot.json') if (run/'snapshot.json').exists() else collect(d,m,run,b)
    parts=text(snap);save(run/'update-parts.json',parts)
    result={'status':'LIVE_DRY_RUN_OK' if args.dry_run else 'COMPLETE_GET_VERIFIED','campaigns':len(snap['rows']),'observed_at':snap['observed_at'],'sb_at':snap['sb_at'],'pending':snap['pending'],'financial_error':snap['financial_error'],'meta_writes':0,'posted':False,'rows':snap['rows']}
    if args.dry_run:save(run/'preflight.json',result);return result
    if args.initial:
        import hashlib
        review=load(ROOT/'review-approved.json')
        for name,sha in review['hashes'].items():assert hashlib.sha256((run/name).read_bytes()).hexdigest()==sha,'Review invalidated'
    m.update(campaigns=snap['campaigns'],last_discovery_at=snap['observed_at']);save(ROOT/'manifest.json',m)
    delivery.deliver(d,m,run,parts);result['posted']=True
    save(run/'complete.json',result);save(ROOT/'state.json',{'last_run':key,'observed_at':snap['observed_at'],'expires_at':m['expires_at']});return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--initial',action='store_true');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--amendment',action='store_true');a=ap.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (ROOT/'run.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        try:
            result=execute(a)
            if a.initial or a.dry_run or a.amendment:print(json.dumps(result,ensure_ascii=False))
        except Exception as exc:
            save(ROOT/'last-error.json',{'at':datetime.now(NY).isoformat(),'error_class':type(exc).__name__,'resumable':True})
            if not a.dry_run:
                m=load(ROOT/'manifest.json')
                if applicable(m,datetime.now(NY)):
                    d,delivery=helpers();run=ROOT/'errors'/datetime.now(NY).strftime('%H%M');run.mkdir(parents=True,exist_ok=True)
                    delivery.deliver(d,m,run,['⚠️ Yolokfx Conta 04: atualização de CPR/ROI temporariamente indisponível; leitura pendente de recuperação, sem valores presumidos e sem alterações nas campanhas.'])
            raise SystemExit('Atualização pendente; diagnóstico protegido registrado.') from None
if __name__=='__main__':main()