"""Bounded GAM recovery. Never infer rollback from a transport error."""
from __future__ import annotations
import imaplib
import subprocess
import time

class RecoveryBlocked(RuntimeError):
    def __init__(self, disposition, cause):
        self.disposition = disposition
        super().__init__(f"GAM recovery blocked: {disposition}; {type(cause).__name__}")

def failure_fields(streak):
    return {"failure_streak": streak, "intervention_required": True, "blocked_after_five": streak >= 5}

def transient(exc):
    # Deny authority/auth/billing/invariant errors before classifying transport failures.
    text = str(exc).lower()
    if any(x in text for x in ('permission denied','authentication','credential','1password','billing','quota','unauthorized','forbidden','invalid token','hash mismatch','assertion')):
        return False
    return isinstance(exc, (TimeoutError, ConnectionError, subprocess.TimeoutExpired, imaplib.IMAP4.abort)) or any(x in text for x in ('connection reset','connection timed out','connection closed','broken pipe'))

def retry_read(operation, step, journal, sleep=time.sleep):
    """At most one retry of a read-only operation; no secret/credential repair."""
    try:
        return operation()
    except Exception as exc:
        journal({"step": step, "error": type(exc).__name__, "retryable": transient(exc), "intervention_required": True})
        if not transient(exc):
            raise
        sleep(1)
        return operation()

def guarded_import(remote, plan, journal, sleep=time.sleep):
    """Caller holds quote/import locks and already validated rehearsal + backup.

    After *any* uncertain apply/verify, inspect the exact plan's current scenario,
    source bundle and audit. Only proven absence + a transient failure permits one
    idempotent retry. A committed operation resumes with reads only.
    """
    recovered = False
    for attempt in range(2):
        step = 'production_apply'
        try:
            applied = remote('apply', plan)
            if applied.get('pass') is not True:
                raise RuntimeError('apply confirmation absent')
            step = 'production_verify'
            verified = remote('verify', plan)
            if verified.get('pass') is not True:
                raise RuntimeError('verification confirmation absent')
            return {"apply": applied, "verify": verified, "recovered": recovered}
        except Exception as exc:
            recovered = True
            journal({"step": step, "error": type(exc).__name__, "attempt": attempt + 1, "intervention_required": True, "write_outcome": "unconfirmed"})
            try:
                state = retry_read(lambda: remote('inspect', plan), 'recovery_readback', journal, sleep)
            except Exception as inspection:
                raise RecoveryBlocked('unknown', inspection) from exc
            disposition = state.get('disposition', 'unknown')
            journal({"step": "recovery_readback", "disposition": disposition, "revision": state.get('revision'), "audit_id": state.get('verify', {}).get('audit_id')})
            if state.get('pass') is True and disposition == 'applied' and state.get('verify', {}).get('pass') is True:
                return {"apply": {"pass": True, "already_applied": True, "recovered_by_readback": True}, "verify": state['verify'], "recovered": True}
            if state.get('pass') is True and disposition == 'not_applied' and transient(exc) and attempt == 0:
                sleep(1)
                continue
            raise RecoveryBlocked(disposition, exc) from exc
    raise AssertionError('unreachable bounded recovery state')
