"""Seal round 106 after actual pixel inspection; no business or queue writes."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round98/seal.py').read_text()
changes = {
    'Seal actual round-98 reads': 'Seal actual round-106 reads',
    "B.parent/'recovery-round97/approved-retry-elements.json'": "B.parent/'recovery-round105/approved-retry-elements.json'",
    "'local_sql_probe_error':'Initial read-only query used nonexistent operation_key column; schema inspected, corrected to key, same request successfully read. No database write.'": "'local_sql_probe_error':'Initial read-only schema discovery queried nonexistent operations table; inspected actual requests schema and successfully read exact key. No database write.'"
}
for old, new in changes.items():
    assert code.count(old) == 1, old
    code = code.replace(old, new)
exec(compile(code, __file__, 'exec'), globals())
