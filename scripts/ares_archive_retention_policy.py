#!/usr/bin/env python3
"""Activate the explicitly confirmed 0s retention; no deletion or scope expansion here."""
from __future__ import annotations
import argparse,fcntl,json,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import ares_archive_retirement as r
CONFIRMATION='1562848227944955935'
QUESTION_REQUEST='1562835794601975811'
BACKUP=Path('/root/.hermes/profiles/zeus/artifacts/immediate-retention-'+CONFIRMATION)

def prepare():
    old=r.authorization(r.CONFIRMATION)
    auth=copy.deepcopy(old)
    auth.update(confirmation_message_id=CONFIRMATION,confirmation_text='sim',confirmation_context_message_id=QUESTION_REQUEST,confirmation_question='Confirma substituir as24horas por exclusao automatica da origem assim que copia, integridade, acessos e funcionamento pelo destino estiverem comprovados, preservando30TB e uploads pendentes/em processamento?',supersedes_confirmation_message_id=r.CONFIRMATION,retention_seconds=0,all_integrity_access_consumer_gates_preserved=True,registered_at=b.now_iso(),rollback_snapshot=str(BACKUP),context='Explicit additional confirmation by Rodolfo after the 24h→0s permanent-source-deletion question. Removes the waiting period only; does not bypass proof, consumer, lineage, active-writer or history gates. Existing new-lineage controller remains bounded; historical legacy cleanup awaits its verified consumer contract.')
    proposal_path=b.DATA/'processed-immediate-retirement-proposal-1562835794601975811.json'
    auth['previous_proposal_sha256']=old.get('proposal_sha256')
    auth['proposal_source']=str(proposal_path.relative_to(b.BASE))
    auth['proposal_sha256']=r.digest(b.read_json(proposal_path,{}))
    path=b.DATA/('retirement-authorization-'+CONFIRMATION+'.json')
    if path.exists():
        existing=b.read_json(path)
        comparable=lambda value:{k:v for k,v in value.items() if k!='registered_at'}
        if comparable(existing)!=comparable(auth):raise r.RetirementError('IMMEDIATE_AUTHORIZATION_IMMUTABLE_CONFLICT')
        auth=existing
    else:b.atomic_json(path,auth)
    if r.authorization(CONFIRMATION)!=auth:raise r.RetirementError('IMMEDIATE_AUTHORIZATION_READBACK')
    return auth

def activate():
    auth=prepare()
    with (b.DATA/'.intake-state.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        with b.queue_lock():
            c=b.config_load()
            if c.get('source_cleanup_confirmation_message_id')==CONFIRMATION:
                r.validate_active_policy(c)
                return {'status':'already_active','confirmation_message_id':CONFIRMATION,'retention_seconds':0,'new_deletions_performed_by_activation':0,'historical_cleanup_enabled':False}
            if c.get('source_cleanup_confirmation_message_id')!=r.CONFIRMATION:raise r.RetirementError('IMMEDIATE_UNEXPECTED_ACTIVE_POLICY')
            for path in (b.DATA/'retirements').glob('source-*.json'):
                intent=b.read_json(path,{})
                if intent.get('phase') not in ['complete']:raise r.RetirementError('IMMEDIATE_PRIOR_INTENT_REQUIRES_RECONCILIATION')
            if not (BACKUP/'queue-config.json').exists():raise r.RetirementError('IMMEDIATE_ROLLBACK_REQUIRED')
            new={**c,'source_cleanup_confirmation_message_id':CONFIRMATION,'source_cleanup_authorization_sha256':r.digest(auth),'source_cleanup_retention_seconds':0,'status':'autonomous_archive_and_verified_immediate_retirement_active'}
            r.validate_active_policy(new)
            b.atomic_json(b.CONFIG,new)
            if b.config_load()!=new or r.authorization()!=auth:raise r.RetirementError('IMMEDIATE_ACTIVATION_READBACK')
            with (b.BASE/'logs/events-audit.jsonl').open('a') as f:
                fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'at':b.now_iso(),'actor':'zeus','action':'verified_source_retention_24h_to_0s_activated','confirmation_message_id':CONFIRMATION,'supersedes_confirmation_message_id':r.CONFIRMATION,'authorization_sha256':r.digest(auth),'retention_before_seconds':86400,'retention_after_seconds':0,'proof_gates_preserved':True,'max_pairs_per_run':2,'historical_controller_scope_unchanged':True,'new_deletions_by_activation':0})+'\n')
            return {'status':'active','confirmation_message_id':CONFIRMATION,'retention_seconds':0,'max_pairs_per_run':2,'new_deletions_performed_by_activation':0,'historical_cleanup_enabled':False,'authorization_sha256':r.digest(auth)}

def verify():
    c=b.config_load();auth=r.validate_active_policy(c)
    return {'status':'active' if auth['confirmation_message_id']==CONFIRMATION else 'legacy_active','confirmation_message_id':auth['confirmation_message_id'],'retention_seconds':auth['retention_seconds'],'max_pairs_per_run':auth['max_pairs_per_run'],'delete_source':c['delete_source'],'include_historical':c['include_historical']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','activate','verify']);args=parser.parse_args()
    print(json.dumps({'prepare':prepare,'activate':activate,'verify':verify}[args.action](),ensure_ascii=False))
