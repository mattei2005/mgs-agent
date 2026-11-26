"""Seal inspected round-103 evidence; no business or queue mutation."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round98/seal.py').read_text()
changes = {
    'Seal actual round-98 reads': 'Seal actual round-103 reads',
    "B.parent/'recovery-round97/approved-retry-elements.json'": "B.parent/'recovery-round102/approved-retry-elements.json'",
    "'local_sql_probe_error':'Initial read-only query used nonexistent operation_key column; schema inspected, corrected to key, same request successfully read. No database write.'": "'local_sql_probe_error':'Initial local read-only query referenced nonexistent operations table. Schema inspected; corrected query against requests succeeded. No database write.'"
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
exec(compile(code, __file__, 'exec'), globals())
