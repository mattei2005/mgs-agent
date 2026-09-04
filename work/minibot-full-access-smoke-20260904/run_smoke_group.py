#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/root/mgs-agent/work/minibot-full-access-smoke-20260904')
ROOT.mkdir(parents=True, exist_ok=True)
PROFILE = Path('/root/.hermes/profiles/ares')
BASE = Path('/root/mgs-agent')


def cmd(name: str, argv: list[str], timeout: int = 240) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=os.environ.copy(),
        )
        return {
            'name': name,
            'rc': proc.returncode,
            'duration_s': round(time.monotonic() - started, 3),
            'stdout_tail': proc.stdout[-4000:],
            'stderr_tail': proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            'name': name,
            'rc': 124,
            'duration_s': round(time.monotonic() - started, 3),
            'stdout_tail': (exc.stdout or '')[-4000:] if isinstance(exc.stdout, str) else '',
            'stderr_tail': (exc.stderr or '')[-4000:] if isinstance(exc.stderr, str) else '',
            'timeout': True,
        }


def py(path: Path, *args: str) -> list[str]:
    return ['/usr/bin/python3', str(path), *args]


def shared(account: str, argv: list[str]) -> list[str]:
    return ['/usr/bin/flock', '-s', '-w', '90', f'/run/lock/ares-cpv-meta-lane-{account}.lock', *argv]


def exclusive(account: str, argv: list[str]) -> list[str]:
    return ['/usr/bin/flock', '-w', '90', f'/run/lock/ares-cpv-meta-lane-{account}.lock', *argv]


