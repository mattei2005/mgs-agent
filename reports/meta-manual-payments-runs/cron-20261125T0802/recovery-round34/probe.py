"""Run inspected same-operation reconciliation and read-only captures."""
from pathlib import Path
import hashlib
import os
os.umask(0o077)
os.environ['HERMES_SESSION_ID'] = 'recovery-79cd082a-round34'
source = Path(__file__).parent.parent / 'recovery-round31/probe.py'
code = source.read_bytes()
print('Inspected probe sha256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
