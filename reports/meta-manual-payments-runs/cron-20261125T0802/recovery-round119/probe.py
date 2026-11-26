"""Same-occurrence probe_only: reuse inspected read-only reconciliation/capture."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round118/probe.py').read_text()
assert 'round118' in code
code = code.replace('round118', 'round119')
exec(compile(code, __file__, 'exec'), globals())
