"""Same occurrence, read-only live validation after fresh pixel review."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round10/validate_and_seal.py'
code = source.read_bytes()
print('Read-only validator source SHA256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
