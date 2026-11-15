"""Eggbev01 operator suspension: local coordination only, never campaign QA.

The exact receipt fences the archived request even after a new writer replaces
its lease. Receipt corruption denies replay and keeps readers blocked.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path

ACCOUNT='1034081997659047'
REQUEST='eggbev-pg23187-1570285402068091011'
STATUS='SUSPENDED_BY_OPERATOR'

def path(root,account,request):
    if re.fullmatch(r'[A-Za-z0-9_.-]{8,120}',str(request)) is None or not str(account).isdigit():
        raise ValueError('invalid operator suspension identity')
    return Path(root)/'operator-suspensions'/f'{request}-{account}.json'

def deny_replay(root,account,request):
    if path(root,account,request).exists():
        raise ValueError('operator suspended historical request; automatic replay forbidden')

def validate(root,account,request):
    p=path(root,account,request);v=json.loads(p.read_text())
    if (str(account)!=ACCOUNT or request!=REQUEST or v.get('account_id')!=ACCOUNT
            or v.get('request_id')!=REQUEST or v.get('status')!=STATUS
            or v.get('authority_message_ids')!=['1570338387380936737','1570343663307989043']
            or v.get('campaign_qa_complete') is not False or v.get('meta_writes')!=0
            or v.get('reservation_release') is not False or not v.get('recorded_at')
            or len(v.get('record_pins',{}))<3):
        raise ValueError('operator suspension receipt invalid')
    for filename,digest in v['record_pins'].items():
        target=Path(root)/filename
        if Path(filename).is_absolute() or '..' in Path(filename).parts or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
            raise ValueError('operator suspension historical evidence changed')
    return v

def lease_valid(root,lease):
    try:
        rec=validate(root,lease['account_id'],lease['request_id'])
        return (lease.get('blocks_readers') is False and bool(lease.get('released_at_utc'))
                and lease.get('status')==STATUS and lease.get('campaign_qa_complete') is False
                and lease.get('operator_suspension_sha256')==hashlib.sha256(path(root,rec['account_id'],rec['request_id']).read_bytes()).hexdigest())
    except (KeyError,OSError,ValueError,TypeError):
        return False
