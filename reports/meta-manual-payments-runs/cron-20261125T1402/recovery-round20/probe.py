"""Same authorized occurrence: current authority and no-input reconciliation."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round10/probe.py'
code = source.read_bytes()
print('Read-only probe SHA256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
