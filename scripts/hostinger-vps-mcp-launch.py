#!/usr/bin/env python3
"""Start the Hostinger VPS read-only MCP with 1Password-only credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys

POLICY = Path('/root/mgs-agent/data/hostinger-vps-zeus.json')
OP_WRAPPER = '/root/mgs-agent/scripts/mgs-op-with-service-account.sh'


def main():
    if len(sys.argv) != 1:
        raise RuntimeError('This launcher accepts no arguments')
    policy = json.loads(POLICY.read_text())
    root = Path(policy['install_dir'])
    package = root / 'node_modules/hostinger-api-mcp/package.json'
    if json.loads(package.read_text())['version'] != policy['package_version']:
        raise RuntimeError('Pinned Hostinger package version mismatch')
    ref = policy['credential']
    result = subprocess.run(
        [OP_WRAPPER, 'read', f"op://{ref['vault_id']}/{ref['item_id']}/{ref['field_id']}"],
        text=True, capture_output=True, timeout=45,
    )
    if result.returncode:
        raise RuntimeError('Hostinger credential unavailable in canonical 1Password service account')
    token = result.stdout.strip()
    if len(token) < 10 or any(c in token for c in ['\r', '\n']):
        raise RuntimeError('Hostinger credential empty or malformed')
    # Do not leak other providers' keys or the bootstrap service-account token.
    env = {key: os.environ[key] for key in ['HOME', 'PATH', 'LANG', 'LC_ALL', 'TMPDIR'] if key in os.environ}
    env.update(HOSTINGER_API_TOKEN=token, API_BASE_URL=policy['api_base_url'], DEBUG='false')
    os.chdir(root)
    os.execve('/usr/bin/node', ['/usr/bin/node', '/root/mgs-agent/scripts/hostinger-vps-mcp-readonly.mjs'], env)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Hostinger VPS launcher failed: {type(exc).__name__}', file=sys.stderr)
        raise SystemExit(1)
