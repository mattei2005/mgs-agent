"""Reuse the inspected same-operation read-only probe, not financial writes."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round31/probe.py'
code = source.read_bytes()
print('Inspected probe sha256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
