"""Seal actual round-114 reads after inspection via vision_analyze."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round98/seal.py').read_text()
changes = {
    'Seal actual round-98 reads': 'Seal actual round-114 reads',
    "B.parent/'recovery-round97/approved-retry-elements.json'": "B.parent/'recovery-round113/approved-retry-elements.json'",
    "'local_sql_probe_error':'Initial read-only query used nonexistent operation_key column; schema inspected, corrected to key, same request successfully read. No database write.'": "'local_sql_probe_error':None",
    "'dialog_preserved':True": "'dialog_preserved':True,'human_currently_present_not_proven':True,'preservation_required_by_scope_guard':True"
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
exec(compile(code, __file__, 'exec'), globals())
