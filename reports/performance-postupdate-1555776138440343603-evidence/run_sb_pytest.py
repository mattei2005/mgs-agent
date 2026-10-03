import os,sys
from pathlib import Path
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
launcher=Path('/root/.local/bin/hermes').resolve()
for p in (launcher.parent.parent/'lib').glob('python*/site-packages'):sys.path.append(str(p))
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
