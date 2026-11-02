"""MGS sb-venv: select the security-maintained system Node for Playwright.

Installed as sb-venv's sitecustomize.py. This uses Playwright's supported
PLAYWRIGHT_NODEJS_PATH switch; browser binaries, profiles and package files
remain unchanged. Scope: this exact virtualenv, never the Hermes runtimes.
Authorization: Rodolfo Mattei, Discord message 1566812251250229279.
"""
import os as _mgs_os
import sys as _mgs_sys

if _mgs_os.path.realpath(_mgs_sys.prefix) == "/root/.local/share/mgs/sb-venv":
    _mgs_node = "/usr/bin/node"
    if not _mgs_os.path.isfile(_mgs_node) or not _mgs_os.access(_mgs_node, _mgs_os.X_OK):
        raise SystemExit("MGS sb-venv: approved system Node is unavailable; refusing embedded-driver fallback")
    _mgs_os.environ["PLAYWRIGHT_NODEJS_PATH"] = _mgs_node
