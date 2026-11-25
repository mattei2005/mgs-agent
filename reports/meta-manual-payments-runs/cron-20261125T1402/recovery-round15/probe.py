"""Read-only probe of the same occurrence; no desktop input."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round10/probe.py'
code = source.read_bytes()
print('Read-only probe source SHA256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
