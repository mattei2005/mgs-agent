"""Offline acceptance of the detached OAuth activation contract."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT=Path('/root/mgs-agent/scripts/codex-refresh-deploy-1560643130531774475.py')


@pytest.fixture
def setup(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('activation_fixture',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    (tmp_path/'logs').mkdir()
    config={'activation_order':['atena','ares','zeus'],'finalizers':{}}
    for agent in config['activation_order']:
        file=tmp_path/(agent+'.sh');file.write_text('# synthetic finalizer '+agent)
        config['finalizers'][agent]={'path':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
    path=tmp_path/'config.json';path.write_text(json.dumps(config))
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'CONFIG',path)
    monkeypatch.setattr(module,'STATUS',tmp_path/'status.json')
    monkeypatch.setenv('MGS_CODEX_DEPLOY_CONFIG_SHA',hashlib.sha256(path.read_bytes()).hexdigest())
    events=[];counts={}
    monkeypatch.setattr(module,'transport',lambda:None)
    monkeypatch.setattr(module.time,'sleep',lambda seconds:None)
    monkeypatch.setattr(module,'audit',lambda event,**kw:events.append(('audit',event)))
    monkeypatch.setattr(module,'inventory_status',lambda *a:None)
    monkeypatch.setattr(module,'checkpoint',lambda *a:None)
    monkeypatch.setattr(module,'report',lambda *a:'report-id')
    monkeypatch.setattr(module,'post_verified',lambda *a:'callback-id')
    monkeypatch.setattr(module,'discord_get',lambda path:[{'id':str(int(module.AUTHORIZATION)+1),'author':{'id':'1496296175014252634'},'content':module.HANDOFF}])
    def check_output(args,**kwargs):
        agent=args[2].split('-')[0];counts[agent]=counts.get(agent,0)+1
        return '100' if counts[agent]==1 else '200'
    monkeypatch.setattr(module.subprocess,'check_output',check_output)
    def run(args,**kwargs):
        if args[0]=='/bin/bash':
            events.append(('restart',Path(args[1]).stem));return SimpleNamespace(returncode=0,stdout='',stderr='')
        agent=args[2];events.append(('inference',agent))
        marker='MGS_CODEX_ACTIVATED_'+agent.upper()+'_1560643130531774475_OK'
        return SimpleNamespace(returncode=0,stdout=marker+'\n',stderr='')
    monkeypatch.setattr(module.subprocess,'run',run)
    return module,events,config


def test_actual_handoff_then_sequential_readiness_inference_before_next(setup):
    module,events,_=setup;module.main()
    assert [e for e in events if e[0] in {'restart','inference'}]==[
        ('restart','atena'),('inference','atena'),('restart','ares'),('inference','ares'),('restart','zeus'),('inference','zeus')]
    state=json.loads(module.STATUS.read_text())
    assert state['state']=='active_verified' and state['callback_message_id']=='callback-id'
    assert len(state['agents'])==3


def test_config_drift_aborts_without_any_restart(setup,monkeypatch):
    module,events,_=setup;monkeypatch.setenv('MGS_CODEX_DEPLOY_CONFIG_SHA','wrong')
    with pytest.raises(RuntimeError,match='configuration_freeze_mismatch'):module.main()
    assert not any(e[0]=='restart' for e in events)


def test_finalizer_drift_aborts_without_any_restart(setup):
    module,events,config=setup;Path(config['finalizers']['atena']['path']).write_text('drift')
    with pytest.raises(RuntimeError,match='finalizer_drift_atena'):module.main()
    assert not any(e[0]=='restart' for e in events)


def test_handoff_absence_never_restarts(setup,monkeypatch):
    module,events,_=setup;monkeypatch.setattr(module,'discord_get',lambda path:[])
    clock=iter([0,2000]);monkeypatch.setattr(module.time,'monotonic',lambda:next(clock))
    with pytest.raises(RuntimeError,match='handoff_not_observed'):module.main()
    assert not any(e[0]=='restart' for e in events)


def test_failed_inference_is_retried_once_then_stops_before_ares(setup,monkeypatch):
    module,events,_=setup;original=module.subprocess.run
    def run(args,**kwargs):
        if args[0]=='/bin/bash':return original(args,**kwargs)
        events.append(('inference',args[2]));return SimpleNamespace(returncode=1,stdout='',stderr='synthetic unavailable')
    monkeypatch.setattr(module.subprocess,'run',run)
    with pytest.raises(RuntimeError,match='model_inference_failed_atena'):module.main()
    assert [e for e in events if e[0]=='restart']==[('restart','atena')]
    assert [e for e in events if e[0]=='inference']==[('inference','atena')]*2
