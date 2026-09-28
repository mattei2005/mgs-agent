"""Admission barrier only: shared jobs, exclusive short release, crash recovery.
Never edits financial data or changes the schedule. Import before business modules.
"""
from __future__ import annotations
import contextlib, datetime, fcntl, json, os, pathlib, time

_HELD = []
_TRIGGER = None
SAFE_STATES = {'committed', 'rolled_back', 'prepared'}


def release_state(root):
    p = pathlib.Path(root)/'private/release-current.json'
    return json.loads(p.read_text()) if p.exists() else None


@contextlib.contextmanager
def lease(root, *, exclusive=False, timeout=None, recover_pending=True):
    root = pathlib.Path(root)
    folder = root/'private'; folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = (folder/'release-admission.lock').open('a')
    start = time.monotonic()
    try:
        while True:
            try:
                fcntl.flock(handle, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if timeout is not None and time.monotonic()-start >= timeout:
                    raise TimeoutError('finance_release_admission_busy_no_changes')
                time.sleep(.05)
        state = release_state(root)
        if not exclusive and recover_pending and state and state.get('state') not in SAFE_STATES:
            # Never upgrade a held shared lock: another reader could deadlock us.
            fcntl.flock(handle, fcntl.LOCK_UN)
            from finance_release import recover
            recover(root)
            fcntl.flock(handle, fcntl.LOCK_SH)
            state = release_state(root)
            if state and state.get('state') not in SAFE_STATES:
                raise RuntimeError('finance_release_recovery_blocked')
        yield handle
    finally:
        handle.close()


def admit_entrypoint(root):
    """Retain the admission fd until process exit, before business imports."""
    global _TRIGGER
    _TRIGGER = datetime.datetime.now(datetime.timezone.utc)
    cm = lease(root)
    cm.__enter__()
    _HELD.append(cm)


def trigger_time(now):
    """The approved cron slot remains the dispatch slot even after a short wait."""
    return _TRIGGER.astimezone(now.tzinfo) if _TRIGGER is not None else now
