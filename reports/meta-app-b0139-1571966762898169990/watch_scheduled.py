import datetime
import json
import time
from pathlib import Path

ROOT = Path(__file__).parent
cutoff = datetime.datetime.fromisoformat(json.loads((ROOT / 'reactivation.json').read_text())['jobs_file_updated_at'])
state_path = Path('/root/mgs-agent/data/b013-dtr-link-monitor-state.json')
jobs_path = Path('/root/.hermes/profiles/zeus/cron/jobs.json')
deadline = time.monotonic() + 1800
while time.monotonic() < deadline:
    state = json.loads(state_path.read_text())
    jobs = json.loads(jobs_path.read_text())['jobs']
    job = next(x for x in jobs if x.get('id') == '498fb0d95e10')
    accounts = list(state.get('accounts', {}).values())
    fresh = accounts and all(datetime.datetime.fromisoformat(x['checked_at']) > cutoff for x in accounts)
    run_after = job.get('last_run_at') and datetime.datetime.fromisoformat(job['last_run_at']) > cutoff
    if state.get('app_id') == '2030252157625027' and fresh and run_after:
        summary = state['_last_run_summary']
        assert summary['targets'] == len(accounts)
        assert summary['app_capability']['status'] == 'healthy'
        assert 'error' not in summary['sheet_sync']
        receipt = {'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'reactivation_cutoff': cutoff.isoformat(), 'state_updated_at': state['_updated_at'], 'earliest_account_checked_at': min(x['checked_at'] for x in accounts), 'latest_account_checked_at': max(x['checked_at'] for x in accounts), 'accounts': len(accounts), 'job_last_run_at': job['last_run_at'], 'job_last_status': job['last_status'], 'summary': summary}
        (ROOT / 'scheduled-readback.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(receipt, ensure_ascii=False))
        raise SystemExit(0)
    time.sleep(15)
raise SystemExit('No fresh complete scheduled cycle within bounded window; preserve checkpoint and reconcile native lock.')
