"""Read-only exact occurrence validation after fresh pixel inspection."""
from pathlib import Path
import hashlib,json
base = Path(__file__).parent
visual = json.loads((base/'visual-verification.json').read_text())
assert visual['native_dialog']['open_pixels'] is True
assert visual['approved_surface']['business_id_pixels'] == '155263197283282'
assert visual['approved_surface']['balance_header'] == 'Outstanding balance'
assert visual['approved_surface']['authentication_gate_visible'] is False
source = base.parent / 'recovery-round10/validate_and_seal.py'
code = source.read_bytes()
print('Read-only validator source SHA256:', hashlib.sha256(code).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
