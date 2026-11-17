#!/usr/bin/env python3
"""Finite Joe/G004 hourly alerts. GET Meta + SB report queries only."""
import argparse, concurrent.futures, fcntl, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

HOME = Path('/root/.hermes/profiles/ares')
BASE = Path('/root/mgs-agent')
ROOT = BASE / 'data/ares/meta-ads/state/roi-watch/1565473799510429788'
AID = '781612907182683'
TID = '1558147211026501643'
USER = '1214246869484576890'
NY = ZoneInfo('America/New_York')

def load(p):
    return json.loads(Path(p).read_text())

def save(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = p.with_suffix(p.suffix + '.tmp')
    with temp.open('w') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, default=str)
        f.flush(); os.fsync(f.fileno())
    temp.chmod(0o600); os.replace(temp, p)

def number(x):
    if x is None: return None
    try:
        n = Decimal(str(x))
        return n if n.is_finite() else None
    except Exception:
        return None

def roi(rev, spend):
    rev, spend = number(rev), number(spend)
    return (rev / spend - 1) * 100 if rev is not None and spend is not None and spend > 0 else None

def compare(previous, current):
    drops, missing = [], []
    for cid, row in current['rows'].items():
        new = number(row.get('roi')); prior = previous.get(cid, {})
        old = number(prior.get('roi'))
        if new is None:
            missing.append(row['number']); continue
        if old is not None and new < old:
            drops.append({'id': cid, 'number': row['number'], 'previous_roi': str(old),
                          'current_roi': str(new), 'drop_pp': str(old-new),
                          'previous_at': prior['observed_at']})
    return sorted(drops, key=lambda x: int(x['number'])), missing

def applicable(manifest, at):
    return at.date().isoformat() == manifest['date'] and at < datetime.fromisoformat(manifest['expires_at'])

def due(manifest, at):
    # Allow bounded scheduler dispatch delay, keeping the immutable logical slot.
    return applicable(manifest, at) and at.hour in manifest['hours'] and manifest['minute'] <= at.minute < manifest['minute'] + 15

def helpers():
    sys.path.insert(0, str(HOME/'scripts'))
    spec = importlib.util.spec_from_file_location('roi_watch_daily', HOME/'scripts/shein-daily-report.py')
    d = importlib.util.module_from_spec(spec); sys.modules[spec.name] = d; spec.loader.exec_module(d)
    return d

def verify_scope(manifest):
    assert manifest['account_id'] == AID and manifest['thread_id'] == TID
    assert manifest['mode'] == 'finite_read_only_alerts' and manifest['date'] == '2026-10-29'
    for cmd in [
        [sys.executable, str(BASE/'scripts/mgs-ares-asset-scope.py'), 'check-account', AID, '--json'],
        [sys.executable, str(BASE/'scripts/mgs-domain-scope.py'), 'check', '--agent', 'ares', 'yolokfx.com']]:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert p.returncode == 0, 'Scope unavailable'
    assert len(manifest['campaigns']) == 11 and len({x['id'] for x in manifest['campaigns']}) == 11

