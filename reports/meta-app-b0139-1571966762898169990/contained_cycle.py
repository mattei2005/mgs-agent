import asyncio
import fcntl
import json
import sys
from pathlib import Path
from cutover_support import namespace, save

ROOT = Path(__file__).parent
name = sys.argv[1]
lock = open('/var/lock/b013-dtr-link-watch.lock', 'a+')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
ns = namespace()
ns['DRY_RUN'] = False
ns['FORCE_LIVE_ALERT'] = False
ns['STATE_PATH'] = Path('/root/mgs-agent/data/b013-dtr-link-monitor-state.json')
config = ns['load_config']()
assert config['app_name'] == 'B013-9' and config['app_id'] == '2030252157625027'
rows = ns['sheet_rows'](config)
assert rows and all(str(r.get('pages') or '').isdigit() and len(str(r.get('pages') or '')) <= 5 for r in rows)
posts = []
def contain(config, content='', embed=None, **kwargs):
    posts.append({'channel_id': config['alert_channel_id'], 'embed_title': (embed or {}).get('title'), 'content_present': bool(content)})
    return None
ns['post_discord'] = contain
started = ns['now_iso']()
asyncio.run(ns['main']())
state = json.loads(ns['STATE_PATH'].read_text())
receipt = {'started_at': started, 'completed_at': ns['now_iso'](), 'app_id': state['app_id'], 'state_updated_at': state['_updated_at'], 'accounts': len(state['accounts']), 'summary': state['_last_run_summary'], 'notification_containment': True, 'contained_posts': posts}
save(name + '.json', receipt)
assert state['app_id'] == config['app_id']
assert state['app_capability']['status'] == 'healthy'
assert 'error' not in state['_last_run_summary']['sheet_sync']
assert state['_last_run_summary']['targets'] > 0
print(json.dumps(receipt, ensure_ascii=False))
