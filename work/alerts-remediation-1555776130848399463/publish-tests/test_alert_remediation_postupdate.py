from __future__ import annotations
import asyncio
import copy
import importlib.util
import importlib.machinery
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
import pytest  # type: ignore[import-not-found]

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import mgs_alert_transport as transport  # type: ignore[import-not-found]
import mgs_scheduler_health as scheduler  # type: ignore[import-not-found]
import mgs_official_release as releases  # type: ignore[import-not-found]
import mgs_restart_attribution as restarts  # type: ignore[import-not-found]
import mgs_hermes_news as news  # type: ignore[import-not-found]
import mgs_sb_session as sb_session  # type: ignore[import-not-found]
import mgs_learning_origin as learning  # type: ignore[import-not-found]


def load(name):
    path = SCRIPTS / name
    loader = importlib.machinery.SourceFileLoader('fixture_' + name.replace('.', '_').replace('-', '_'), str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class DiscordFixture:
    def __init__(self):
        self.posts = []; self.messages = {}; self.fail_post = False; self.fail_get = False; self.headers = []
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args): pass
            def reply(self, code, data):
                raw = json.dumps(data).encode(); self.send_response(code); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(raw)
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length']))); owner.headers.append(self.headers.get('Authorization'))
                if owner.fail_post: self.reply(503, {'message':'fixture outage'}); return
                mid = str(1000 + len(owner.posts)); owner.posts.append(payload); owner.messages[mid] = {'id':mid, **copy.deepcopy(payload)}; self.reply(200, owner.messages[mid])
            def do_PATCH(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                mid = self.path.rsplit('/', 1)[-1]
                owner.messages[mid].update(payload)
                self.reply(200, owner.messages[mid])
            def do_GET(self):
                if owner.fail_get: self.reply(503, {'message':'fixture GET outage'}); return
                mid = self.path.rsplit('/', 1)[-1]; self.reply(200, owner.messages[mid])
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}/channels/fixture/messages'
    def close(self): self.server.shutdown(); self.server.server_close(); self.thread.join()


@pytest.fixture
def discord(monkeypatch):
    server = DiscordFixture()
    monkeypatch.setenv('MGS_DISCORD_API_URL_OVERRIDE', server.url)
    monkeypatch.setenv('MGS_DISCORD_BOT_TOKEN_OVERRIDE', 'fixture-not-a-production-credential')
    yield server
    server.close()


def cron_env(tmp, monkeypatch, lines):
    b = tmp / 'bin'; b.mkdir()
    crontab = b / 'crontab'; crontab.write_text('#!/usr/bin/env python3\nprint(' + repr(lines) + ', end="")\n'); crontab.chmod(0o700)
    monkeypatch.setenv('PATH', str(b) + ':' + os.environ['PATH']); monkeypatch.setenv('CRON_STALE_STATE', str(tmp / 'state.json'))
    return tmp / 'state.json'


def run_cron():
    return subprocess.run(['bash', str(SCRIPTS / 'monitor-cron-stale-logs.sh')], capture_output=True, text=True, timeout=30)


def test_transport_requires_exact_readback_and_does_not_repeat_post(discord):
    payload = {'content':'', 'embeds':[{'title':'fixture', 'color':3447003, 'fields':[{'name':'item', 'value':'value'}]}], 'allowed_mentions':{'parse':[], 'users':[], 'roles':[], 'replied_user':False}}
    discord.fail_get = True; saved = []
    with pytest.raises(RuntimeError): transport.post_verified(payload, on_created=saved.append)
    assert len(saved) == 1 and len(discord.posts) == 1
    discord.fail_get = False
    assert transport.post_verified(payload, prior_id=saved[0]) == saved[0]
    assert len(discord.posts) == 1
    assert discord.headers == ['Bot fixture-not-a-production-credential']