def run(group: str) -> list[dict]:
    pscript = PROFILE / 'scripts'
    mscript = BASE / 'scripts'
    engine = mscript / 'ares-campaign-engine-v3.py'
    if group == 'cpv13':
        account = '1046241194533786'
        cases = [
            ('cpv13_daily_readonly', shared(account, py(pscript / 'creditoparaveiculo-fixed-reports.py', '--mode', 'daily', '--dry-run', '--report-only'))),
            ('cpv13_intraday_readonly', shared(account, py(pscript / 'creditoparaveiculo-fixed-reports.py', '--mode', 'intraday', '--dry-run', '--report-only'))),
            ('cpv13_snapshot_readonly', shared(account, py(pscript / 'creditoparaveiculo-fixed-reports.py', '--mode', 'snapshot', '--dry-run'))),
            ('cpv13_reactivation_dry_run', shared(account, py(pscript / 'creditoparaveiculo-fixed-reports.py', '--mode', 'reactivate', '--dry-run'))),
            ('cpv13_first_delivery_dry_run', shared(account, py(pscript / 'creditoparaveiculo-first-delivery-guardrail.py', '--watch', '--dry-run', '--quiet'))),
            ('cpv13_engine_offline_smoke', py(mscript / 'ares-creditoparaveiculo-v3-daily.py', '--offline-smoke')),
            ('cpv13_engine_live_dry_run', py(mscript / 'ares-creditoparaveiculo-v3-daily.py', '--dry-run', '--operational-date', '2026-09-04')),
            ('cpv13_manifest_validate', py(engine, 'validate', '--manifest', str(BASE / 'data/ares/meta-ads/engine-v3/state/cpv13-pure-clone-c36-c40-20260831T065356Z.sealed.json'))),
            ('cpv13_manifest_plan', py(engine, 'plan', '--manifest', str(BASE / 'data/ares/meta-ads/engine-v3/state/cpv13-pure-clone-c36-c40-20260831T065356Z.sealed.json'))),
        ]
    elif group == 'cpv05':
        account = '2039876850230678'
        op = BASE / 'data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR-05-CREATIVE-CUT-24H.json'
        acct = BASE / 'data/ares/meta-ads/accounts/2039876850230678.json'
        general = py(pscript / 'creditoparaveiculo-general-daily.py', '--dry-run', '--report-only')
        general_locked = ['/usr/bin/flock', '-s', '-w', '90', '/run/lock/ares-cpv-meta-lane-1046241194533786.lock', '/usr/bin/flock', '-s', '-w', '90', '/run/lock/ares-cpv-meta-lane-2039876850230678.lock', *general]
        cases = [
            ('cpv05_daily_readonly', shared(account, py(pscript / 'creditoparaveiculo-account05-reports.py', '--mode', 'daily', '--dry-run', '--report-only'))),
            ('cpv05_intraday_readonly', shared(account, py(pscript / 'creditoparaveiculo-account05-reports.py', '--mode', 'intraday', '--dry-run', '--report-only'))),
            ('cpv05_first_delivery_dry_run', shared(account, py(pscript / 'creditoparaveiculo-account05-first-delivery.py', '--watch', '--dry-run', '--quiet'))),
            ('cpv05_creative_cut_preflight', exclusive(account, py(pscript / 'creditoparaveiculo-account05-creative-cut24h.py', '--watch', '--dry-run', '--preflight', '--quiet'))),
            ('cpv05_activity_monitor_dry_run', exclusive(account, py(mscript / 'ares-meta-account-activity-monitor.py', '--operation', str(op), '--account', str(acct), '--dry-run'))),
            ('cpv_general_daily_readonly', general_locked),
            ('cpv05_manifest_validate', py(BASE / 'scripts/ares-campaign-engine-v3.py', 'validate', '--manifest', str(PROFILE / 'work/cpv05-c11-c14-mixed-20260903/manifest-r3-sealed.json'))),
            ('cpv05_manifest_plan', py(BASE / 'scripts/ares-campaign-engine-v3.py', 'plan', '--manifest', str(PROFILE / 'work/cpv05-c11-c14-mixed-20260903/manifest-r3-sealed.json'))),
        ]
    elif group == 'eggbev':
        creation_manifest = BASE / 'data/ares/meta-ads/audit/eggbev/creation/eggbev-pg-8348-20260902-nicolas-01-manifest.json'
        pure_manifest = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-tina-c003-all-modes-20260830-nicolas-01-dup01-manifest.json'
        prestaged_manifest = BASE / 'data/ares/meta-ads/audit/eggbev/clone/eggbev-clone-tina-c003-all-modes-20260830-nicolas-01-dup02-manifest.json'
        cases = [
            ('eggbev_roas_readonly', py(BASE / 'scripts/ares-eggbev-roas-cycle.py', '--quiet')),
            ('eggbev_leads_readonly', py(BASE / 'scripts/ares-eggbev-page-lead-guardrail.py', '--quiet')),
            ('eggbev_restriction_readonly', py(BASE / 'scripts/ares-eggbev-page-restriction-guardrail.py', '--quiet')),
            ('eggbev_creation_offline_smoke', py(BASE / 'scripts/ares-eggbev-creation.py', 'offline-smoke')),
            ('eggbev_from_zero_validate', py(BASE / 'scripts/ares-campaign-engine-v3.py', 'validate', '--manifest', str(creation_manifest))),
            ('eggbev_from_zero_plan', py(BASE / 'scripts/ares-campaign-engine-v3.py', 'plan', '--manifest', str(creation_manifest))),
            ('eggbev_pure_clone_validate', py(BASE / 'scripts/ares-campaign-engine-v3.py', 'validate', '--manifest', str(pure_manifest))),
            ('eggbev_pure_clone_plan', py(BASE / 'scripts/ares-campaign-engine-v3.py', 'plan', '--manifest', str(pure_manifest))),
            ('eggbev_clone_prestaged_validate', py(BASE / 'scripts/ares-campaign-engine-v3.py', 'validate', '--manifest', str(prestaged_manifest))),
            ('eggbev_clone_prestaged_plan', py(BASE / 'scripts/ares-campaign-engine-v3.py', 'plan', '--manifest', str(prestaged_manifest))),
        ]
    else:
        raise SystemExit(f'unknown group: {group}')
    return [cmd(name, argv) for name, argv in cases]


def main() -> int:
    group = sys.argv[1]
    results = run(group)
    payload = {
        'group': group,
        'ok': all(row['rc'] == 0 for row in results),
        'passed': sum(row['rc'] == 0 for row in results),
        'total': len(results),
        'results': results,
    }
    out = ROOT / f'{group}.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'group': group,
        'ok': payload['ok'],
        'passed': payload['passed'],
        'total': payload['total'],
        'failures': [{'name': row['name'], 'rc': row['rc'], 'stderr_tail': row['stderr_tail'][-600:], 'stdout_tail': row['stdout_tail'][-600:]} for row in results if row['rc'] != 0],
        'output': str(out),
    }, ensure_ascii=False, indent=2))
    return 0 if payload['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
