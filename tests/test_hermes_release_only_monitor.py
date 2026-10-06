from __future__ import annotations
import copy
import importlib.util
import json
import os
import subprocess
import sys
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import mgs_hermes_release_monitor as monitor
from mgs_hermes_news import explain_monitor
from mgs_official_release import release_metadata

SCRIPT = ROOT / 'scripts/monitor-hermes-updates.sh'


def git(cwd, *args):
    return subprocess.check_output(['git', '-C', str(cwd), '-c', 'user.name=MGS Test',
                                    '-c', 'user.email=test@mgs.invalid', *args], text=True, stderr=subprocess.DEVNULL).strip()


@pytest.fixture
def repo(tmp_path):
    origin, seed, live = [tmp_path / x for x in ['origin.git', 'seed', 'live']]
    origin.mkdir(); seed.mkdir()
    git(origin, 'init', '--bare', '--initial-branch=main')
    git(seed, 'init', '--initial-branch=main')
    (seed / 'one').write_text('one')
    git(seed, 'add', '.'); git(seed, 'commit', '-m', 'feat: initial release')
    first = git(seed, 'rev-parse', 'HEAD'); git(seed, 'tag', 'v2026.1.1')
    git(seed, 'remote', 'add', 'origin', str(origin));git(seed, 'push', 'origin', 'main', '--tags')
    subprocess.run(['git', 'clone', str(origin), str(live)], check=True, capture_output=True)
    state = tmp_path / 'state.json'
    state.write_text(json.dumps({'schema_version': 2, 'latest_tag': 'v2026.1.1', 'latest_release_commit': first,
                                 'last_notified_upstream': first}))
    meta = tmp_path / 'release.json'
    meta.write_text(json.dumps({'tag_name': 'v2026.1.1', 'draft': False, 'prerelease': False,
                                'body': 'Official release notes: reliability improvements.'}))
    env = {**os.environ, 'HERMES_MONITOR_SKIP_ENV_LOAD': '1', 'HERMES_MONITOR_DIR': str(live),
           'HERMES_MONITOR_UPSTREAM_URL': str(origin), 'HERMES_MONITOR_STATE': str(state),
           'HERMES_MONITOR_LOG': str(tmp_path / 'monitor.log'), 'HERMES_MONITOR_RELEASE_METADATA_FILE': str(meta),
           'HERMES_MONITOR_DRY_RUN_OUTPUT': str(tmp_path / 'payload.json'),
           'HERMES_MONITOR_DRY_RUN': '1', 'DISCORD_BOT_TOKEN': 'isolated-fixture-token'}
    return dict(origin=origin, seed=seed, live=live, first=first, state=state, meta=meta, env=env, tmp=tmp_path)


def advance(r, *, release=False):
    n = len(list(r['seed'].glob('change*')))
    p = r['seed'] / f'change{n}';p.write_text(str(n))
    git(r['seed'], 'add', '.');git(r['seed'], 'commit', '-m', 'fix: new reliability improvement')
    sha = git(r['seed'], 'rev-parse', 'HEAD')
    if release:
        tag = f'v2026.1.{n+2}';git(r['seed'], 'tag', tag)
        r['meta'].write_text(json.dumps({'tag_name': tag, 'draft': False, 'prerelease': False,
                                        'body': 'Improve voice-channel reconnect and plugin task inheritance.'}))
    git(r['seed'], 'push', 'origin', 'main', '--tags')
    return sha


def run(r, **env):
    return subprocess.run(['bash', str(SCRIPT)], cwd=ROOT, env={**r['env'], **env},
                          text=True, capture_output=True, timeout=60)


def test_main_silent_and_dry_state_neutral(repo):
    advance(repo);before=repo['state'].read_bytes()
    cp=run(repo)
    assert cp.returncode == 0, cp.stderr
    assert 'official_release_unchanged' in cp.stdout
    assert 'main_pending=1' in cp.stdout
    assert not Path(repo['env']['HERMES_MONITOR_DRY_RUN_OUTPUT']).exists()
    assert repo['state'].read_bytes() == before


def test_production_main_updates_observation_without_credentials_or_post(repo):
    advance(repo)
    cp=run(repo,HERMES_MONITOR_DRY_RUN='0',DISCORD_BOT_TOKEN='',HERMES_MONITOR_ZEUS_ENV=str(repo['tmp']/'absent'))
    assert cp.returncode == 0,cp.stderr
    state=json.loads(repo['state'].read_text())
    assert state['main_commits_pending']==1 and state['stable_commits_pending']==0
    assert state['last_notified_release_commit']==repo['first']
    assert state['last_notified_upstream']==repo['first']
    assert state['notification_policy']=='official-release-only'