def test_cron_failure_keeps_outbox_and_success_retries_without_duplicate(tmp_path, monkeypatch, discord):
    log = tmp_path / 'job.log'; log.write_text('[now] ERROR: fixture failed\n')
    state = cron_env(tmp_path, monkeypatch, f'*/15 * * * * /root/mgs-agent/scripts/fixture-monitor.py >> {log} 2>&1\n')
    discord.fail_get = True; p = run_cron(); assert p.returncode == 1, p.stderr
    first = json.loads(state.read_text()); assert first['alerts']['fixture-monitor.py']['last_alert'] == 0
    assert first['outbox']['fixture-monitor.py']['message_id'] and len(discord.posts) == 1
    discord.fail_get = False; p = run_cron(); assert p.returncode == 0, p.stderr
    second = json.loads(state.read_text()); assert second['alerts']['fixture-monitor.py']['last_alert'] > 0 and not second['outbox'] and len(discord.posts) == 1
    second['alerts']['fixture-monitor.py']['last_alert'] = int(time.time()) - 7*3600
    state.write_text(json.dumps(second))
    p = run_cron(); assert p.returncode == 0 and len(discord.posts) == 1, p.stderr
    registered = json.loads(state.read_text())['alerts']['fixture-monitor.py']['message_id']
    assert discord.messages[registered]['content'] == ''
    log.write_text('[now] OK fixture recovered\n'); p = run_cron(); assert p.returncode == 0, p.stderr
    recovered = json.loads(state.read_text()); assert not recovered['alerts'] and not recovered['outbox']
    assert len(discord.posts) == 2 and discord.posts[-1]['content'] == '' and not discord.posts[-1]['allowed_mentions']['users']


def test_cron_missing_transport_recovered_before_post_does_not_fake_green(tmp_path, monkeypatch, discord):
    log = tmp_path / 'job.log'; log.write_text('ERROR: fixture failed\n')
    state = cron_env(tmp_path, monkeypatch, f'* * * * * /root/mgs-agent/scripts/fixture-monitor.py >> {log} 2>&1\n')
    discord.fail_post = True; p = run_cron(); assert p.returncode == 1, p.stderr
    assert json.loads(state.read_text())['outbox']
    log.write_text('[now] OK fixture recovered\n'); discord.fail_post = False
    p = run_cron(); assert p.returncode == 0, p.stderr
    data = json.loads(state.read_text()); assert not data['alerts'] and not data['outbox'] and data['suppressed_transients']
    assert discord.posts == []


def test_cron_finance_outside_scripts_prefix_is_observed(tmp_path, monkeypatch):
    log = tmp_path / 'finance.log'; log.write_text('[now] OK finance fixture\n')
    cron_env(tmp_path, monkeypatch, f'3 9 * * * /root/mgs-agent/apps/finance-system/finance_media_spend_sync.py >> {log} 2>&1\n')
    p = subprocess.run(['bash', str(SCRIPTS/'monitor-cron-stale-logs.sh'), '--dry-run'],capture_output=True,text=True)
    assert p.returncode == 0 and 'apps/finance-system/finance_media_spend_sync.py' in p.stdout and 'problems=0' in p.stdout


def test_native_delivery_failures_overdue_and_paused_are_distinct(tmp_path):
    now = time.time()
    for profile in ('zeus','atena','ares'):
        p = tmp_path/profile/'cron'; p.mkdir(parents=True)
        jobs = [] if profile != 'zeus' else [
            {'id':'a','enabled':True,'state':'scheduled','last_status':'ok','last_delivery_error':'fixture','next_run_at':datetime.fromtimestamp(now+60,timezone.utc).isoformat()},
            {'id':'b','enabled':True,'state':'scheduled','last_status':'ok','next_run_at':datetime.fromtimestamp(now-3600,timezone.utc).isoformat()},
            {'id':'c','enabled':False,'state':'paused','last_status':'error'},
            {'id':'d','enabled':True,'state':'scheduled','last_status':'ok','next_run_at':datetime.fromtimestamp(now+8*3600,timezone.utc).isoformat()},
        ]
        (p/'jobs.json').write_text(json.dumps({'jobs':jobs}))
    values = {key:(status,detail) for key,status,detail in scheduler.native_rows(now,tmp_path)}
    assert values['hermes:zeus:a'][0]=='ERROR' and 'delivery' in values['hermes:zeus:a'][1]
    assert values['hermes:zeus:b'][0]=='STALE' and 'hermes:zeus:c' not in values and values['hermes:zeus:d'][0]=='OK'


def test_native_unreadable_store_is_not_healthy_zero(tmp_path):
    assert all(status=='ERROR' for _,status,_ in scheduler.native_rows(time.time(),tmp_path))


