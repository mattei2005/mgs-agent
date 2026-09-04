#!/usr/bin/env python3
import fcntl, json, os
from datetime import datetime, timezone
from pathlib import Path
path=Path('/root/mgs-agent/logs/events-audit.jsonl')
record={
 'ts':datetime.now(timezone.utc).isoformat(),
 'agent':'zeus',
 'event':'report_infra_sent_validated',
 'related_event':'finance_caixa_august_j59_j75_completed',
 'artifact_id':'zeus-finance-caixa-j59-j75-20260904',
 'channel_id':'1498132022634483894',
 'message_id':'1545556291521355817',
 'http_status':200,
 'content_empty':True,
 'embed_count':1,
 'mentions':0,
 'thread_created':False,
 'source_thread_id':'1545426987756298340',
 'verification_sha256':'6db929e79fa559b6785f5c0908411d315a2fb72c9b828f3a015a70e5badaeb98'
}
with path.open('a',encoding='utf-8') as h:
 fcntl.flock(h.fileno(),fcntl.LOCK_EX)
 h.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n'); h.flush(); os.fsync(h.fileno())
 fcntl.flock(h.fileno(),fcntl.LOCK_UN)
print(json.dumps({'status':'pass','event':record['event'],'message_id':record['message_id']},separators=(',',':')))
