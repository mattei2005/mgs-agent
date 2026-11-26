#!/usr/bin/env python3
"""Public MGS HTTP/TCP observations; no guest writes or provider credential calls."""
import argparse, concurrent.futures, datetime, fcntl, hashlib, importlib.util, json, os
from pathlib import Path
import socket, subprocess, sys, time
from zoneinfo import ZoneInfo
BASE=Path('/root/mgs-agent')
CONFIG=BASE/'data/mattei-uptime-config.json'
STATE=BASE/'data/mattei-uptime-state.json'
spec=importlib.util.spec_from_file_location('runcloud_transport',BASE/'scripts/monitor-runcloud.py')
assert spec is not None and spec.loader is not None
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
save=transport.save

def classify(rc,code,body,seconds,limit=8):
    text=body.lower()
    if rc: return {6:'dns_error',7:'connection_error',28:'timeout',35:'tls_error',60:'tls_error'}.get(rc,'probe_error')
    if any(x in text for x in ('cf-chl-','just a moment...','checking your browser')):return 'challenge'
    if code in (401,403,429):return 'access_restricted'
    if code>=400 or code<200:return 'http_error'
    if code>=300:return 'redirect_error'
    if any(x in text for x in ('there has been a critical error on this website','error establishing a database connection')):return 'application_error'
    if len(body.strip())<80:return 'empty_response'
    return 'slow' if seconds>limit else 'ok'

def http_probe(url,limit=8,origin=None):
    args=['curl','--silent','--show-error','--location','--max-redirs','5','--connect-timeout','6','--max-time','20','--proto','=https','--proto-redir','=https','--user-agent','MGS-Uptime/1.0','--write-out','\nMGS_METRICS:%{json}',url]
    if origin:
        from urllib.parse import urlsplit
        args.extend(['--resolve',urlsplit(url).hostname+':443:'+origin])
    try:
        p=subprocess.run(args,capture_output=True,timeout=24)
        raw,marker,meta=p.stdout.rpartition(b'\nMGS_METRICS:')
        metrics=json.loads(meta) if marker else {};body=raw[:262144].decode(errors='replace');code=int(metrics.get('http_code',0));seconds=float(metrics.get('time_total',0))
        return {'status':classify(p.returncode,code,body,seconds,limit),'http':code,'seconds':round(seconds,3),'ttfb':round(float(metrics.get('time_starttransfer',0)),3),'curl_rc':p.returncode,'remote_ip':metrics.get('remote_ip'),'effective_url':metrics.get('url_effective',url)}
    except subprocess.TimeoutExpired:return {'status':'timeout','http':0,'seconds':24,'curl_rc':28}
    except (OSError,ValueError,TypeError):return {'status':'probe_error','http':0,'seconds':0}

def website(domain,ips,limit,probe=http_probe,sleep=time.sleep):
    first=probe('https://'+domain+'/',limit)
    if first['status']=='ok':return first
    sleep(3)
    final=probe('https://'+domain+'/',limit);final['first_status']=first['status'];final['confirmed']=final['status']!='ok'
    if final['status'] not in ('ok','slow'):
        final['origins']={ip:probe('https://'+domain+'/',limit,origin=ip) for ip in ips}
    return final

def server_probe(server):
    ports={}
    for port in (22,80,443):
        try:
            with socket.create_connection((server['ip'],port),timeout=4):ports[str(port)]=True
        except OSError:ports[str(port)]=False
    return {'status':'ok' if any(ports.values()) else 'unreachable','ports':ports}