@pytest.mark.parametrize('meta',[{'tag_name':'v2026.9.24','draft':False,'prerelease':True},{'tag_name':'rc.35-v0.21.5','draft':False,'prerelease':False},{'tag_name':'v2026.9.24','draft':True,'prerelease':False}])
def test_official_release_rejects_prerelease_and_classification_conflict(tmp_path, monkeypatch, meta):
    p=tmp_path/'release.json';p.write_text(json.dumps(meta));monkeypatch.setenv('HERMES_MONITOR_RELEASE_METADATA_FILE',str(p))
    with pytest.raises(RuntimeError): releases.latest_release(str(tmp_path),'https://github.com/NousResearch/hermes-agent.git')


def test_official_release_uses_metadata_not_nearest_rc(tmp_path, monkeypatch):
    p=tmp_path/'release.json';p.write_text(json.dumps({'tag_name':'v2026.9.24','draft':False,'prerelease':False}));monkeypatch.setenv('HERMES_MONITOR_RELEASE_METADATA_FILE',str(p))
    assert releases.latest_release(str(tmp_path),'https://github.com/NousResearch/hermes-agent.git')=='v2026.9.24'


def test_restarts_do_not_infer_monarx_from_agent_start():
    answer=restarts.infer('zeus-gateway',10000,'Started monarx-agent',boot_epoch=9000,pid='1',receipts=[])
    assert answer.startswith('Causa não atribuída')
    assert restarts.infer('zeus-gateway',10000,'Started monarx-agent',boot_epoch=9900,pid='1',receipts=[]).startswith('Reboot do host confirmado')
    assert restarts.infer('zeus-gateway',10000,'apt-get install monarx-agent',boot_epoch=8000,pid='1',receipts=[]).startswith('Atualização do pacote Monarx')


def test_restarts_require_matching_receipt_pid_and_window():
    receipt={'status':'completed','runtime_validated':True,'started_at':'2026-10-03T02:19:00+00:00','validated_at':'2026-10-03T02:55:00+00:00','gateways':{'zeus':{'pid':7,'active':True,'code_matches':True}}}
    epoch=datetime.fromisoformat('2026-10-03T02:30:00+00:00').timestamp()
    assert restarts.infer('zeus-gateway',epoch,'',boot_epoch=1,pid=7,receipts=[receipt]).startswith('Ativação Hermes validada')
    assert restarts.infer('zeus-gateway',epoch,'',boot_epoch=1,pid=8,receipts=[receipt]).startswith('Causa não atribuída')


def test_oauth_current_models_unknown_billing_is_not_confirmed_charge(tmp_path,monkeypatch):
    module=load('monitor-gpt55-oauth-cost.sh');now=datetime.now(timezone.utc)
    for profile in module.PROFILES:
        folder=tmp_path/profile;folder.mkdir();(folder/'config.yaml').write_text('model:\n  default: gpt-6.1-sol\n  provider: openai-codex\n')
        with sqlite3.connect(folder/'state.db') as db:
            db.execute('CREATE TABLE sessions(id TEXT,source TEXT)')
            db.execute('CREATE TABLE session_model_usage(session_id TEXT,model TEXT,billing_provider TEXT,billing_mode TEXT,api_call_count INTEGER,input_tokens INTEGER,output_tokens INTEGER,cache_read_tokens INTEGER,cache_write_tokens INTEGER,reasoning_tokens INTEGER,actual_cost_usd REAL,first_seen REAL,last_seen REAL)')
            db.execute('INSERT INTO sessions VALUES(?,?)',('fixture','cli'))
            db.execute('INSERT INTO session_model_usage VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',('fixture','gpt-5.6-sol','openai-codex','unknown',1,100,20,0,0,0,0,now.timestamp()-30,now.timestamp()-10))
    monkeypatch.setattr(module,'PROFILES_ROOT',tmp_path);payload,result=module.build_report(now)
    assert result['config_ok'] and result['billing_ok'] and result['billing_unknown'] and not result['unexpected_usage']
    assert 'GPT-5.6' not in payload['embeds'][0]['title'] and 'não é cobrança confirmada' in json.dumps(payload,ensure_ascii=False)
    assert payload['embeds'][0]['color']==3447003


