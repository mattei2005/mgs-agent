"""Validate explicit profiles with no toolsets and no restarts."""
import os, pathlib, subprocess, json, time, concurrent.futures, re
OUT = pathlib.Path(__file__).parent
SEC = pathlib.Path('/root/.hermes/secure-backups/capture-retirement-1571691667516424224')
os.umask(0o077)
SEC.mkdir(mode=0o700, exist_ok=False)
MARK = 'MGS_CLEANUP_SMOKE_OK'
def check(profile):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env.pop('HERMES_HOME', None)
    env.pop('HERMES_PROFILE', None)
    start = time.monotonic()
    config = subprocess.run(['/root/.local/bin/hermes', '-p', profile, 'config', 'check'], capture_output=True, text=True, timeout=60, env=env)
    (SEC / ('config-' + profile + '.log')).write_text(config.stdout + '\n' + config.stderr)
    if config.returncode != 0:
        return dict(profile=profile, config_returncode=config.returncode, smoke_executed=False, status='FAIL')
    cmd = ['/root/.local/bin/hermes', '-p', profile, 'chat', '--oneshot', '-Q', '-t', '', '--max-turns', '1', '--run-budget', '60', '-q', 'Reply only MGS_CLEANUP_SMOKE_OK. Do not use tools or modify files.']
    try:
        smoke = subprocess.run(cmd, capture_output=True, text=True, timeout=100, env=env)
    except subprocess.TimeoutExpired:
        return dict(profile=profile, config_returncode=config.returncode, smoke_executed=True, status='FAIL', reason='bounded_cli_timeout')
    (SEC / ('smoke-' + profile + '.log')).write_text(smoke.stdout + '\n' + smoke.stderr)
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', smoke.stdout).strip()
    final = text.splitlines()[-1].strip() if text else ''
    passed = smoke.returncode == 0 and final == MARK
    return dict(profile=profile, config_returncode=config.returncode, smoke_returncode=smoke.returncode, toolsets_disabled=True, exact_final_line_matches_marker=final == MARK, elapsed_seconds=round(time.monotonic()-start, 2), status='PASS' if passed else 'FAIL')
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(check, ['zeus', 'ares', 'atena']))
receipt = dict(status='PASS' if all(x['status'] == 'PASS' for x in results) else 'FAIL', results=results, configs_passed=sum(x.get('config_returncode') == 0 for x in results), smokes_passed=sum(x['status'] == 'PASS' for x in results), explicit_profiles=True, proves='Current profile/provider text availability only; not historical environment or full production restore')
(OUT / 'post-availability.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
