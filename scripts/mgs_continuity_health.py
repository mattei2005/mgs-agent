"""Read-only health of the common recovery consumer and its durable backlog."""
import json
import os
from pathlib import Path
import sqlite3

DB=Path('/root/.hermes/shared/automation-continuity/queue.sqlite3')


def rows(now,path=DB):
    path=Path(path)
    if not path.exists():return []  # Not enabled/installed yet; no false rollout claim.
    try:
        db=sqlite3.connect(f'file:{path}?mode=ro',uri=True)
        try:
            meta=dict(db.execute('SELECT key,value FROM service'))
            if not json.loads(meta.get('enabled','false')):return []
            heartbeat=json.loads(meta.get('heartbeat','{}'))
            pending=db.execute("SELECT COUNT(*),MIN(created) FROM requests WHERE state NOT IN ('completed_validated','cancelled_owner')").fetchone()
            failures=db.execute("SELECT COUNT(*) FROM requests WHERE state='needs_diagnosis'").fetchone()[0]
        finally:db.close()
    except Exception:return [('service:automation-continuity','ERROR','recovery queue unreadable; no healthy zero inferred')]
    stamp=float(heartbeat.get('at',0));phase=heartbeat.get('phase');pid=heartbeat.get('pid')
    alive=bool(pid and Path('/proc',str(pid)).exists())
    grace=35*60 if phase in ('dispatching','collecting') and alive else 10*60
    if now-stamp>grace:return [('service:automation-continuity','ERROR','common recovery consumer heartbeat overdue; durable requests preserved')]
    result=[('service:automation-continuity','OK',f'consumer phase={phase}; open={pending[0]}; durable queue readable')]
    if int(json.loads(meta.get('worker_failure_streak','0')))>=5:
        result.append(('service:automation-continuity-diagnosis','ERROR','five consecutive worker failures; blind dispatch stopped; requests preserved for Zeus technical diagnosis'))
    if failures:result.append(('service:automation-continuity-diagnosis','ERROR',f'{failures} recovery requests require technical diagnosis; not completed or discarded'))
    return result
