"""Read-only reconciliation of the same supervised occurrence."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round40/probe.py'
code = source.read_text()
old = "or'recovery-ce11800-round40'"
assert code.count(old) == 1
code = code.replace(old, "or'recovery-ce11800-round84'")
print('Read-only predecessor SHA256:', hashlib.sha256(source.read_bytes()).hexdigest(), flush=True)
exec(compile(code, str(Path(__file__)), 'exec'), globals())