@pytest.mark.parametrize('kind',['clone','worktree'])
def test_resolves_active_launcher_clone_or_linked_worktree(repo,kind):
    live=repo['live']
    if kind=='worktree':
        live=repo['tmp']/'linked';git(repo['seed'],'worktree','add','--detach',str(live),repo['first'])
    launcher=repo['tmp']/'hermes';launcher.write_text(f'#!{live}/.venv/bin/python3\n');launcher.chmod(0o755)
    cp=run(repo,HERMES_MONITOR_DIR='',HERMES_MONITOR_BIN=str(launcher))
    assert cp.returncode==0,cp.stderr
    assert f'runtime_dir={live}' in cp.stdout


def test_frozen_origin_does_not_hide_upstream(repo):
    frozen=repo['tmp']/'frozen.git';frozen.mkdir();git(frozen,'init','--bare','--initial-branch=main')
    git(repo['live'],'remote','set-url','origin',str(frozen))
    advance(repo)
    cp=run(repo)
    assert cp.returncode==0 and 'main_pending=1' in cp.stdout


def test_runtime_change_and_rc_tag_do_not_trigger(repo):
    advance(repo);git(repo['live'],'fetch','origin')
    git(repo['live'],'checkout','--detach','origin/main');git(repo['live'],'tag','rc.35-v0.21.5')
    cp=run(repo)
    assert cp.returncode==0 and 'official_release_unchanged' in cp.stdout
    assert not Path(repo['env']['HERMES_MONITOR_DRY_RUN_OUTPUT']).exists()


def test_new_official_release_payload_uses_release_delta_not_main_or_runtime(repo):
    second=advance(repo,release=True);advance(repo)
    cp=run(repo)
    assert cp.returncode==0,cp.stderr
    payload=json.loads(Path(repo['env']['HERMES_MONITOR_DRY_RUN_OUTPUT']).read_text())
    e=payload['embeds'][0];fields={x['name']:x['value'] for x in e['fields']}
    assert e['title']==monitor.TITLE
    assert 'Fixes 1' in fields['Desde a versão oficial anterior']
    assert second[:10] in fields['Última release oficial']
    assert 'Main de desenvolvimento' not in fields
    assert 'Improve voice-channel' in e['description']
    assert payload['allowed_mentions']=={'parse':[]}
    assert fields['Atualização estável'].startswith('Disponível: 1')


def test_official_release_announcement_when_already_installed(repo):
    advance(repo,release=True);git(repo['live'],'fetch','origin','--tags');git(repo['live'],'checkout','--detach','origin/main')
    cp=run(repo)
    assert cp.returncode==0,cp.stderr
    f={x['name']:x['value'] for x in json.loads(Path(repo['env']['HERMES_MONITOR_DRY_RUN_OUTPUT']).read_text())['embeds'][0]['fields']}
    assert f['Atualização estável'].startswith('Nenhuma')


@pytest.mark.parametrize('changes',[{'prerelease':True},{'draft':True},{'tag_name':'rc.1-v0.22.0'}])
def test_rejects_nonofficial_metadata_fail_closed(repo,changes):
    m=json.loads(repo['meta'].read_text());m.update(changes);repo['meta'].write_text(json.dumps(m))
    cp=run(repo)
    assert cp.returncode!=0
    assert not Path(repo['env']['HERMES_MONITOR_DRY_RUN_OUTPUT']).exists()


def test_missing_state_baselines_without_backlog_spam(repo):
    advance(repo,release=True)
    missing=repo['tmp']/'never-existed-state.json'
    cp=run(repo,HERMES_MONITOR_DRY_RUN='0',HERMES_MONITOR_STATE=str(missing),DISCORD_BOT_TOKEN='',HERMES_MONITOR_ZEUS_ENV=str(repo['tmp']/'absent'))
    assert cp.returncode==0,cp.stderr
    assert json.loads(missing.read_text())['status']=='release-baseline-initialized'


@pytest.fixture
def discord_server():
    record={'posts':[],'messages':{},'fail_post':False,'fail_read':False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def respond(self,status,body):
            self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(body).encode())
        def do_POST(self):
            assert self.headers['Authorization']=='Bot isolated-fixture-token'
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            record['posts'].append(body)
            if record['fail_post']:
                self.respond(429,{'retry_after':1});return
            mid='1556909999999999999'
            record['messages'][mid]={**body,'id':mid,'author':{'id':monitor.BOT_ID}}
            self.respond(200,record['messages'][mid])
        def do_GET(self):
            if record['fail_read']:
                self.respond(503,{});return
            if '?' in self.path:
                self.respond(200,list(record['messages'].values()));return
            self.respond(200,record['messages'][self.path.rsplit('/',1)[-1]])
    server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}/api/v10',record
    server.shutdown();thread.join();server.server_close()


