"""Reconcile same authorized occurrence and capture PC1 with no inputs."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round107/probe.py').read_text()
assert code.count('round107') == 2
code = code.replace('round107', 'round110')
exec(compile(code, __file__, 'exec'), globals())
