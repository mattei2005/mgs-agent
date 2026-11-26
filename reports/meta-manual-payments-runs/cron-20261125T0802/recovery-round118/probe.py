"""probe_only: same occurrence, GET reconciliation and no-input capture."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round107/probe.py').read_text()
assert code.count('round107') == 2
code = code.replace('round107', 'round118')
# Include native authentication dialogs in the read-only discovery/capture.
old = "capture = capture.replace(old, \"session='recovery-79cd082a-round118-capture'\")"
assert old in code
code = code.replace(old, old + "\ncapture = capture.replace(\"re.search('Save As|Salvar como',w.get('title',''),re.I)\", \"re.search('Save As|Salvar como|Windows Security|Segurança do Windows|passkey',w.get('title',''),re.I)\")")
exec(compile(code, __file__, 'exec'), globals())
