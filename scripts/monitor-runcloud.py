#!/usr/bin/env python3
"""RunCloud read-only monitor. No remote mutation; explicit approved targets."""
import argparse, copy, fcntl, hashlib, json, os, subprocess, sys, time
import urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
BASE=Path('/root/mgs-agent')
CONFIG=BASE/'data/runcloud-alert-config.json'
STATE=BASE/'data/runcloud-alert-state.json'
UTC=timezone.utc

def load_env(path):
    for raw in Path(path).read_text().splitlines():
        if '=' not in raw or raw.lstrip().startswith('#'): continue
        k,v=raw.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))

def save(path,data):
    path=Path(path); tmp=path.with_suffix(path.suffix+'.tmp')
    with open(tmp,'w') as f:
        os.chmod(tmp,0o600); json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def fresh_state(): return {'schema':1,'incidents':{},'outbox':[],'last_check':None,'last_backup_check':0,'generation':0}

class APIError(Exception):
    definitely_rejected=False
class API:
    def __init__(self,token): self.token=token; self.last=0; self.calls=0; self.failures=0
    def get(self,path):
        reason='Request failed'
        for attempt in range(2):
            time.sleep(max(0,1.3-(time.monotonic()-self.last)))
            self.last=time.monotonic(); self.calls+=1
            req=urllib.request.Request('https://manage.runcloud.io/api/v3'+path,headers={'Authorization':'Bearer '+self.token,'Accept':'application/json','User-Agent':'MGS-RunCloud-Monitor/1.0'})
            try:
                with urllib.request.urlopen(req,timeout=20) as r: value=json.load(r)
                self.failures=0; return value
            except urllib.error.HTTPError as e:
                reason='HTTP '+str(e.code); delay=min(30,float(e.headers.get('Retry-After','2')) if e.headers.get('Retry-After','2').replace('.','',1).isdigit() else 2)
                e.close()
                if e.code in (401,403): break
                if attempt==0: time.sleep(delay)
            except (OSError,ValueError) as e:
                reason=type(e).__name__
                if attempt==0: time.sleep(2)
        self.failures+=1
        raise APIError(reason+' '+path.split('?')[0])
    def pages(self,path):
        rows=[]
        for page in range(1,101):
            d=self.get(path+f'?perPage=40&page={page}')
            if isinstance(d,list): return rows+d
            if not isinstance(d,dict) or not isinstance(d.get('data'),list): raise APIError('Invalid list schema '+path)
            rows+=d['data']; m=d.get('meta',{}); p=m.get('pagination',{}); last=p.get('total_pages') or m.get('lastPage') or m.get('last_page')
            if last is None: raise APIError('Missing pagination metadata '+path)
            if page>=int(last): return rows
        raise APIError('Pagination limit '+path)

def snapshot_time(row):
    t=datetime.fromisoformat(row['runDate'].replace('Z','+00:00'))
    return t.replace(tzinfo=UTC).timestamp() if t.tzinfo is None else t.timestamp()

def disk_observation(h):
    total=float(h['totalDiskSpace']); used=float(h['usedDiskSpace']); free=float(h['availableDiskSpace'])
    if total<=0 or used<0 or free<0 or used>total*1.01: raise ValueError('Invalid disk values')
    pct=100*used/total; severity=2 if pct>=90 or free<1024 else 1 if pct>=80 or free<5120 else 0
    return severity,f'Disco {pct:.1f}% ocupado; livre {free/1024:.1f} GiB (unidade API MB).'

