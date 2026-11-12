"""Lexically scoped schema admission of the exact sealed target, never a writer."""
from contextlib import contextmanager
from contextvars import ContextVar
from . import shein_elapsed_continuation as effective

_CURRENT = ContextVar('shein_effective_elapsed_schema', default=None)


@contextmanager
def admission(value):
    accepted = None
    try:
        rid = value.get('request_id'); campaigns = value.get('campaigns') or []
        if value.get('operation') == 'SHEIN-US-DIRECT' and campaigns and campaigns[0].get('status') == 'ACTIVE':
            aid = campaigns[0]['account_id']
            state, _, _, _, _, _, rp = effective.load(effective.BASE, rid, aid)
            import json
            receipt = json.loads(rp.read_text())
            slot = receipt['binding']['slots'][0]
            if value == state['target_manifest'] and effective.proof(
                    slot['expected_start_time'], slot['observed_start_time'],
                    request_id=rid, account_id=aid, campaign_id=slot['campaign_id'],
                    idempotency_key=slot['idempotency_key']):
                accepted = value['campaigns']
    except (OSError, KeyError, ValueError, TypeError, IndexError):
        pass
    token = _CURRENT.set(accepted)
    try:
        yield
    finally:
        _CURRENT.reset(token)


def allows_campaign(value):
    candidates = _CURRENT.get()
    return candidates is not None and value in candidates
