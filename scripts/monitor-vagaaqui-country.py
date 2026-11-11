#!/usr/bin/env python3
"""Finite, hostname-scoped Cloudflare country monitoring. No production writes.

Monthly interval is frozen in config; UTC daily slices are clipped at its ends.
Hourly cron is a recovery consumer, not an hourly publisher. Data is collected
once per closed slice after a 3h settling delay. Discord outbox is durable and
verified with exact GET; completed runs perform no external requests.
"""
from __future__ import annotations
import argparse
import calendar
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path('/root/mgs-agent')
STORE = ROOT / 'data/vagaaqui-country-monitor'
UTC = dt.timezone.utc
ZONE = '0a38ce4f11fedd8f03e02fcc07601d74'
HOSTS = ['vagaaqui.com', 'www.vagaaqui.com']
THREAD = '1569851196234014781'
ITEM = 'Cloudflare MGS Admin Token - mattei2005'
NAMES = {'ZA':'África do Sul','US':'Estados Unidos','BR':'Brasil','FR':'França','DE':'Alemanha','GB':'Reino Unido','SG':'Singapura','BE':'Bélgica','CA':'Canadá','CN':'China','NL':'Países Baixos','IN':'Índia','AU':'Austrália','IE':'Irlanda','ES':'Espanha','PT':'Portugal','IT':'Itália','JP':'Japão','RU':'Rússia','ID':'Indonésia','MX':'México','AR':'Argentina','XX':'Não identificado','T1':'Tor','ZZ':'Não identificado'}
QUERY = '''query($z: string, $start: Time, $end: Time) {
 viewer {zones(filter:{zoneTag:$z}) {
 httpRequestsAdaptiveGroups(limit:1000, orderBy:[count_DESC], filter:{
 datetime_geq:$start, datetime_lt:$end,
 clientRequestHTTPHost_in:["vagaaqui.com","www.vagaaqui.com"], requestSource:"eyeball"})
 {count dimensions {clientCountryName} avg {sampleInterval}}
 }}}
'''

class MonitorError(Exception):
    def __init__(self, reason, permanent=False):
        super().__init__(reason)
        self.permanent = permanent

def iso(t):
    return t.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00','Z')

def parse(s):
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = path.with_suffix(path.suffix + '.new')
    with candidate.open('w') as f:
        json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(candidate,path)

def config_read(store):
    c=json.loads((store/'config.json').read_text())
    if c['zone_id'] != ZONE or c['hosts'] != HOSTS or c['thread_id'] != THREAD or c['credential_item'] != ITEM:
        raise MonitorError('scope_guard_mismatch',True)
    start,end=parse(c['start']),parse(c['end'])
    month=start.month+1; year=start.year
    if month==13:month=1;year+=1
    expected=start.replace(year=year,month=month,day=min(start.day,calendar.monthrange(year,month)[1]))
    if end != expected:raise MonitorError('month_interval_guard_mismatch',True)
    return c