def test_own_git_alert_does_not_invoke_model(tmp_path,monkeypatch):
    module=load('hermes-news-explainer.py')
    source={'id':'2','author':{'id':module.ZEUS_BOT_ID},'content':'','embeds':[{'title':'Hermes Agent — novidades em desenvolvimento','fields':[{'name':'Atualização estável','value':'Nenhuma — já contida'},{'name':'Última release oficial','value':'v2026.9.24'},{'name':'Runtime MGS','value':'current'},{'name':'Main de desenvolvimento','value':'Main pendente no runtime:18 commits'}]}]}
    state={'last_seen_id':'1','processed':{}}
    monkeypatch.setattr(module,'load_token',lambda:'fixture');monkeypatch.setattr(module,'load_state',lambda:state);monkeypatch.setattr(module,'save_state',lambda s:None)
    monkeypatch.setattr(module,'api',lambda *args:[source]);monkeypatch.setattr(module,'post_reply',lambda *args:{'id':'3'})
    monkeypatch.setattr(module,'explain',lambda *args:(_ for _ in ()).throw(AssertionError('must not call model')));monkeypatch.setattr(module.time,'sleep',lambda *_:None);monkeypatch.setattr(sys,'argv',['fixture'])
    assert module.main()==0 and state['processed']['2']['reply_id']=='3'
    assert '18 commits' in news.explain_monitor(source)


def test_resolver_accepts_actual_native_cron_envelope_but_not_ordinary_prose():
    module=load('alerts-infra-failed-alert-resolver.py')
    source={'id':'1','author':{'id':module.ZEUS_BOT_ID,'bot':True},'embeds':[],'content':'Cronjob Response: Financeiro\n(job_id: 685397627b29)\nAtualização automática falhou.'}
    assert module.is_candidate(source)
    source['content']='Atualização automática falhou.';assert not module.is_candidate(source)
    assert module.safe_error(subprocess.TimeoutExpired(['fixture','sensitive-prompt'],30))=='TimeoutExpired seconds=30'
    assert 'sensitive-prompt' not in module.safe_error(subprocess.CalledProcessError(1,['fixture','sensitive-prompt']))


def test_resolver_paginate_to_cursor_and_never_drop_backlog(monkeypatch):
    module=load('alerts-infra-failed-alert-resolver.py');calls=[]
    def fetch(token,limit,before=None):
        calls.append(before)
        return [{'id':str(x)} for x in ([10,9] if before is None else [8,7])]
    monkeypatch.setattr(module,'_fetch_page',fetch)
    assert len(module.fetch_messages('fixture',2,'7'))==4 and calls==[None,'9']
    assert module.build_feedback_payload({'id':'1','content':'<@344196393512075265>'},'Resolvido e validado por readback.')['content']==''
    assert module.build_feedback_payload({'id':'1'},'Bloqueado: Critical Subset exige confirmação.')['content']=='<@344196393512075265>'


def test_sb_read_refresh_reuses_context_and_true_expiry_is_fail_closed():
    async def scenario():
        headers={'authorization':'fixture-a'};ready=asyncio.Event();ready.set()
        class Response:
            def __init__(self,status):self.status=status
        class Request:
            def __init__(self):self.statuses=[401,200];self.calls=0
            async def get(self,*args,**kwargs):self.calls+=1;return Response(self.statuses.pop(0))
        class Page:
            url='https://app.smartbiddingdigital.com/accounts'
            reloads=0
            async def reload(self,**kwargs):self.reloads+=1;headers['authorization']='fixture-b';ready.set()
        request=Request();ctx=type('Ctx',(),{'request':request})();page=Page()
        result,h=await sb_session.company_probe(ctx,page,headers,ready)
        assert result.status==200 and request.calls==2 and page.reloads==1
        page.url='https://app.smartbiddingdigital.com/login'
        with pytest.raises(RuntimeError,match='canonical login required'):
            await sb_session.company_probe(ctx,page,headers,ready)
        assert request.calls==2
    asyncio.run(scenario())


def test_sb_shared_lease_never_overlaps_state_writers(tmp_path):
    async def scenario():
        running=0;peak=0
        async def task():
            nonlocal running,peak
            async with sb_session.session_lease(tmp_path/'state.json',timeout=2):
                running+=1;peak=max(peak,running);await asyncio.sleep(.02);running-=1
        await asyncio.gather(task(),task());assert peak==1
    asyncio.run(scenario())