def test_mock_delivery_readback_dedupe_same_release_and_later_main(repo,discord_server):
    url,record=discord_server;second=advance(repo,release=True)
    env={'HERMES_MONITOR_DRY_RUN':'0','HERMES_MONITOR_API_BASE':url}
    cp=run(repo,**env);assert cp.returncode==0,cp.stderr
    state=json.loads(repo['state'].read_text())
    assert state['last_notified_release_commit']==second
    assert state['last_announcement_message_id']=='1556909999999999999'
    assert len(record['posts'])==1 and record['posts'][0]['enforce_nonce'] is True
    advance(repo)
    cp=run(repo,**env);assert cp.returncode==0,cp.stderr
    assert len(record['posts'])==1


def test_failed_http_keeps_outbox_and_retries(repo,discord_server):
    url,record=discord_server;advance(repo,release=True);record['fail_post']=True
    env={'HERMES_MONITOR_DRY_RUN':'0','HERMES_MONITOR_API_BASE':url}
    cp=run(repo,**env);assert cp.returncode!=0
    state=json.loads(repo['state'].read_text())
    assert state['last_notified_release_commit']==repo['first']
    assert 'pending_announcement' in state
    record['fail_post']=False
    cp=run(repo,**env);assert cp.returncode==0,cp.stderr
    assert 'pending_announcement' not in json.loads(repo['state'].read_text())


def test_post_accepted_get_failed_retries_only_get(repo,discord_server):
    url,record=discord_server;advance(repo,release=True);record['fail_read']=True
    env={'HERMES_MONITOR_DRY_RUN':'0','HERMES_MONITOR_API_BASE':url}
    cp=run(repo,**env);assert cp.returncode!=0
    state=json.loads(repo['state'].read_text())
    assert state['pending_announcement']['message_id']
    assert state['last_notified_release_commit']==repo['first']
    record['fail_read']=False
    cp=run(repo,**env);assert cp.returncode==0,cp.stderr
    assert len(record['posts'])==1


def test_ambiguous_delivery_never_blindly_reposts(tmp_path):
    state={'pending_announcement':{'channel_id':'1','delivery_ambiguous':True,'payload':{'embeds':[{'fields':[]}]}}}
    calls=[]
    def api(token,method,path,body=None):calls.append(method);return []
    with pytest.raises(RuntimeError,match='no blind repost'):
        monitor.deliver(state,tmp_path/'state.json',api=api,token='fixture')
    assert calls==['GET']


def test_current_source_field_aliases_preserve_delta_features_and_fixes():
    msg={'embeds':[{'fields':[{'name':'Atualização estável','value':'Nenhuma'},
        {'name':'Novos no main desde o último alerta','value':'164 commits'},
        {'name':'Top features','value':'inherit auxiliary tasks'},
        {'name':'Top fixes','value':'voice reconnect fix'}]}]}
    text=explain_monitor(msg)
    assert '164 commits' in text and 'inherit auxiliary tasks' in text and 'voice reconnect fix' in text


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_official_release_uses_contextual_generator_in_both_consumers(monkeypatch):
    import subprocess as sp
    from unittest.mock import Mock
    source={'embeds':[{'title':monitor.TITLE,'description':'Official notes about voice reconnect','fields':[]}]}
    response='O que mudou: reconexão de voz corrigida.\n\nImpacto: melhora a continuidade dos canais de voz quando esse recurso é usado.\n\nExige ação: revisar compatibilidade antes de instalar; nenhuma alteração foi aplicada.'
    primary=load('hermes-news-explainer');watchdog=load('hermes-news-explainer-watchdog')
    gen=Mock(return_value=sp.CompletedProcess(['hermes'],0,stdout=response,stderr=''))
    monkeypatch.setattr(primary.subprocess,'run',gen)
    assert primary.explain_announcement(source)==response
    assert watchdog.generate_llm_explanation(source)==response
    assert gen.call_count==2
    assert primary.is_hermes_monitor_alert(source) and watchdog.is_hermes_monitor_alert(source)
    fallback=watchdog.deterministic_fallback(source)
    assert watchdog.is_usable_explanation(fallback)
    assert 'contingência' in fallback