def collect(api,cfg,state,now,force_backups=False):
    observations={}; errors=[]; summary=[]
    def put(key,server,severity,detail,confirmed=False):
        observations[key]={'server':server,'severity':severity,'detail':detail,'confirmed':confirmed}
    for target in cfg['servers']:
        sid=target['id']; name=target['name']
        try:
            d=api.get('/servers/'+sid)
            if not isinstance(d.get('online'),bool) or not isinstance(d.get('connected'),bool): raise APIError('Missing connection fields '+sid)
            if not d['online'] or not d['connected']: d=api.get('/servers/'+sid)
            offline=d.get('online') is False; disconnected=d.get('connected') is False
            put(sid+':connection',name,2 if offline or disconnected else 0,'Servidor reportado offline.' if offline else 'Agente desconectado da RunCloud; queda do servidor não comprovada.' if disconnected else 'Servidor online e agente conectado.',offline or disconnected)
            if offline or disconnected: continue
            h=api.get('/servers/'+sid+'/health/latest')
            age=str(h.get('updated_at','')).lower()
            import re
            found=re.fullmatch(r'(\d+)\s+(second|minute|hour)s? ago',age)
            if not found or int(found[1])*{'second':1,'minute':60,'hour':3600}[found[2]]>300: raise APIError('Health stale/unrecognized '+sid)
            sev,detail=disk_observation(h)
            if sev==2: sev,detail=disk_observation(api.get('/servers/'+sid+'/health/latest'))
            put(sid+':disk',name,sev,detail,sev==2)
            services=api.get('/servers/'+sid+'/services')
            if any(services.get(k,{}).get('running') is False for k in target['services']): services=api.get('/servers/'+sid+'/services')
            for key in target['services']:
                value=services.get(key,{}).get('running')
                if not isinstance(value,bool): errors.append('Estado de serviço não disponível: '+name+'/'+key); continue
                put(sid+':service:'+key,name,0 if value else 2,('Serviço ativo: ' if value else 'Serviço esperado parado: ')+key,not value)
            summary.append({'server':name,'online':True,'disk_pct':round(100*float(h['usedDiskSpace'])/float(h['totalDiskSpace']),2)})
        except (APIError,ValueError,KeyError,TypeError) as e:
            errors.append(str(e) if isinstance(e,APIError) else 'Invalid health schema '+sid)
        if getattr(api,'failures',0)>=5: break
    backup_due=force_backups or now-state.get('last_backup_check',0)>=3600
    backup_summary=None
    if backup_due and getattr(api,'failures',0)<5:
        try:
            routines=api.pages('/backups'); selected=[b for b in routines if str(b.get('items',{}).get('webApplicationId')) in cfg['webapp_servers'] and b.get('status')=='active']
            backup_summary={'active':len(selected),'completed_latest':0,'checked':0}; all_ok=True
            for b in selected:
                bid=str(b['id']); sid=cfg['webapp_servers'][str(b['items']['webApplicationId'])]; name=next(t['name'] for t in cfg['servers'] if t['id']==sid)
                try:
                    rows=api.pages('/backups/'+bid+'/snapshots')
                    overdue_first=not any(x.get('status')=='COMPLETED' for x in rows) or now-max((snapshot_time(x) for x in rows if x.get('status')=='COMPLETED'),default=0)>cfg['backup_max_age_hours']*3600
                    if overdue_first or (rows and max(rows,key=snapshot_time).get('status')=='FAILED'): rows=api.pages('/backups/'+bid+'/snapshots')
                    latest=max(rows,key=snapshot_time,default={}); completed=[x for x in rows if x.get('status')=='COMPLETED']; last=max((snapshot_time(x) for x in completed),default=0)
                    if last>now+3600: raise APIError('Snapshot timestamp in future '+bid)
                    failed=latest.get('status')=='FAILED'; overdue=not last or now-last>cfg['backup_max_age_hours']*3600
                    sev=2 if failed or overdue else 0
                    detail=f'Backup #{bid}: '+('última execução FAILED.' if failed else f'sem conclusão válida nas últimas {cfg["backup_max_age_hours"]}h.' if overdue else 'conclusão recente válida.')
                    put(sid+':backup:'+bid,name,sev,detail,True)
                    backup_summary['checked']+=1; backup_summary['completed_latest']+=int(latest.get('status')=='COMPLETED')
                except (APIError,ValueError,KeyError,TypeError) as e:
                    all_ok=False; errors.append(str(e) if isinstance(e,APIError) else 'Invalid snapshot schema '+bid)
                if getattr(api,'failures',0)>=5: all_ok=False; break
            if all_ok: state['last_backup_check']=now
        except (APIError,KeyError,TypeError) as e: errors.append(str(e) if isinstance(e,APIError) else 'Invalid backups schema')
    put('monitor:api','Monitor RunCloud',2 if errors else 0,'; '.join(errors)[:850] if errors else 'Coleta API íntegra.',True)
    return observations,{'servers':summary,'backups':backup_summary,'api_errors':errors,'api_calls':getattr(api,'calls',0)}

