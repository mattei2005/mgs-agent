"""Reconcile same authorized operation; read-only PC1, no input."""
import sys, shutil, importlib.util, json, os
from pathlib import Path
B = Path(__file__).parent
B.chmod(0o700)
ROOT = Path('/root/mgs-agent')
launcher = shutil.which('hermes')
assert launcher is not None
R = Path(launcher).resolve().parents[2]
sys.path.insert(0, str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
spec = importlib.util.spec_from_file_location('authority_resolver', ROOT / 'scripts/alerts-infra-failed-alert-resolver.py')
assert spec is not None and spec.loader is not None
authority = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = authority
spec.loader.exec_module(authority)
status, context = authority.discord_api(authority.load_token(), 'GET', '/channels/1563926766286803004/messages/1563960022252392459')
assert status == 200 and context['id'] == '1563960022252392459'
assert context['channel_id'] == '1563926766286803004' and context['author']['id'] == '1496296175014252634'
context_path = B / 'original-command-context.json'
assert not context_path.exists()
context_path.write_text(json.dumps({'status': status, 'id': context['id'], 'channel_id': context['channel_id'], 'author_id': context['author']['id'], 'content': context['content']}, ensure_ascii=False, indent=2))
context_path.chmod(0o600)
os.environ['MGS_CONTINUITY_OPERATION_KEY'] = '79cd082a20c22a736307765f'
source = B.parent / 'recovery-round17/probe.py'
exec(compile(source.read_text(), str(source), 'exec'), globals())
