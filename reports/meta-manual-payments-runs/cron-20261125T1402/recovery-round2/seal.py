"""Seal this round after direct inspection of its two fresh captures."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round1/seal.py'
code = source.read_bytes()
print('Evidence sealer source sha256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
