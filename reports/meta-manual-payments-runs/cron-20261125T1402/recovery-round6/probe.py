"""Reconcile the same occurrence and capture exact PC1 surface, no input."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round1/probe.py'
code = source.read_bytes()
print('Read-only probe source sha256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
