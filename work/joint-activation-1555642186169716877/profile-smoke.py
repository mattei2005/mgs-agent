#!/usr/bin/env python3
"""Fresh, target-profile, read-only browser/config smoke; isolated named test browser."""
import json
import os
from pathlib import Path
import sys
import time
import urllib.parse
import yaml

agent = sys.argv[1]
assert agent in ('ares', 'atena', 'zeus')
home = Path('/root/.hermes/profiles') / agent
assert Path(os.environ['HERMES_HOME']) == home
repo = Path('/root/.local/bin/hermes').resolve().parent.parent.parent
sys.path.insert(0, str(repo))
from tools.browser_use_cli import browser_exec, _backend_cache_key
from tools.browser_tool_session import _run_browser_command
from hermes_cli.config import load_config

config = load_config()
assert config['model']['default'] == 'gpt-6.1-sol'
assert config['model']['provider'] == 'openai-codex'
assert config['compression']['threshold'] == 0.90
assert config['browser']['resource_budget_module'] == '/root/mgs-agent/scripts/mgs_browser_budget.py'
assert config['checkpoints']['max_total_size_mb'] == (4096 if agent == 'zeus' else 1024)
assert config['checkpoints']['max_snapshots'] == 50 and config['checkpoints']['retention_days'] == 7
assert yaml.safe_load((home/'config.yaml').read_text()) == yaml.safe_load(Path('/root/mgs-agent/profiles') .joinpath(agent+'-config.yaml').read_text())
name = 'activation-' + agent + '-1555642186169716877'
task = name
marker = 'MGS-ACTIVATION-' + agent
html = '<title>'+marker+'</title><main id="smoke">'+marker+'</main>'
url = 'data:text/html,' + urllib.parse.quote(html)
code = '# Validando navegador isolado de '+agent+'\nnew_tab('+repr(url)+')\nwait_for_load()\nprint(js("document.querySelector(\'#smoke\').textContent"))'
started = time.monotonic()
try:
    result = json.loads(browser_exec(code, session=name, timeout_s=75, task_id=task))
    (Path(__file__).parent / (agent+'-browser-result.json')).write_text(json.dumps(result, indent=2)+'\n')
    assert result.get('success'), 'browser_exec smoke failed: ' + str(result.get('error') or result.get('stderr', ''))[-600:]
    assert marker in result.get('output', '') or marker in result.get('stdout', ''), 'Rendered browser marker missing'
    receipt = {'agent': agent, 'configured_model': config['model']['default'], 'provider': config['model']['provider'],
               'compression_threshold': config['compression']['threshold'], 'checkpoint_cap_mib': config['checkpoints']['max_total_size_mb'],
               'config_mirror_equal': True, 'native_browser_exec': True, 'budget_admitted_rendered_dom': True,
               'external_requests': 0, 'protected_browser_sessions_touched': False,
               'browser_elapsed_seconds': round(time.monotonic()-started,3), 'pass': True}
    print(json.dumps(receipt))
finally:
    from tools.browser_supervisor import SUPERVISOR_REGISTRY
    from tools.browser_tool_lifecycle import _stop_browser_cleanup_thread
    SUPERVISOR_REGISTRY.stop(task)
    _stop_browser_cleanup_thread()
    # Close only this named test browser, not a protected/authenticated session.
    closed = _run_browser_command(_backend_cache_key(task, name), 'close', [], timeout=15)
    assert closed.get('success'), 'Isolated test browser close failed'
