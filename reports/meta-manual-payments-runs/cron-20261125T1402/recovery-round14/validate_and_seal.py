"""Read-only same-occurrence validation after actual fresh pixel inspection."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round10/validate_and_seal.py'
code = source.read_bytes()
print('Validator source SHA256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
