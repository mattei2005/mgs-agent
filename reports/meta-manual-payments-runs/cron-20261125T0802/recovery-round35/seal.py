"""Seal fresh diagnostic evidence after visual inspection, no business write."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round33/seal.py'
code = source.read_bytes()
print('Inspected diagnostic seal sha256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