def transitions(state,observations,now):
    events=[]
    for key,obs in observations.items():
        record=state['incidents'].setdefault(key,{'published':0,'candidate':0,'count':0})
        sev=obs['severity']; old=record['published']
        record['detail']=obs['detail']; record['observed_at']=now
        if sev!=record['candidate']: record['candidate']=sev; record['count']=0
        record['count']+=1
        ready=sev==0 or obs.get('confirmed') or record['count']>=2
        if ready and (sev>old or (sev==0 and old>0)):
            events.append({'key':key,**obs,'previous':old,'status':'recovery' if sev==0 else 'alert'})
    # Unknown observations must not resolve an incident or join nonconsecutive candidates.
    for key,record in state['incidents'].items():
        if key not in observations: record['count']=0
    return events

class Discord:
    def __init__(self,token,channel,base='https://discord.com/api/v10'): self.token=token; self.channel=channel; self.base=base
    def request(self,path,method='GET',payload=None):
        req=urllib.request.Request(self.base+path,method=method,headers={'Authorization':'Bot '+self.token,'Content-Type':'application/json','User-Agent':'MGS-Zeus/1.0'},data=json.dumps(payload).encode() if payload is not None else None)
        try:
            with urllib.request.urlopen(req,timeout=20) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            error=APIError('Discord HTTP '+str(e.code)); error.definitely_rejected=400<=e.code<500; e.close(); raise error
    def recent(self): return self.request('/channels/'+self.channel+'/messages?limit=100')
    def get(self,ident): return self.request('/channels/'+self.channel+'/messages/'+ident)
    def post(self,payload): return self.request('/channels/'+self.channel+'/messages','POST',payload)

def payload_for(events,ident):
    recovery=all(e['status']=='recovery' for e in events); critical=any(e['severity']==2 for e in events)
    groups={}
    for e in events: groups.setdefault(e['server'],[]).append(e['detail'])
    lines=[]
    for name,details in groups.items():
        lines.append('**'+name+'**\n'+'\n'.join('- '+d for d in details))
    body='\n\n'.join(lines)
    if len(body)>3600: body=body[:3500]+'\nDetalhes completos no state do monitor; '+str(len(events))+' ocorrências neste lote.'
    return {'content':'<@344196393512075265>' if critical and not recovery else '', 'allowed_mentions':{'parse':[],'users':['344196393512075265'] if critical and not recovery else []},'nonce':ident,'enforce_nonce':True,'embeds':[{'title':'RunCloud — recuperação validada' if recovery else 'RunCloud — incidente confirmado','description':body,'color':3066993 if recovery else 15158332 if critical else 15844367,'footer':{'text':'MGS RunCloud event '+ident}}]}

def enqueue(state,events,path,now,observations=None):
    if observations is not None:
        for entry in list(state['outbox']):
            if entry['phase']=='queued' and not entry.get('message_id'):
                valid=[e for e in entry['events'] if e['key'] not in observations or observations[e['key']]['severity']==e['severity']]
                if not valid: state['outbox'].remove(entry)
                elif valid!=entry['events']:
                    entry['events']=valid; entry['payload']=payload_for(valid,entry['id'])
    pending={e['key'] for o in state['outbox'] for e in o['events']}
    for batch_status in ('alert','recovery'):
        eligible=[e for e in events if e['key'] not in pending and e['status']==batch_status]
        for i in range(0,len(eligible),20):
            batch=eligible[i:i+20]; state['generation']+=1
            ident=str(int(hashlib.sha256(f'runcloud:{now}:{state["generation"]}'.encode()).hexdigest()[:15],16))
            state['outbox'].append({'id':ident,'events':batch,'payload':payload_for(batch,ident),'phase':'queued','created_at':now})
    save(path,state)