def intervals(c):
    current=parse(c['start']);end=parse(c['end'])
    while current<end:
        midnight=(current+dt.timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
        following=min(end,midnight)
        yield iso(current),iso(following)
        current=following

def state_read(store):
    p=store/'state.json'
    return json.loads(p.read_text()) if p.exists() else {'schema':1,'status':'active','days':{},'outbox':{},'failure_streak':0}

def cf_token():
    result=subprocess.run([str(ROOT/'scripts/mgs-op-with-service-account.sh'),'item','get',ITEM,'--vault','MGS Conteúdo','--format','json'],capture_output=True,text=True,timeout=45)
    if result.returncode:raise MonitorError('credential_read_failed',True)
    try:
        fields=json.loads(result.stdout)['fields']
        return next(f['value'] for f in fields if f.get('label')=='token')
    except (KeyError,ValueError,StopIteration):raise MonitorError('credential_field_missing',True)

def cf_query(token,start,end):
    body=json.dumps({'query':QUERY,'variables':{'z':ZONE,'start':start,'end':end}}).encode()
    req=urllib.request.Request('https://api.cloudflare.com/client/v4/graphql',data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','User-Agent':'MGS-Zeus-Country-Monitor/1.0'})
    reason='cloudflare_transport_unconfirmed'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=35) as r:a=json.load(r)
            if a.get('errors'):
                errors=a['errors'];codes=[str((e.get('extensions') or {}).get('code','graphql')) for e in errors]
                blocked=any('auth' in code.lower() for code in codes)
                # Provider text is not echoed: it may include request/credential data.
                raise MonitorError('cloudflare_graphql_'+'_'.join(codes),blocked)
            zones=a['data']['viewer']['zones']
            if len(zones)!=1:raise MonitorError('zone_data_unavailable',True)
            rows=zones[0]['httpRequestsAdaptiveGroups']
            return normalize(rows,start,end)
        except urllib.error.HTTPError as e:
            if e.code not in [429,500,502,503,504]:raise MonitorError('cloudflare_http_'+str(e.code),e.code in [401,403])
            reason='cloudflare_http_'+str(e.code)
        except (TimeoutError,OSError) as e:reason='cloudflare_transport_'+type(e).__name__
        except (KeyError,ValueError,TypeError):raise MonitorError('cloudflare_invalid_response')
        if attempt<2:time.sleep(2**(attempt+1))
    raise MonitorError(reason)

def normalize(rows,start,end):
    if not isinstance(rows,list) or len(rows)>=1000:raise MonitorError('country_result_incomplete')
    countries={};samples=[]
    for r in rows:
        code=r['dimensions']['clientCountryName'] or 'XX';count=r['count'];sample=r['avg']['sampleInterval']
        if not re.fullmatch('[A-Z0-9]{2}',code) or isinstance(count,bool) or not isinstance(count,(int,float)) or count<0 or sample<1:
            raise MonitorError('country_row_invalid')
        if code in countries:raise MonitorError('country_duplicate')
        countries[code]=count;samples.append(sample)
    return {'start':start,'end':end,'total':sum(countries.values()),'countries':countries,'max_sample_interval':max(samples,default=1),'collected_at':iso(dt.datetime.now(UTC)),'dataset':'httpRequestsAdaptiveGroups','estimated':True}

def aggregate(slices):
    countries={};samples=[]
    for s in slices:
        for code,count in s['countries'].items():countries[code]=countries.get(code,0)+count
        samples.append(s['max_sample_interval'])
    return {'total':sum(countries.values()),'countries':countries,'max_sample_interval':max(samples,default=1)}

def number(n):return f'{n:,.0f}'.replace(',','.')

def ranking(data):
    rows=sorted(data['countries'].items(),key=lambda x:(-x[1],x[0]));total=data['total']
    lines=['País                   Requisições      %']
    for code,count in rows[:10]:
        label=(str(NAMES.get(code,code))+' ('+code+')') if code in NAMES else code
        lines.append(f'{label[:22]:22} {number(count):>11} {100*count/total if total else 0:6.2f}')
    if len(rows)>10:
        rest=sum(n for _,n in rows[10:]);lines.append(f'{"Outros ("+str(len(rows)-10)+")":22} {number(rest):>11} {100*rest/total if total else 0:6.2f}')
    if not rows:lines.append('Sem requisições retornadas para este intervalo.')
    return '```\n'+'\n'.join(lines)+'\n```'

def payload(kind,key,data,c,detail):
    title={'initial':'Vagaaqui — monitor por país ativado','daily':'Vagaaqui — tráfego diário por país','final':'Vagaaqui — fechamento do monitor por país','failure':'Vagaaqui — monitor com pendência','recovery':'Vagaaqui — monitor recuperado'}[kind]
    fields=[{'name':'Período / cobertura','value':detail,'inline':False}]
    if data is not None:
        fields += [{'name':'Requisições estimadas','value':number(data['total']),'inline':True},{'name':'Países / categorias','value':str(len(data['countries'])),'inline':True},{'name':'Distribuição por país','value':ranking(data),'inline':False}]
    fields.append({'name':'Leitura correta','value':'País estimado pelo IP, não localização física garantida. Requisições incluem recursos, bots e acessos que podem ser bloqueados; não são pessoas ou visitas. Analytics com amostragem adaptativa.'+(' Maior intervalo de amostragem: '+f"{data['max_sample_interval']:.3f}"+'.' if data else ''),'inline':False})
    marker='CF-VAGAAQUI:'+key
    return {'content':'','allowed_mentions':{'parse':[]},'embeds':[{'title':title,'color':15844367 if kind=='failure' else 3066993 if kind=='recovery' else 3447003,'fields':fields,'footer':{'text':marker}}],'nonce':str(int(hashlib.sha256(marker.encode()).hexdigest()[:15],16)),'enforce_nonce':True}

def bot_token():
    spec=importlib.util.spec_from_file_location('poster',ROOT/'scripts/discord-bot-post.py')
    if spec is None or spec.loader is None:raise MonitorError('discord_transport_missing',True)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.load_env(Path('/root/.hermes/profiles/zeus/.env'))
    token=os.environ.get('DISCORD_BOT_TOKEN')
    if not token:raise MonitorError('discord_credential_unavailable',True)
    return token

def discord_get(path):
    req=urllib.request.Request('https://discord.com/api/v10/'+path,headers={'Authorization':'Bot '+bot_token(),'User-Agent':'MGS-Zeus/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
    except urllib.error.HTTPError as e:raise MonitorError('discord_read_http_'+str(e.code),e.code in [401,403])
    except (TimeoutError,OSError,ValueError) as e:raise MonitorError('discord_read_'+type(e).__name__)

def verify_message(m,p):
    if m.get('channel_id')!=THREAD or m.get('content')!='' or m.get('mentions') or m.get('mention_roles') or m.get('mention_everyone'):
        raise MonitorError('discord_readback_metadata_mismatch')
    if not m.get('author',{}).get('bot') or str(m['author']['id'])!='1496296175014252634':raise MonitorError('discord_author_mismatch')
    actual=m.get('embeds',[]);wanted=p['embeds']
    if len(actual)!=1 or any(actual[0].get(k)!=wanted[0].get(k) for k in ['title','fields','footer']):raise MonitorError('discord_readback_content_mismatch')

def deliver(s,key,p,store):
    entry=s['outbox'].get(key)
    if entry and entry.get('verified'):return
    if not entry:
        entry={'payload':p,'prepared_at':iso(dt.datetime.now(UTC))};s['outbox'][key]=entry;save(store/'state.json',s)
    p=entry['payload']
    if not entry.get('message_id'):
        # Reconcile a prior ambiguous POST before any resend.
        marker=p['embeds'][0]['footer']['text']
        recent=discord_get('channels/'+THREAD+'/messages?limit=100')
        matches=[m for m in recent if any(e.get('footer',{}).get('text')==marker for e in m.get('embeds',[])) and str(m.get('author',{}).get('id'))=='1496296175014252634']
        if len(matches)>1:raise MonitorError('discord_duplicate_marker',True)
        if matches:entry['message_id']=matches[0]['id']
        else:
            r=subprocess.run([sys.executable,str(ROOT/'scripts/discord-bot-post.py'),'--channel-id',THREAD],input=json.dumps(p),capture_output=True,text=True,timeout=45)
            match=re.search(r'message_id=(\d+)',r.stdout)
            if r.returncode or not match:raise MonitorError('discord_post_unconfirmed')
            entry['message_id']=match.group(1)
        save(store/'state.json',s)
    message=discord_get('channels/'+THREAD+'/messages/'+entry['message_id']);verify_message(message,p)
    entry['verified']=True;entry['verified_at']=iso(dt.datetime.now(UTC));save(store/'state.json',s)

def run(c,s,store,now,mode):
    if s.get('status')=='completed':return {'status':'completed_noop','external_requests':0}
    if s.get('status')=='blocked':return {'status':'blocked_noop','external_requests':0,'reason':s.get('last_error')}
    if mode=='initial':
        key='initial'
        if s['outbox'].get(key,{}).get('verified'):return {'status':'initial_already_verified'}
        if key not in s['outbox']:
            start=iso(now-dt.timedelta(hours=24));end=iso(now)
            data=cf_query(cf_token(),start,end)
            save(store/'initial-reference.json',data)
            detail=f"Referência: {start} a {end} (24h anteriores; fora do acumulado mensal).\nMonitor: {c['start']} a {c['end']}, em UTC. Resumo diário nesta thread; encerramento automático e fechamento final. Apenas vagaaqui.com e www.vagaaqui.com."
            p=payload('initial',key,data,c,detail)
        else:p=s['outbox'][key]['payload']
        deliver(s,key,p,store)
        return {'status':'initial_verified','message_id':s['outbox'][key]['message_id']}
    # Frozen payloads are resumed first, never recomputed or duplicated.
    for key,entry in list(s['outbox'].items()):
        if not entry.get('verified'):deliver(s,key,entry['payload'],store)
    due=[(a,b) for a,b in intervals(c) if parse(b)<=now-dt.timedelta(hours=3)]
    token=None
    for a,b in due:
        key='daily:'+a
        if key not in s['days']:
            if token is None:token=cf_token()
            data=cf_query(token,a,b);s['days'][key]=data;save(store/'state.json',s)
        data=s['days'][key]
        cumulative=aggregate(list(s['days'].values()))
        detail=f"{a} a {b} (UTC; início/fim do mês podem ser parciais).\nAcumulado dos {len(s['days'])} intervalos coletados: {number(cumulative['total'])} requisições estimadas."
        deliver(s,key,payload('daily',key,data,c,detail),store)
    all_intervals=list(intervals(c))
    keys=['daily:'+a for a,b in all_intervals]
    if now>=parse(c['end'])+dt.timedelta(hours=3) and all(k in s['days'] and s['outbox'].get(k,{}).get('verified') for k in keys):
        total=aggregate([s['days'][k] for k in keys]);detail=f"{c['start']} a {c['end']} (UTC).\nCobertura completa: {len(keys)}/{len(keys)} intervalos diários, sem sobreposição. Referência inicial excluída. Coleta encerrada; nenhuma consulta ou publicação posterior."
        deliver(s,'final',payload('final','final',total,c,detail),store)
        s['status']='completed';s['completed_at']=iso(now);save(store/'state.json',s)
    return {'status':s['status'],'closed_intervals':len(s['days']),'expected_intervals':len(all_intervals),'verified_messages':sum(1 for e in s['outbox'].values() if e.get('verified'))}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--initial',action='store_true');parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    STORE.mkdir(exist_ok=True)
    with (STORE/'writer.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print('SKIP writer_busy');return 0
        c=config_read(STORE);s=state_read(STORE);now=dt.datetime.now(UTC)
        if args.dry_run:
            sample=cf_query(cf_token(),iso(now-dt.timedelta(hours=24)),iso(now))
            print(json.dumps({'status':'dry_run_ok','hosts':HOSTS,'total':sample['total'],'countries':len(sample['countries']),'max_sample_interval':sample['max_sample_interval'],'start':c['start'],'end':c['end'],'state_write':False,'discord_write':False}));return 0
        try:
            prior_failures=s.get('failure_streak',0)
            result=run(c,s,STORE,now,'initial' if args.initial else 'scheduled')
            if prior_failures and s.get('status') not in ['blocked']:
                key='recovery:'+s.get('incident_id',iso(now))
                deliver(s,key,payload('recovery',key,None,c,'Leitura e entregas pendentes recuperadas, com GET dos recibos. Intervalos anteriores preservados, sem republicação dos já concluídos.'),STORE)
                s.pop('incident_id',None)
            s['last_check']=iso(now)
            if s.get('status')!='blocked':s['failure_streak']=0;s.pop('last_error',None)
            save(STORE/'state.json',s);print(json.dumps(result));return 0
        except Exception as exc:
            reason=str(exc) if isinstance(exc,MonitorError) else type(exc).__name__
            s['failure_streak']=s.get('failure_streak',0)+1;s['last_error']=reason;s['last_check']=iso(now)
            if getattr(exc,'permanent',False) or s['failure_streak']>=5:s['status']='blocked'
            s['next_action']='Human decision required; preserve missing intervals and receipts.' if s['status']=='blocked' else 'Hourly consumer resumes only missing slices/outbox; no completed effects replayed.'
            save(STORE/'state.json',s)
            if not s.get('incident_id'):s['incident_id']=iso(now)
            failure_key=('blocked:' if s['status']=='blocked' else 'failure:')+s['incident_id']
            if failure_key not in s['outbox']:
                detail=f"Falha: {reason}. Estado: {s['status']}. Nenhum intervalo faltante será contabilizado como zero. "+s['next_action']
                try:deliver(s,failure_key,payload('failure',failure_key,None,c,detail),STORE)
                except Exception:pass
            print(json.dumps({'status':s['status'],'error':reason,'failure_streak':s['failure_streak']}));return 1

if __name__=='__main__':raise SystemExit(main())
