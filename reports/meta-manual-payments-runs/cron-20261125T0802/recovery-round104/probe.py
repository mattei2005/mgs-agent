"""Reconcile the same authorized occurrence; read-only PC1 probe."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round100/probe.py').read_text()
assert code.count('round100') == 2
code = code.replace('round100', 'round104')
exec(compile(code, __file__, 'exec'), globals())