def collect(d, manifest, run):
    binding = next(b for b in d.load(BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if b['thread_id'] == TID)
    assert binding['account_id'] == AID and binding['channel_id'] == manifest['parent_id']
    r = d.Runner({'policy_id': manifest['request_id']}, run, [binding], manifest['date'])
    account = r.source(run, 'account', lambda: r.graph('act_'+AID, {'fields':'id,name,currency,timezone_name,account_status'}))
    assert account['id'].removeprefix('act_') == AID and account['name'] == manifest['account_name']
    assert account['currency'] == 'USD' and account['timezone_name'] == 'America/New_York'
    ids = [x['id'] for x in manifest['campaigns']]
    pub = manifest['publisher']
    filt = json.dumps([{'field':'campaign.id','operator':'IN','value':ids}])
    def insights():
        return r.paged('act_'+AID+'/insights', {'level':'campaign','time_range':json.dumps({'since':manifest['date'],'until':manifest['date']}), 'fields':'campaign_id,spend,impressions', 'filtering':filt, 'limit':500})
    def sbrows():
        data = r.sbquery('/report/performance_per_campaigns', {'initialDate':manifest['date']+'T00:00:00.000Z','finalDate':manifest['date']+'T23:59:59.999Z','publishers':[pub['publisherId']],'currency':'USD'})
        assert isinstance(data, list)
        return [x for x in data if str(x.get('CUSTOMER_ID','')).removeprefix('act_') == AID and str(x.get('CAMPAIGN_ID','')) in ids and str(x.get('DATE',''))[:10] == manifest['date'] and x.get('PUBLISHER') == pub['publisherId'] and x.get('DOMAIN') in (pub['name'],'yolokfx.com')]
    tasks = {'insights': insights, 'sb': sbrows, 'delay':lambda:r.sbquery('/estimated/delay', {'publisherIds':[pub['publisherId']],'currency':'USD'})}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(r.source, run, n, fn):n for n,fn in tasks.items()}
        sources = {futures[f]:f.result() for f in concurrent.futures.as_completed(futures)}
    im = {x['campaign_id']:x for x in sources['insights']}
    assert len(im) == len(sources['insights']) and set(im) <= set(ids)
    stamp = lambda name: load(run/(name+'-observed-at.json'))['observed_at']
    result = {'date':manifest['date'], 'observed_at':stamp('insights'), 'sb_at':stamp('sb'), 'delay':sources['delay'], 'rows':{}}
    for c in manifest['campaigns']:
        spend = number(im.get(c['id'],{}).get('spend','0'))
        assert spend is not None and spend >= 0
        rows = [x for x in sources['sb'] if str(x['CAMPAIGN_ID']) == c['id']]
        vals = [number(x.get('NET_REVENUE')) for x in rows]
        rev = sum(vals, Decimal(0)) if vals and all(v is not None for v in vals) else None
        result['rows'][c['id']] = {'number':c['number'], 'spend':str(spend), 'net_revenue':str(rev) if rev is not None else None, 'roi':str(roi(rev,spend)) if roi(rev,spend) is not None else None, 'observed_at':result['observed_at']}
    save(run/'snapshot.json', result)
    return result

def fmt(value):
    n = Decimal(str(value)); s = format(n.quantize(Decimal('.01')), 'f')
    if n and Decimal(s) == 0: s = format(n.normalize(), 'f')
    return s.replace('.', ',')

