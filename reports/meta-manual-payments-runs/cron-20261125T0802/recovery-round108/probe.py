"""Read-only same-occurrence reconciliation and fresh no-input PC1 capture."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round107/probe.py').read_text()
assert code.count('round107') == 2
code = code.replace('round107', 'round108')
exec(compile(code, __file__, 'exec'), globals())