def collect(cfg):
    bindings={}
    for s in cfg['servers']:
        for domain in s['domains']:bindings.setdefault(domain,[]).append(s['ip'])
    result={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        jobs={pool.submit(website,d,ips,cfg['slow_seconds']):'site:'+d for d,ips in bindings.items()}
        jobs.update({pool.submit(server_probe,s):'server:'+s['name'] for s in cfg['servers']})
        for future in concurrent.futures.as_completed(jobs):result[jobs[future]]=future.result()
    for s in cfg['servers']:
        key='server:'+s['name']
        if result[key]['status']!='ok':
            time.sleep(3);result[key]=server_probe(s);result[key]['confirmed']=result[key]['status']!='ok'
    return result

def events_for(state,observations):
    events=[]
    for key,obs in observations.items():
        old=state.setdefault('announced',{}).get(key,'ok');new=obs['status']
        if old==new:continue
        if new=='probe_error' and old not in ('ok','probe_error'):continue # unknown sample never resolves or overwrites a known target incident
        events.append({'key':key,'previous':old,'status':new,'observation':obs})
    return events

def marker(ident):return 'MGS Mattei uptime '+ident

def enqueue(state,payload,kind):
    state['generation']=state.get('generation',0)+1
    ident=str(int(hashlib.sha256((str(time.time_ns())+str(state['generation'])).encode()).hexdigest()[:15],16))
    payload.update(content='',allowed_mentions={'parse':[]},nonce=ident,enforce_nonce=True)
    payload['embeds'][-1]['footer']={'text':marker(ident)}
    state.setdefault('outbox',[]).append({'id':ident,'payload':payload,'kind':kind,'phase':'queued'})

def verify(message,payload,channel):
    assert str(message['channel_id'])==str(channel) and message.get('content','')=='' and not message.get('mentions')
    assert len(message['embeds'])==len(payload['embeds'])
    for got,want in zip(message['embeds'],payload['embeds']):
        for key in ('title','description','color','footer'):
            if key in want:assert got.get(key)==want[key], 'Discord readback mismatch: '+key

def reconcile_queued(state,observations):
    for entry in list(state.get('outbox',[])):
        if entry['phase']!='queued' or entry.get('message_id') or not entry.get('events'):continue
        valid=[e for e in entry['events'] if e['key'] not in observations or observations[e['key']]['status']==e['status']]
        if not valid:state['outbox'].remove(entry)
        elif valid!=entry['events']:
            entry['events']=valid;entry['payload']=event_payload(valid)
            entry['payload'].update(content='',allowed_mentions={'parse':[]},nonce=entry['id'],enforce_nonce=True)
            entry['payload']['embeds'][-1]['footer']={'text':marker(entry['id'])}

def deliver(state,path,discord):
    for entry in list(state.get('outbox',[])):
        if not entry.get('message_id') and entry['phase']=='sending':
            matches=[m for m in discord.recent() if any(e.get('footer',{}).get('text')==marker(entry['id']) for e in m.get('embeds',[]))]
            if len(matches)!=1:raise RuntimeError('ambiguous_delivery_requires_reconciliation')
            entry['message_id']=matches[0]['id'];save(path,state)
        if not entry.get('message_id'):
            entry['phase']='sending';save(path,state)
            try:m=discord.post(entry['payload'])
            except transport.APIError as e:
                if e.definitely_rejected:entry['phase']='queued'
                save(path,state);raise
            entry['message_id']=m['id'];save(path,state)
        verify(discord.get(entry['message_id']),entry['payload'],discord.channel)
        if entry['kind']=='panel':state['panel_id']=entry['message_id']
        if entry.get('events'):
            for e in entry['events']:state.setdefault('announced',{})[e['key']]=e['status']
        state.setdefault('receipts',[]).append({'id':entry['message_id'],'kind':entry['kind'],'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        state['receipts']=state['receipts'][-100:];state['outbox'].remove(entry);save(path,state)

LABELS={'ok':'OK','slow':'LENTO','challenge':'CHALLENGE','access_restricted':'RESTRITO','http_error':'ERRO HTTP','timeout':'TIMEOUT','dns_error':'ERRO DNS','connection_error':'SEM CONEXÃO','tls_error':'ERRO TLS','probe_error':'SEM LEITURA','redirect_error':'REDIRECT','empty_response':'VAZIO','application_error':'ERRO APP','unreachable':'INALCANÇÁVEL'}
def panel(cfg,obs,stamp):
    embeds=[]
    for s in cfg['servers']:
        host=obs['server:'+s['name']];lines=[s['ip']+' — '+LABELS[host['status']], 'Site público                     Estado       HTTP  Tempo', '----------------------------------------------------------']
        for domain in s['domains']:
            r=obs['site:'+domain];lines.append(f"{domain:32} {LABELS[r['status']]:12} {r.get('http',0):3}  {r.get('seconds',0):4.1f}s")
        desc='```\n'+'\n'.join(lines)+'\n```\nTCP 22/80/443: '+', '.join(k+(' aberto' if v else ' sem resposta') for k,v in host['ports'].items())
        interval=cfg.get('interval_seconds',3600)
        cadence='1 minuto' if interval==60 else ('1 hora' if interval==3600 else str(interval)+' segundos')
        desc+='\nChecagem: '+stamp+' • atualização a cada '+cadence+'.'
        embeds.append({'title':s['name']+' — '+str(len(s['domains']))+' vínculos MGS','description':desc,'color':3066993 if all(obs['site:'+d]['status']=='ok' for d in s['domains']) and host['status']=='ok' else 15844367})
    return {'content':'','allowed_mentions':{'parse':[]},'embeds':embeds}

def event_payload(events):
    lines=[]
    for e in events:
        r=e['observation'];line=e['key'].split(':',1)[1]+': '+LABELS.get(e['previous'],e['previous'])+' → '+LABELS[e['status']]
        if 'http' in r:line+=' (HTTP '+str(r['http'])+', '+str(r['seconds'])+'s)'
        if r.get('origins'):line+='; origem(s): '+', '.join(ip+'='+str(v.get('http',0))+'/'+v['status'] for ip,v in r['origins'].items())
        lines.append(line)
    recovered=all(e['status']=='ok' for e in events)
    body='\n'.join(lines)+'\n\n'+('Recuperação observada pela mesma sonda externa.' if recovered else 'Repetição da leitura concluída. Restrição/challenge não comprova queda. TCP inalcançável não comprova máquina desligada. Sem mudanças nos sites ou reinícios. Próximo passo: Zeus investigar a camada indicada; qualquer ajuste crítico depende da confirmação de Rodolfo.')
    assert len(body)<4096
    return {'embeds':[{'title':'Mattei — recuperação' if recovered else 'Mattei — alteração de disponibilidade','description':body,'color':3066993 if recovered else 15158332}]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry-run',action='store_true');ap.add_argument('--config',type=Path,default=CONFIG);ap.add_argument('--state',type=Path,default=STATE);args=ap.parse_args()
    lock=args.state.with_suffix('.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    cfg=json.loads(args.config.read_text());allowed=set(json.loads((BASE/'data/mgs-domain-scope.json').read_text())['domains'])
    assert all(d in allowed for s in cfg['servers'] for d in s['domains']),'scope_changed_fail_closed'
    obs=collect(cfg);stamp=datetime.datetime.now(ZoneInfo('America/New_York')).strftime('%d/%m/%Y %H:%M %Z')
    state=json.loads(args.state.read_text()) if args.state.exists() else {'announced':{},'outbox':[]}
    events=events_for(state,obs);summary={'checked_at':stamp,'sites':len([k for k in obs if k.startswith('site:')]),'servers':3,'states':{status:sum(v['status']==status for v in obs.values()) for status in sorted(set(v['status'] for v in obs.values()))},'events':len(events)}
    if args.dry_run:print(json.dumps({'mode':'dry-run',**summary,'observations':obs},ensure_ascii=False));return 0
    transport.load_env('/root/.hermes/profiles/zeus/.env');discord=transport.Discord(os.environ['DISCORD_BOT_TOKEN'],cfg['channel_id'])
    # Reconcile accepted POSTs before enqueuing new events; never replay ambiguous writes.
    reconcile_queued(state,obs);save(args.state,state)
    deliver(state,args.state,discord)
    events=events_for(state,obs)
    state.update(last_check=datetime.datetime.now(datetime.timezone.utc).isoformat(),observations=obs,summary=summary);save(args.state,state)
    payload=panel(cfg,obs,stamp)
    if state.get('panel_id'):
        payload['embeds'][-1]['footer']={'text':'MGS Mattei uptime panel'}
        discord.request('/channels/'+discord.channel+'/messages/'+state['panel_id'],'PATCH',payload)
        verify(discord.get(state['panel_id']),payload,discord.channel)
    else:enqueue(state,payload,'panel');save(args.state,state);deliver(state,args.state,discord)
    for i in range(0,len(events),8):
        batch=events[i:i+8];enqueue(state,event_payload(batch),'events');state['outbox'][-1]['events']=batch;save(args.state,state)
    deliver(state,args.state,discord)
    print(json.dumps({'mode':'apply',**summary,'panel_id':state['panel_id'],'pending':len(state['outbox'])},ensure_ascii=False));return 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        print(json.dumps({'monitor':'mattei-uptime','error':type(e).__name__,'status':'failed'}),file=sys.stderr);sys.exit(1)