def deliver(state,path,discord):
    sent=[]
    for entry in list(state['outbox']):
        if not entry.get('message_id') and entry['phase']=='sending':
            matches=[m for m in discord.recent() if any(x.get('footer',{}).get('text')=='MGS RunCloud event '+entry['id'] for x in m.get('embeds',[]))]
            if not matches: raise APIError('Ambiguous previous delivery; reconcile before repost')
            entry['message_id']=matches[0]['id']; save(path,state)
        if not entry.get('message_id'):
            entry['phase']='sending'; save(path,state)
            try: m=discord.post(entry['payload'])
            except APIError as error:
                if error.definitely_rejected: entry['phase']='queued'
                save(path,state); raise
            entry['message_id']=m['id']; save(path,state)
        m=discord.get(entry['message_id'])
        if str(m.get('channel_id'))!=discord.channel or m.get('content')!=entry['payload']['content'] or not any(e.get('footer',{}).get('text')=='MGS RunCloud event '+entry['id'] for e in m.get('embeds',[])): raise APIError('Discord readback mismatch')
        for e in entry['events']: state['incidents'][e['key']]['published']=e['severity']
        sent.append(entry['message_id']);state['outbox'].remove(entry);save(path,state)
    return sent

def main():
    p=argparse.ArgumentParser();p.add_argument('--dry-run',action='store_true');p.add_argument('--force-backups',action='store_true');p.add_argument('--config',type=Path,default=CONFIG);p.add_argument('--state',type=Path,default=STATE); args=p.parse_args()
    if not args.dry_run:
        lock_handle=open(args.state.with_suffix('.lock'),'a'); os.chmod(args.state.with_suffix('.lock'),0o600)
        try: fcntl.flock(lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: print('{"monitor":"runcloud","status":"skip_locked"}'); return 0
    cfg=json.loads(args.config.read_text()); state=json.loads(args.state.read_text()) if args.state.exists() else fresh_state(); now=time.time()
    state.setdefault('last_backup_summary',state.get('last_summary',{}).get('backups'))
    if not args.dry_run:
        rotation=subprocess.run(['/usr/sbin/logrotate','--state',str(BASE/'data/runcloud-logrotate.status'),str(BASE/'config/runcloud-logrotate.conf')],capture_output=True,timeout=15)
        if rotation.returncode: raise APIError('Local log rotation failed; exit '+str(rotation.returncode))
    load_env(BASE/'.env');load_env('/root/.hermes/profiles/zeus/.env')
    r=subprocess.run(['op','item','get','RunCloud API - MGS','--vault',os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo'),'--fields','label=runcloud_api_key_token','--reveal'],capture_output=True,text=True,timeout=40)
    if r.returncode or not r.stdout.strip():
        observations={'monitor:api':{'server':'Monitor RunCloud','severity':2,'detail':'Credencial RunCloud indisponível no 1Password; valor/erro bruto omitido.','confirmed':True}};summary={'api_errors':['1Password credential unavailable']}
    else: observations,summary=collect(API(r.stdout.strip()),cfg,state,now,args.force_backups)
    events=transitions(state,observations,now); state['last_check']=datetime.now(UTC).isoformat();state['last_summary']=summary
    if summary.get('backups') is not None: state['last_backup_summary']=summary['backups']
    if args.dry_run: print(json.dumps({'mode':'dry-run','events':len(events),'summary':summary},ensure_ascii=False));return 0
    enqueue(state,events,args.state,now,observations)
    sent=deliver(state,args.state,Discord(os.environ['DISCORD_BOT_TOKEN'],cfg['channel_id']))
    print(json.dumps({'mode':'apply','events':len(events),'sent':sent,'summary':summary},ensure_ascii=False));return 0 if not summary.get('api_errors') else 1
if __name__=='__main__':
    try: sys.exit(main())
    except Exception as e:
        print('ERROR: '+json.dumps({'monitor':'runcloud','status':'failed','error':str(e) if isinstance(e,APIError) else type(e).__name__}),file=sys.stderr);sys.exit(1)
