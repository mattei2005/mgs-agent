"""Restricted SSH health collector; the private key never enters disk or argv."""
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

WRAPPER='/root/mgs-agent/scripts/mgs-op-with-service-account.sh'
COMMAND='mgs-health-v1'

class SSHError(Exception):
    def __init__(self,code):self.code=code;super().__init__(code)

def load_key(cfg):
    ref=cfg.get('ssh_key_ref',{})
    if not ref.get('item_id') or not ref.get('vault'):raise SSHError('credential_reference_missing')
    try:
        p=subprocess.run([WRAPPER,'item','get',ref['item_id'],'--vault',ref['vault'],'--format','json','--reveal'],capture_output=True,text=True,timeout=45)
        if p.returncode:raise SSHError('credential_unavailable')
        item=json.loads(p.stdout)
        key=next((f.get('value') for f in item.get('fields',[]) if f.get('id')=='private_key'),None)
        if not isinstance(key,str) or not key.startswith('-----BEGIN OPENSSH PRIVATE KEY-----'):raise SSHError('credential_invalid')
        return key.encode()
    except (OSError,ValueError,subprocess.SubprocessError):raise SSHError('credential_unavailable') from None

def validate_health(data,target,now):
    try:
        if not isinstance(data,dict) or data.get('schema')!=1:raise ValueError()
        observed=data['checked_at']
        if isinstance(observed,bool) or not isinstance(observed,(int,float)) or not math.isfinite(observed) or abs(now-observed)>120:raise ValueError()
        disk=data['disk'];values=[disk[k] for k in ['total_mb','used_mb','available_mb']]
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in values):raise ValueError()
        total,used,free=values
        if total<=0 or used<0 or free<0 or used>total or free>total or used+free>total*1.01:raise ValueError()
        for name in target['services']:
            unit=target['ssh']['unit_map'][name]
            if not re.fullmatch(r'[A-Za-z0-9_.@-]+\.service',unit):raise ValueError()
            value=data['services'][unit]
            if value.get('load')!='loaded' or value.get('active') not in ['active','inactive','failed','activating','deactivating','reloading']:raise ValueError()
    except (KeyError,TypeError,ValueError,AttributeError):raise SSHError('ssh_invalid_sample') from None
    return data

def read_target(key,target,known_hosts,runner=None,now=None):
    runner=runner or subprocess.run
    ssh=target.get('ssh',{})
    try:
        host=str(ipaddress.ip_address(ssh['host']))
        if ssh['user']!='zeus':raise ValueError()
        if not Path(known_hosts).is_file():raise ValueError()
    except (ValueError,KeyError,TypeError):raise SSHError('ssh_invalid_target') from None
    fd=os.memfd_create('mgs-runcloud-monitor-key',os.MFD_CLOEXEC)
    try:
        os.fchmod(fd,0o600)
        view=memoryview(key)
        while view:
            written=os.write(fd,view);view=view[written:]
        os.lseek(fd,0,os.SEEK_SET)
        args=['/usr/bin/ssh','-F','/dev/null','-T','-i','/proc/self/fd/'+str(fd),'-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','BatchMode=yes','-o','PreferredAuthentications=publickey','-o','PasswordAuthentication=no','-o','KbdInteractiveAuthentication=no','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known_hosts),'-o','GlobalKnownHostsFile=/dev/null','-o','ConnectTimeout=12','-o','ConnectionAttempts=1','-o','LogLevel=ERROR','-l','zeus',host,COMMAND]
        p=runner(args,pass_fds=(fd,),capture_output=True,text=True,timeout=35)
        if p.returncode:
            error=p.stderr.lower()
            code='ssh_host_key_failed' if 'host key' in error or 'host identification' in error else 'ssh_auth_failed' if 'permission denied' in error else 'ssh_command_denied' if 'access denied' in error else 'ssh_unreachable'
            raise SSHError(code)
        if len(p.stdout)>65536:raise SSHError('ssh_invalid_sample')
        try:data=json.loads(p.stdout)
        except ValueError:raise SSHError('ssh_invalid_sample') from None
        return validate_health(data,target,time.time() if now is None else now)
    except (OSError,subprocess.SubprocessError):raise SSHError('ssh_transport_error') from None
    finally:os.close(fd)

def disk_severity(disk):
    total=disk['total_mb'];used=disk['used_mb'];free=disk['available_mb'];pct=100*used/total
    return (2 if pct>=90 or free<1024 else 1 if pct>=80 or free<5120 else 0),pct

def collect_health(cfg,now,key_loader=None,target_reader=None):
    key_loader=key_loader or load_key;target_reader=target_reader or read_target
    observations={};servers=[];errors=[];attempts=0
    try:key=key_loader(cfg)
    except SSHError as e:
        return {'monitor:ssh':{'server':'Monitor SSH','severity':2,'detail':'Credencial dedicada de monitoramento indisponível; nenhum acesso alternativo utilizado.','confirmed':True}},{'servers':[],'ssh_errors':[e.code],'ssh_attempts':0}
    for target in cfg['servers']:
        sid=target['id'];name=target['name']
        try:
            attempts+=1;data=target_reader(key,target,cfg['ssh_known_hosts'],now=now)
            validate_health(data,target,now)
            severity,pct=disk_severity(data['disk'])
            if severity==2 or any(data['services'][target['ssh']['unit_map'][s]]['active']!='active' for s in target['services']):
                attempts+=1;data=target_reader(key,target,cfg['ssh_known_hosts'],now=now);validate_health(data,target,now);severity,pct=disk_severity(data['disk'])
            observations[sid+':ssh']={'server':name,'severity':0,'detail':'Coleta SSH restrita validada; não representa o estado do agente RunCloud.','confirmed':True}
            observations[sid+':disk']={'server':name,'severity':severity,'detail':f"Disco via SSH: {pct:.1f}% ocupado; livre {data['disk']['available_mb']/1024:.1f} GiB.",'confirmed':severity==2}
            for service in target['services']:
                active=data['services'][target['ssh']['unit_map'][service]]['active']=='active'
                observations[sid+':service:'+service]={'server':name,'severity':0 if active else 2,'detail':('Serviço ativo via SSH: ' if active else 'Serviço esperado parado, confirmado via SSH: ')+service,'confirmed':not active}
            servers.append({'server':name,'source':'ssh','disk_pct':round(pct,2),'expected_services':len(target['services']),'services_running':all(data['services'][target['ssh']['unit_map'][s]]['active']=='active' for s in target['services'])})
        except SSHError as e:
            errors.append(name+':'+e.code)
            observations[sid+':ssh']={'server':name,'severity':2,'detail':'Coleta SSH indisponível ('+e.code+'); parada do servidor/serviços não comprovada.','confirmed':True}
    observations['monitor:ssh']={'server':'Monitor SSH','severity':2 if errors else 0,'detail':'Coleta SSH parcial; preservar estados não observados.' if errors else 'Coleta SSH restrita íntegra nos servidores configurados.','confirmed':True}
    return observations,{'servers':servers,'ssh_errors':errors,'ssh_attempts':attempts}
