"""Restricted RunCloud SSH: tests use synthetic keys; no real credentials."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from typing import Any

MODULE=Path('/root/mgs-agent/scripts/mgs_runcloud_ssh.py')
REMOTE=Path('/root/mgs-agent/scripts/runcloud-ssh-readonly.py')
MONITOR=Path('/root/mgs-agent/scripts/monitor-runcloud.py')
def load(path,name) -> Any:
    if not path.exists(): return None
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
S=load(MODULE,'ssh_fixture');M=load(MONITOR,'hybrid_fixture')

def fixture(now=1000):
    return {'schema':1,'checked_at':now,'disk':{'total_mb':100000,'used_mb':10000,'available_mb':90000},'services':{'nginx-rc.service':{'load':'loaded','active':'active'}}}
TARGET={'id':'1','name':'Inc','services':['nginx'],'ssh':{'host':'192.0.2.1','user':'zeus','unit_map':{'nginx':'nginx-rc.service'}}}
CFG={'servers':[TARGET],'ssh_key_ref':{'item_id':'fixture-only','vault':'fixture'},'ssh_known_hosts':'/root/.ssh/known_hosts_mgs'}

class SSHTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(S,'SSH collector is not implemented yet')
    def test_key_loader_uses_native_openssh_export(self):
        calls=[];private='-----BEGIN OPENSSH PRIVATE KEY-----\nfixture\n-----END OPENSSH PRIVATE KEY-----\n'
        def run(args,**kwargs):
            calls.append(args)
            output=private if args[1]=='read' else json.dumps({'fields':[{'id':'private_key','value':private}]})
            return subprocess.CompletedProcess(args,0,output,'')
        with patch.object(S.subprocess,'run',side_effect=run):key=S.load_key(CFG)
        self.assertEqual(key,private.encode())
        self.assertEqual(calls[0][1],'read')
        self.assertIn('ssh-format=openssh',calls[0][-1])
    def test_schema_rejects_stale_sample(self):
        with self.assertRaises(S.SSHError):S.validate_health(fixture(700),TARGET,1000)
    def test_schema_rejects_missing_service(self):
        data=fixture();data['services']={}
        with self.assertRaises(S.SSHError):S.validate_health(data,TARGET,1000)
    def test_schema_rejects_invalid_disk(self):
        data=fixture();data['disk']['total_mb']=-1
        with self.assertRaises(S.SSHError):S.validate_health(data,TARGET,1000)
    def test_key_stays_in_memory_and_no_password_fallback(self):
        seen=[]
        def runner(args,**kwargs):
            fd=kwargs['pass_fds'][0];seen.append(fd)
            self.assertEqual(os.pread(fd,100,0),b'fixture-key-not-a-secret')
            self.assertEqual(os.fstat(fd).st_mode & 0o777,0o600)
            self.assertIn('PreferredAuthentications=publickey',args)
            self.assertIn('PasswordAuthentication=no',args)
            self.assertIn('StrictHostKeyChecking=yes',args)
            self.assertIn('IdentityAgent=none',args)
            self.assertIn('IdentityFile=none',args)
            self.assertEqual(args[args.index('-i')+1],'/proc/'+str(os.getpid())+'/fd/'+str(fd))
            self.assertEqual(args[-1],'mgs-health-v1')
            return subprocess.CompletedProcess(args,0,json.dumps(fixture()),'')
        sample=S.read_target(b'fixture-key-not-a-secret',TARGET,CFG['ssh_known_hosts'],runner=runner,now=1000)
        self.assertEqual(sample['schema'],1)
        with self.assertRaises(OSError):os.fstat(seen[0])
    def test_error_never_contains_raw_stderr(self):
        def runner(args,**kwargs):return subprocess.CompletedProcess(args,255,'','Permission denied; fixture-sensitive-marker')
        with self.assertRaises(S.SSHError) as caught:S.read_target(b'fixture',TARGET,CFG['ssh_known_hosts'],runner=runner,now=1000)
        self.assertEqual(caught.exception.code,'ssh_auth_failed')
        self.assertNotIn('fixture-sensitive-marker',str(caught.exception))
    def test_invalid_user_or_host_is_rejected(self):
        for ssh in [{'host':'192.0.2.1;touch /x','user':'zeus'},{'host':'192.0.2.1','user':'root'}]:
            with self.subTest(ssh=ssh),self.assertRaises(S.SSHError):S.read_target(b'fixture',{**TARGET,'ssh':{**ssh,'unit_map':{'nginx':'nginx-rc.service'}}},CFG['ssh_known_hosts'],now=1000)
    def test_health_continues_without_provider_api(self):
        obs,summary=S.collect_health(CFG,1000,key_loader=lambda c:b'fixture',target_reader=lambda *a,**k:fixture())
        self.assertEqual(summary['ssh_errors'],[])
        self.assertEqual(obs['1:ssh']['severity'],0)
        self.assertEqual(obs['1:service:nginx']['severity'],0)
        self.assertNotIn('1:connection',obs)
    def test_service_stopped_requires_second_probe(self):
        data=fixture();data['services']['nginx-rc.service']['active']='inactive';calls=[]
        def read(*args,**kwargs):calls.append(1);return data
        obs,summary=S.collect_health(CFG,1000,key_loader=lambda c:b'fixture',target_reader=read)
        self.assertEqual(len(calls),2)
        self.assertEqual(obs['1:service:nginx']['severity'],2)
        self.assertTrue(obs['1:service:nginx']['confirmed'])
    def test_ssh_auth_error_is_not_server_offline_or_service_stopped(self):
        def read(*args,**kwargs):raise S.SSHError('ssh_auth_failed')
        obs,summary=S.collect_health(CFG,1000,key_loader=lambda c:b'fixture',target_reader=read)
        self.assertEqual(obs['1:ssh']['severity'],2)
        self.assertNotIn('1:service:nginx',obs)
        self.assertNotIn('1:connection',obs)
    def test_private_key_lookup_failure_is_not_host_failure(self):
        def key(cfg):raise S.SSHError('credential_unavailable')
        obs,summary=S.collect_health(CFG,1000,key_loader=key,target_reader=lambda *a,**k:fixture())
        self.assertEqual(obs['monitor:ssh']['severity'],2)
        self.assertNotIn('1:ssh',obs)

class RemoteGuardTests(unittest.TestCase):
    def test_forced_command_rejects_arbitrary_input(self):
        self.assertTrue(REMOTE.exists(),'Restricted remote collector is missing')
        for command in ['', 'id', 'sh', 'mgs-health-v1; id','mgs-health-v1 ', 'sftp', 'scp -t /home/zeus/x']:
            with self.subTest(command=command):
                env={**os.environ,'SSH_ORIGINAL_COMMAND':command};env.pop('SSH_TTY',None)
                p=subprocess.run([sys.executable,'-I',str(REMOTE)],env=env,capture_output=True,text=True,timeout=20)
                self.assertEqual(p.returncode,126)
                self.assertEqual(p.stdout,'')
    def test_forced_command_rejects_pty(self):
        self.assertTrue(REMOTE.exists(),'Restricted remote collector is missing')
        p=subprocess.run([sys.executable,'-I',str(REMOTE)],env={**os.environ,'SSH_ORIGINAL_COMMAND':'mgs-health-v1','SSH_TTY':'/dev/pts/fixture'},capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,126)
    def test_allowed_collector_emits_real_read_only_json(self):
        self.assertTrue(REMOTE.exists(),'Restricted remote collector is missing')
        env={**os.environ,'SSH_ORIGINAL_COMMAND':'mgs-health-v1'};env.pop('SSH_TTY',None)
        p=subprocess.run([sys.executable,'-I',str(REMOTE)],env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr)
        d=json.loads(p.stdout);self.assertEqual(d['schema'],1)
        self.assertGreater(d['disk']['total_mb'],0)

class HybridTests(unittest.TestCase):
    def test_monthly_quota_does_not_disable_ssh_health(self):
        self.assertTrue(hasattr(M,'collect_hybrid'),'Hybrid dispatcher is missing')
        state=M.fresh_state();state['api_control']={'kind':'monthly_quota','retry_at':9999,'observed_at':900}
        called=[]
        def health(cfg,now):called.append('ssh');return {'1:ssh':{'server':'Inc','severity':0,'detail':'SSH','confirmed':True}},{'servers':[{'server':'Inc'}],'ssh_errors':[],'ssh_attempts':1}
        def provider(cfg,state,now,force=False):return M.deferred_collection(state['api_control'])
        obs,summary=M.collect_hybrid({**CFG,'health_transport':'ssh'},state,1000,health_collector=health,provider_collector=provider)
        self.assertEqual(called,['ssh']);self.assertEqual(obs['1:ssh']['severity'],0)
        self.assertEqual(obs['monitor:api']['severity'],2)
        self.assertEqual(summary['api_calls'],0)
        self.assertEqual(summary['status'],'health_ok_backups_deferred')
        self.assertEqual(state['api_control']['retry_at'],9999)
    def test_provider_mode_skips_host_endpoints_when_health_is_ssh(self):
        self.assertTrue(hasattr(M,'collect_hybrid'),'Hybrid dispatcher is missing')
        class API:
            failures=0;calls=0;control={}
            def get(self,path):raise AssertionError('Provider host endpoint must not be called')
            def pages(self,path):return []
        obs,summary=M.collect(API(),{**CFG,'health_transport':'ssh','webapp_servers':{},'backup_cadence_seconds':86400,'backup_max_age_hours':36},M.fresh_state(),1000000,True)
        self.assertEqual(summary['servers'],[])
        self.assertEqual(obs['monitor:api']['severity'],0)

if __name__=='__main__':unittest.main(verbosity=2)
