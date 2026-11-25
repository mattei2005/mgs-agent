"""Reconcile the same authorized occurrence; capture only, no UI input."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round1/probe.py'
code = source.read_bytes()
print('Read-only probe source SHA256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
