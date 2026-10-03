"""Official stable-release metadata, never inferred from nearest git tag.
Only local DRY_RUN fixtures may use their own declared exact stable tags.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path


def latest_release(runtime: str, upstream: str, dry_run=False):
    fixture = os.environ.get('HERMES_MONITOR_RELEASE_METADATA_FILE')
    if fixture:
        meta = json.loads(Path(fixture).read_text())
    elif dry_run and not upstream.startswith(('https://', 'git@', 'ssh://')):
        tags = subprocess.check_output(['git', '-C', runtime, 'tag', '--sort=-version:refname'], text=True).splitlines()
        tag = next((t for t in tags if re.fullmatch(r'v\d+\.\d+\.\d+', t)), None)
        if not tag:
            raise RuntimeError('Fixture has no exact stable release tag')
        meta = {'tag_name': tag, 'draft': False, 'prerelease': False}
    else:
        url = 'https://api.github.com/repos/NousResearch/hermes-agent/releases/latest'
        req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'MGS-Hermes-release-monitor/2'})
        # Bounded retries for public metadata; no personal token fallback.
        last = None
        for _ in range(2):
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    meta = json.load(resp)
                break
            except Exception as exc:
                last = type(exc).__name__
        else:
            raise RuntimeError('Official release metadata unavailable: ' + str(last))
    tag = meta.get('tag_name')
    if meta.get('draft') is not False or meta.get('prerelease') is not False or not isinstance(tag, str) or not tag:
        raise RuntimeError('Release metadata does not prove published stable release')
    if re.search(r'(^rc\.|canary|(?:^|[-.])(?:rc|alpha|beta)(?:[.\d-]|$))', tag, re.I):
        raise RuntimeError('Release metadata/tag classification conflict; not declaring stable')
    return tag


if __name__ == '__main__':
    import sys
    try:
        print(latest_release(sys.argv[1], sys.argv[2], sys.argv[3] == '1'))
    except Exception as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
