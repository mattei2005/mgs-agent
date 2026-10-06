#!/usr/bin/env python3
"""Import only validated Keitaro day/route aggregate counts; preserve native totals.
Atomic, bounded writer lock, stable source hash and import ledger prevent replay.
"""
import json,sqlite3,time
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

IMPORT_ID='keitaro-history-1556908028450836511'

def import_history(db_path,rows,history,source_sha256,before_commit=None):
    assert len(source_sha256)==64 and all(x in '0123456789abcdef' for x in source_sha256),'invalid_source_sha256'
    assert history['source']=='Keitaro' and history['timezone']=='America/New_York'
    prepared=[];seen=set()
    for row in rows:
        day,key,count=row['day'],row['route_key'],row['clicks']
        assert datetime.strptime(day,'%Y-%m-%d').strftime('%Y-%m-%d')==day
        assert history['from']<=day<=history['to'] and isinstance(count,int) and not isinstance(count,bool) and count>0
        host,path=key.split('\n');assert host and path.startswith('/') and len(key)<=1300
        assert (day,key) not in seen,'duplicate_day_route';seen.add((day,key));prepared.append((day,key,count))
    assert len(prepared)==history['daily_rows'] and sum(x[2] for x in prepared)==history['imported_clicks'] and len({x[1] for x in prepared})==history['campaigns_with_history']
    db=sqlite3.connect(str(db_path),timeout=10,isolation_level=None)
    try:
        db.execute('PRAGMA busy_timeout=10000');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA temp_store=MEMORY')
        since=db.execute("SELECT value FROM click_meta WHERE name='since'").fetchone()[0]
        assert history['to']<datetime.fromisoformat(since).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d'),'historical_daily_rows_overlap_native_day'
        # Prepare rows in a connection-private in-memory table before locking
        # the live writer. No live routing or count writes are blocked here.
        db.execute('CREATE TEMP TABLE staged_history(day TEXT NOT NULL,route_key TEXT NOT NULL,total INTEGER NOT NULL,PRIMARY KEY(day,route_key)) WITHOUT ROWID')
        db.executemany('INSERT INTO staged_history VALUES(?,?,?)',prepared)
        t0=time.perf_counter();db.execute('BEGIN IMMEDIATE')
        try:
            db.execute('CREATE TABLE IF NOT EXISTS click_imports(import_id TEXT PRIMARY KEY,source_sha256 TEXT NOT NULL,total INTEGER NOT NULL,rows INTEGER NOT NULL,metadata TEXT NOT NULL,applied_at TEXT NOT NULL) WITHOUT ROWID')
            existing=db.execute('SELECT source_sha256,total,rows,metadata FROM click_imports WHERE import_id=?',(IMPORT_ID,)).fetchone()
            if existing:
                assert existing[0]==source_sha256 and existing[1]==history['imported_clicks'] and existing[2]==len(prepared) and json.loads(existing[3])==history,'replay_source_changed'
                db.execute('ROLLBACK');return {'status':'already_applied','import_id':IMPORT_ID,'imported_clicks':existing[1],'daily_rows':existing[2],'write_lock_seconds':0}
            assert db.execute('SELECT COUNT(*) FROM click_imports').fetchone()[0]==0,'prior_history_requires_reconciliation'
            assert db.execute("SELECT COUNT(*) FROM click_meta WHERE name='history_keitaro'").fetchone()[0]==0,'orphan_history_metadata'
            assert db.execute('SELECT COUNT(*) FROM click_totals WHERE day<=?',(history['to'],)).fetchone()[0]==0,'preexisting_historical_totals_requires_reconciliation'
            db.execute('INSERT INTO click_totals(day,route_key,total) SELECT day,route_key,total FROM staged_history WHERE 1 ON CONFLICT(day,route_key) DO UPDATE SET total=total+excluded.total')
            metadata=json.dumps(history,ensure_ascii=False,sort_keys=True)
            db.execute('INSERT INTO click_imports VALUES(?,?,?,?,?,?)',(IMPORT_ID,source_sha256,history['imported_clicks'],len(prepared),metadata,datetime.now(timezone.utc).isoformat()))
            db.execute("INSERT INTO click_meta(name,value) VALUES('history_keitaro',?)",(metadata,))
            if before_commit:before_commit(db)
            db.execute('COMMIT')
        except BaseException:
            if db.in_transaction:db.execute('ROLLBACK')
            raise
        lock_seconds=time.perf_counter()-t0
        actual=list(db.execute('SELECT day,route_key,total FROM click_totals WHERE day>=? AND day<=? ORDER BY day,route_key',(history['from'],history['to'])))
        assert actual==sorted(prepared),'historical_exact_readback_failed'
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        return {'status':'applied_exact_readback','import_id':IMPORT_ID,'imported_clicks':history['imported_clicks'],'daily_rows':len(prepared),'write_lock_seconds':lock_seconds,'native_since_preserved':since}
    finally:db.close()