def test_vps_warning_recovery_hysteresis_does_not_hide_critical():
    module=load('monitor-vps-health.py')
    metrics={'disk_root':{'used_pct':74.5},'load':{'load15':0}}
    old={'disk_root':{'severity':'warning'}}
    held=module.warning_hysteresis([],metrics,old);assert held[0]['severity']=='warning'
    metrics['disk_root']['used_pct']=72;assert not module.warning_hysteresis([],metrics,old)
    critical={'key':'disk_root','severity':'critical','detail':'fixture'}
    assert module.warning_hysteresis([critical],metrics,old)==[critical]


def test_vps_pending_delivery_retry_and_recovery_preserve_public_incident(tmp_path,monkeypatch,discord):
    module=load('monitor-vps-health.py');state={'alerts':{}}
    issue={'key':'disk_root','severity':'critical','title':'fixture','detail':'fixture disk'}
    active=[issue];metrics={'disk_root':{'used_pct':90,'free_gb':1},'load':{'load15':0},'updates':{}}
    monkeypatch.setattr(module,'log',lambda *_:None);monkeypatch.setattr(module,'load_env_file',lambda *_:None);monkeypatch.setattr(module,'load_state',lambda:copy.deepcopy(state))
    def save(s):state.clear();state.update(copy.deepcopy(s))
    monkeypatch.setattr(module,'save_state',save);monkeypatch.setattr(module,'collect',lambda *_:(copy.deepcopy(active),copy.deepcopy(metrics),{}));monkeypatch.setattr(module,'apt_updates_metrics',lambda **_: {})
    monkeypatch.setattr(module,'issue_payload',lambda *args:{'content':'','embeds':[{'title':'fixture critical','color':15158332}]})
    monkeypatch.setattr(module,'resolved_payload',lambda *args:{'content':'','embeds':[{'title':'fixture recovered','color':3066993}]});monkeypatch.setattr(sys,'argv',['fixture'])
    discord.fail_get=True;assert module.main()==1
    assert state['pending_notifications'] and len(discord.posts)==1 and not state['alerts']['disk_root'].get('last_alert')
    discord.fail_get=False;assert module.main()==0 and not state['pending_notifications'] and len(discord.posts)==1
    active.clear();metrics['disk_root']['used_pct']=60
    assert module.main()==0 and not state['alerts'] and len(discord.posts)==2 and discord.posts[-1]['content']==''


def test_isolated_learning_scope_and_coalescing(tmp_path,monkeypatch):
    profiles=tmp_path/'profiles';repo=tmp_path/'repo';origin='1555572634228490283'
    live=profiles/'zeus/skills/ops/demo/SKILL.md';mirror=repo/'profiles/zeus-skills/ops/demo/SKILL.md'
    record={'profile':'zeus','subsystem':'skills','session':{'platform':'discord','thread_id':origin},'correlation_id':'a','before':{str(live):'old'},'after':{str(live):'new'}}
    assert learning.origin_channel(record,profiles)==origin
    assert learning.origin_channel({**record,'profile':'ares'},profiles) is None
    outside=profiles/'zeus/config.yaml';assert learning.origin_channel({**record,'after':{str(outside):'new'}},profiles) is None
    posted=[];patched=[];actual={}
    def post(payload,**kwargs):
        actual.update(copy.deepcopy(payload));posted.append(payload);kwargs['on_created']('1234');return '1234'
    def request(method,url,payload=None):
        if method=='PATCH':
            assert isinstance(payload, dict)
            actual.clear();actual.update(copy.deepcopy(payload));patched.append(payload)
        return {'id':'1234','mentions':[],**copy.deepcopy(actual)}
    monkeypatch.setattr(learning,'post_verified',post);monkeypatch.setattr(learning,'request',request)
    assert learning.publish_learning(record,[str(mirror)],repo_root=repo,profiles_root=profiles)=='1234'
    assert learning.publish_learning({**record,'correlation_id':'b'},[str(mirror.with_name('reference.md'))],repo_root=repo,profiles_root=profiles)=='1234'
    assert len(posted)==1 and len(patched)==1 and 'SKILL.md' in actual['embeds'][0]['description'] and 'reference.md' in actual['embeds'][0]['description']
