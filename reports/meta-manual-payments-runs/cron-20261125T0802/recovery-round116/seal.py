"""Seal fresh round-116 reads after actual vision_analyze inspection."""
from pathlib import Path
base = Path(__file__).parent.parent
code = (base / 'recovery-round115/seal.py').read_text()
code = code.replace('round-115', 'round-116').replace('recovery-round114/', 'recovery-round115/')
exec(compile(code, __file__, 'exec'), globals())
