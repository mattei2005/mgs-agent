"""Seal this round only after actual pixel inspection; no business mutation."""
from pathlib import Path
source = Path(__file__).parent.parent / 'recovery-round75/seal.py'
code = source.read_text()
old = "'recovery-round74/approved-elements.json'"
assert code.count(old) == 1
code = code.replace(old, "'recovery-round75/approved-elements.json'")
exec(compile(code, str(Path(__file__)), 'exec'), globals())
