"""Same authorized occurrence: inspected read-only reconciliation/probe."""
from pathlib import Path
import os
import hashlib
os.umask(0o077)
os.environ['HERMES_SESSION_ID'] = 'recovery-79cd082a-round35'
source = Path(__file__).parent.parent / 'recovery-round31/probe.py'
code = source.read_bytes()
print('Inspected read-only probe sha256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