def message(manifest, snapshot, drops, missing):
    at = datetime.fromisoformat(snapshot['observed_at']).astimezone(NY).strftime('%H:%M EDT')
    lines = [f'<@{USER}> ⚠️ **Queda de ROI — Yolokfx Conta 04**', f'29/10 · corte {at} · USD · ROI real acumulado do dia', 'Comparação com a última leitura válida de cada campanha:']
    for x in drops:
        prior = datetime.fromisoformat(x['previous_at']).astimezone(NY).strftime('%H:%M')
        lines.append(f"- **C{x['number']}**: {fmt(x['previous_roi'])}% → **{fmt(x['current_roi'])}%** · queda de {fmt(x['drop_pp'])} p.p. (base {prior}).")
    if missing: lines.append('ROI indisponível, sem imputar zero: C'+', C'.join(missing)+'.')
    delay = snapshot.get('delay',{}).get('totalMinutes')
    lines += [f'⏱️ Atraso GAM/SB: {delay} min.' if number(delay) is not None else '⏱️ Atraso GAM/SB: n/d.', 'Fonte: gasto Meta × receita líquida SB. Dados parciais e sujeitos à atualização da receita; queda não comprova efeito das alterações.', 'Somente alerta; nenhuma campanha foi alterada.']
    parts=[];current=''
    for line in lines:
        new=current+'\n'+line if current else line
        if len(new.encode('utf-16-le'))//2>1950:
            assert current;parts.append(current);current=line
        else:current=new
    if current:parts.append(current)
    assert all(len(p.encode('utf-16-le'))//2<=2000 for p in parts)
    return parts

def deliver(d, manifest, run, parts):
    dc=d.Discord();binding={'thread_id':TID,'channel_id':manifest['parent_id']};dc.verify([binding])
    for i,part in enumerate(parts):
        path=run/f'delivery-{i}.json';sha=hashlib.sha256(part.encode()).hexdigest()
        nonce=str(int(hashlib.sha256((manifest['request_id']+run.name+str(i)+sha).encode()).hexdigest()[:15],16))
        rec=load(path) if path.exists() else {'status':'PREPARED','nonce':nonce,'sha256':sha}
        assert rec['sha256']==sha and rec['nonce']==nonce
        mid=rec.get('message_id')
        if not mid and rec['status']=='IN_FLIGHT':
            recent=dc.call('GET','/channels/'+TID+'/messages?limit=100')
            matches=[x for x in recent if x['author']['id']==d.BOT_ID and (str(x.get('nonce'))==nonce or x.get('content')==part)]
            assert len(matches)==1,'Uncertain delivery requires reconciliation'
            mid=matches[0]['id'];rec.update(message_id=mid,status='POST_RETURNED');save(path,rec)
        if not mid:
            rec['status']='IN_FLIGHT';save(path,rec)
            response=dc.call('POST','/channels/'+TID+'/messages',{'content':part,'allowed_mentions':{'parse':[],'users':[USER],'roles':[],'replied_user':False},'nonce':nonce,'enforce_nonce':True,'tts':False})
            mid=response['id'];rec.update(message_id=mid,status='POST_RETURNED');save(path,rec)
        remote=dc.call('GET','/channels/'+TID+'/messages/'+mid)
        assert remote['content']==part and remote['channel_id']==TID and remote['author']['id']==d.BOT_ID
        rec['status']='GET_VERIFIED';save(path,rec)

def execute(args):
    manifest=load(ROOT/'manifest.json');at=datetime.now(NY)
    if not applicable(manifest,at): return {'status':'EXPIRED','api_calls':0}
    if not (args.baseline or args.dry_run) and not due(manifest,at): return {'status':'NOT_DUE','api_calls':0}
    verify_scope(manifest);d=helpers()
    key='baseline' if args.baseline else ('preflight-'+at.strftime('%H%M%S') if args.dry_run else f'{at.hour:02d}{manifest["minute"]:02d}')
    run=ROOT/'runs'/key;run.mkdir(parents=True,exist_ok=True,mode=0o700)
    if (run/'complete.json').exists() and not args.dry_run: return load(run/'complete.json')
    state=load(ROOT/'state.json') if (ROOT/'state.json').exists() else {'previous':{}}
    snapshot=load(run/'snapshot.json') if (run/'snapshot.json').exists() else collect(d,manifest,run)
    drops,missing=compare(state['previous'],snapshot)
    if args.dry_run:
        parts=message(manifest,snapshot,drops,missing) if drops else []
        save(run/'preflight.json',{'drops':drops,'missing':missing,'would_send':parts,'no_external_writes':True})
        return {'status':'LIVE_DRY_RUN_OK','campaigns':len(snapshot['rows']),'drops':len(drops),'missing':missing,'posted':False}
    if args.baseline:
        assert not (ROOT/'state.json').exists(), 'Baseline already initialized; no reset'
        assert not missing,'Baseline incomplete'
    elif drops:
        parts=message(manifest,snapshot,drops,missing);save(run/'alert-parts.json',parts);deliver(d,manifest,run,parts)
    elif missing:
        parts=[f'<@{USER}> ⚠️ Monitor ROI — Yolokfx Conta 04: ROI indisponível para C'+', C'.join(missing)+'. Comparação não concluída para essas campanhas; última referência válida preservada. Nenhuma campanha alterada.']
        save(run/'alert-parts.json',parts);deliver(d,manifest,run,parts)
    for cid,row in snapshot['rows'].items():
        if row['roi'] is not None:state['previous'][cid]=row
    state.update(updated_at=snapshot['observed_at'],last_run=key,expires_at=manifest['expires_at'])
    save(ROOT/'state.json',state)
    result={'status':'BASELINE_OK' if args.baseline else 'COMPLETE','campaigns':len(snapshot['rows']),'drops':len(drops),'missing':missing,'observed_at':snapshot['observed_at'],'posted':bool(not args.baseline and (drops or missing))}
    save(run/'complete.json',result);return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',action='store_true');ap.add_argument('--dry-run',action='store_true');args=ap.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (ROOT/'run.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        try:
            result=execute(args)
            if args.baseline or args.dry_run:print(json.dumps(result,ensure_ascii=False))
        except Exception as exc:
            save(ROOT/'last-error.json',{'at':datetime.now(NY).isoformat(),'error_class':type(exc).__name__,'needs_resume':True})
            if not (args.baseline or args.dry_run):
                manifest=load(ROOT/'manifest.json');at=datetime.now(NY)
                if applicable(manifest,at):
                    d=helpers();run=ROOT/'errors'/at.strftime('%H%M');run.mkdir(parents=True,exist_ok=True,mode=0o700)
                    deliver(d,manifest,run,[f'<@{USER}> ⚠️ Não consegui concluir a checagem horária do ROI da Yolokfx Conta 04. A última referência válida foi preservada; nenhuma queda foi inferida e nenhuma campanha foi alterada.'])
            raise SystemExit('Falha na checagem; diagnóstico protegido registrado.') from None

if __name__=='__main__':main()
