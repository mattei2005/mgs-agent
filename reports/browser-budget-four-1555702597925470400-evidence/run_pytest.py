import os, sys
from pathlib import Path
# Pure pytest packages from the existing Hermes environment only; append after
# production SB site-packages so SB Playwright/greenlet binaries remain native.
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
p=Path('/root/.hermes/hermes-agent-port-main-ad2d4822-mgs/.venv/lib')
for d in p.glob('python*/site-packages'): sys.path.append(str(d))
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
