"""Read-only reconciliation and no-input captures for the same occurrence."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round1/probe.py'
code = source.read_bytes()
print('Reused read-only probe sha256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
