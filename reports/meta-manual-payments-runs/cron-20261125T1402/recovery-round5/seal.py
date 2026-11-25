"""Seal fresh observed occupancy; supervisor retains transition ownership."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round3/seal.py'
code = source.read_bytes()
print('Evidence sealing source sha256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
