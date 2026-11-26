"""Local evidence: live read-only validation of the same occurrence."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round40/validate_and_seal.py'
print('Read-only validator SHA256:', hashlib.sha256(source.read_bytes()).hexdigest(), flush=True)
exec(compile(source.read_text(), str(Path(__file__)), 'exec'), globals())
