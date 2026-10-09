"""D1 restart provenance requires both creation and activation evidence."""
import copy
import importlib.util
import pytest


def module():
    spec=importlib.util.spec_from_file_location('cpv_d1_provenance_test','/root/.hermes/profiles/ares/scripts/creditoparaveiculo-fixed-reports.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def evidence():
    config={'campaign_id':'target','source':'rodolfo_explicit_operational_d1_restart',
        'request_id':'restart','cycle_restart_request':'restart','creation_request_id':'creation',
        'creation_readback_audit':'creation-audit','activation_readback_audit':'activation-audit',
        'cycle_start_date':'2026-10-09','authorized_by':'Rodolfo Mattei','authorization_source':'discord:thread:123'}
    creation={'engine_version':3,'request_id':'creation','status':'COMPLETE_PAUSED',
        'result':{'status':'COMPLETE_PAUSED','campaign_ids':['target']}}
    after={'id':'target','account_id':'1046241194533786','configured_status':'ACTIVE',
        'adsets':{'data':[{'configured_status':'ACTIVE'}]},
        'ads':{'data':[{'configured_status':'ACTIVE'} for _ in range(3)]}}
    activation={'request_id':'restart','original_creation_request_id':'creation','status':'COMPLETE_ACTIVATED',
        'account_id':'1046241194533786','cycle_start_date':'2026-10-09','authorized_by':'Rodolfo Mattei',
        'authorization_source':'discord:thread:123','activation_final_readback':{'46':after}}
    return config,creation,activation


def check(monkeypatch,config,creation,activation):
    m=module();monkeypatch.setattr(m,'AUTONOMOUS_WRITE_NUMBERS',{'13'})
    monkeypatch.setattr(m,'_load_provenance_audit',lambda ref:{'creation-audit':creation,'activation-audit':activation}.get(ref))
    op={'management_scope':{'autonomous_action_scope':{'allowed_campaigns':{'13':{'campaign_id':'base'},'46':config}}}}
    return m.validated_allowed_campaigns(op)


def test_verified_paused_creation_followed_by_explicit_d1_activation(monkeypatch):
    cfg,c,a=evidence();assert set(check(monkeypatch,cfg,c,a))=={'13','46'}


@pytest.mark.parametrize('fault',['missing_creation','missing_activation','wrong_id','wrong_date','wrong_authority','paused_child','incomplete_creation'])
def test_restart_fail_closed_on_incomplete_or_mismatched_evidence(monkeypatch,fault):
    cfg,c,a=evidence()
    if fault=='missing_creation':c=None
    elif fault=='missing_activation':a=None
    elif fault=='wrong_id':a['activation_final_readback']['46']['id']='other'
    elif fault=='wrong_date':a['cycle_start_date']='2026-10-08'
    elif fault=='wrong_authority':a['authorized_by']='other'
    elif fault=='paused_child':a['activation_final_readback']['46']['ads']['data'][0]['configured_status']='PAUSED'
    elif fault=='incomplete_creation':c['status']='FAILED'
    with pytest.raises(RuntimeError,match='provenance'):check(monkeypatch,cfg,c,a)
