"""Seal this round's directly observed resource gate; no queue takeover."""
from pathlib import Path
import hashlib
source = Path(__file__).parent.parent / 'recovery-round6/seal.py'
code = source.read_text()
# The pixels prove an open native dialog, not who originally opened it.
code = code.replace("'cause': 'pc1_human_save_as_dialog_still_open'", "'cause': 'pc1_native_save_as_dialog_still_open'")
code = code.replace("'human_save_as_dialog_open_pixels': True", "'native_save_as_dialog_open_pixels': True, 'dialog_origin_not_established_by_pixels': True")
print('Read-only seal source sha256:', hashlib.sha256(source.read_bytes()).hexdigest(), flush=True)
exec(compile(code, str(source), 'exec'), globals())
