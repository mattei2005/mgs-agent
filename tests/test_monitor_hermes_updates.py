"""Entrypoint invariants; commit-alert fixtures superseded by release-only suite.
Behavior/transport/ancestry coverage: test_hermes_release_only_monitor.py.
Authority: Rodolfo message 1556908630278803478.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_entrypoint_preserves_canonical_launcher_and_environment_loading():
    source = (ROOT / 'scripts/monitor-hermes-updates.sh').read_text()
    assert 'mgs_hermes_release_monitor.py' in source
    assert 'HERMES_MONITOR_DRY_RUN' in source
    assert 'HERMES_MONITOR_SKIP_ENV_LOAD' in source
    assert 'set -euo pipefail' in source


def test_explainer_cannot_recommend_main_as_a_stable_update():
    source = (ROOT / 'scripts/hermes-news-explainer.py').read_text()
    assert 'total main pós-release e commits do main ainda não contidos no runtime' in source
    assert 'Nenhuma atualização estável não prova main atualizado' in source
    assert 'Não transforme RC/canary em release estável' in source


def test_official_notification_policy_does_not_change_full_update_scope():
    source = (ROOT / 'scripts/hermes-news-explainer.py').read_text()
    assert 'Atualizar tudo na MGS significa main' in source
    monitor = (ROOT / 'scripts/mgs_hermes_release_monitor.py').read_text()
    assert 'official-release-only' in monitor
    assert 'main_commits_pending=main_pending' in monitor
    assert 'last_notified_release_commit' in monitor
