from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "monitor-hermes-updates.sh"


def run(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def git(*args: str, cwd: Path) -> str:
    proc = run(
        "git",
        "-c",
        "user.name=MGS Monitor Test",
        "-c",
        "user.email=monitor-test@mgs.invalid",
        *args,
        cwd=cwd,
    )
    return proc.stdout.strip()


def field(payload: dict, name: str) -> str:
    fields = payload["embeds"][0]["fields"]
    return next(item["value"] for item in fields if item["name"] == name)


def test_resolves_active_launcher_checkout_and_dry_run_is_side_effect_free(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    live = tmp_path / "active-runtime"
    bin_dir = tmp_path / "bin"
    output = tmp_path / "payload.json"
    state = tmp_path / "state.json"
    log = tmp_path / "monitor.log"

    origin.mkdir()
    git("init", "--bare", "--initial-branch=main", cwd=origin)
    seed.mkdir()
    git("init", "--initial-branch=main", cwd=seed)
    (seed / "marker.txt").write_text("installed\n", encoding="utf-8")
    git("add", "marker.txt", cwd=seed)
    git("commit", "-m", "feat: installed baseline", cwd=seed)
    installed = git("rev-parse", "HEAD", cwd=seed)
    git("remote", "add", "origin", str(origin), cwd=seed)
    git("push", "-u", "origin", "main", cwd=seed)

    (seed / "marker.txt").write_text("upstream\n", encoding="utf-8")
    git("commit", "-am", "fix: upstream change", cwd=seed)
    upstream = git("rev-parse", "HEAD", cwd=seed)
    git("push", "origin", "main", cwd=seed)

    run("git", "clone", str(origin), str(live), cwd=tmp_path)
    git("checkout", "--detach", installed, cwd=live)

    bin_dir.mkdir()
    launcher = bin_dir / "hermes-active"
    launcher.write_text(f"#!{live}/venv/bin/python3\n", encoding="utf-8")
    launcher.chmod(0o755)
    symlink = bin_dir / "hermes"
    symlink.symlink_to(launcher)

    env = os.environ.copy()
    env.update(
        {
            "HERMES_MONITOR_DRY_RUN": "1",
            "HERMES_MONITOR_BIN": str(symlink),
            "HERMES_MONITOR_UPSTREAM_URL": str(origin),
            "HERMES_MONITOR_LOG": str(log),
            "HERMES_MONITOR_STATE": str(state),
            "HERMES_MONITOR_DRY_RUN_OUTPUT": str(output),
        }
    )
    proc = run("bash", str(SCRIPT), cwd=ROOT, env=env)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert f"runtime_dir={live}" in proc.stdout
    assert "behind=1" in proc.stdout
    assert "discord_post=false" in proc.stdout
    assert field(payload, "Runtime MGS").find(installed[:7]) >= 0
    assert field(payload, "Upstream oficial").find(upstream[:7]) >= 0
    assert field(payload, "Atualizações acumuladas").endswith("1 commits pendentes no runtime")
    assert field(payload, "Resumo acumulado") == "Features 0 | Fixes 1 | Perf 0 | Security 0 | Breaking 0"
    assert not state.exists(), "dry-run must not mutate the configured state file"
    assert "state_unchanged=true discord_post=false" in log.read_text(encoding="utf-8")


def test_custom_runtime_on_top_of_upstream_is_current(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    live = tmp_path / "active-runtime"
    output = tmp_path / "payload.json"
    state = tmp_path / "state.json"
    log = tmp_path / "monitor.log"

    origin.mkdir()
    git("init", "--bare", "--initial-branch=main", cwd=origin)
    seed.mkdir()
    git("init", "--initial-branch=main", cwd=seed)
    (seed / "marker.txt").write_text("upstream\n", encoding="utf-8")
    git("add", "marker.txt", cwd=seed)
    git("commit", "-m", "feat: upstream baseline", cwd=seed)
    git("remote", "add", "origin", str(origin), cwd=seed)
    git("push", "-u", "origin", "main", cwd=seed)

    run("git", "clone", str(origin), str(live), cwd=tmp_path)
    (live / "mgs.txt").write_text("custom port\n", encoding="utf-8")
    git("add", "mgs.txt", cwd=live)
    git("commit", "-m", "fix(mgs): custom runtime", cwd=live)

    env = os.environ.copy()
    env.update(
        {
            "HERMES_MONITOR_DRY_RUN": "1",
            "HERMES_MONITOR_DIR": str(live),
            "HERMES_MONITOR_UPSTREAM_URL": str(origin),
            "HERMES_MONITOR_LOG": str(log),
            "HERMES_MONITOR_STATE": str(state),
            "HERMES_MONITOR_DRY_RUN_OUTPUT": str(output),
        }
    )
    proc = run("bash", str(SCRIPT), cwd=ROOT, env=env)

    assert "contains_upstream=true" in proc.stdout
    assert "discord_post=false" in proc.stdout
    assert not output.exists(), "an up-to-date custom runtime must not build an alert payload"
    assert not state.exists(), "dry-run must not mutate the configured state file"
    assert "OK already_contains_upstream" in log.read_text(encoding="utf-8")


def test_frozen_runtime_origin_does_not_hide_official_upstream(tmp_path: Path) -> None:
    frozen_origin = tmp_path / "frozen-origin.git"
    official_origin = tmp_path / "official-origin.git"
    seed = tmp_path / "seed"
    live = tmp_path / "active-runtime"
    output = tmp_path / "payload.json"
    state = tmp_path / "state.json"
    log = tmp_path / "monitor.log"

    frozen_origin.mkdir()
    official_origin.mkdir()
    git("init", "--bare", "--initial-branch=main", cwd=frozen_origin)
    git("init", "--bare", "--initial-branch=main", cwd=official_origin)
    seed.mkdir()
    git("init", "--initial-branch=main", cwd=seed)
    (seed / "marker.txt").write_text("installed\n", encoding="utf-8")
    git("add", "marker.txt", cwd=seed)
    git("commit", "-m", "feat: installed baseline", cwd=seed)
    installed = git("rev-parse", "HEAD", cwd=seed)
    git("remote", "add", "frozen", str(frozen_origin), cwd=seed)
    git("remote", "add", "official", str(official_origin), cwd=seed)
    git("push", "frozen", "main", cwd=seed)
    git("push", "official", "main", cwd=seed)

    run("git", "clone", str(frozen_origin), str(live), cwd=tmp_path)
    (seed / "marker.txt").write_text("official update\n", encoding="utf-8")
    git("commit", "-am", "fix: official upstream advanced", cwd=seed)
    upstream = git("rev-parse", "HEAD", cwd=seed)
    git("push", "official", "main", cwd=seed)

    env = os.environ.copy()
    env.update(
        {
            "HERMES_MONITOR_DRY_RUN": "1",
            "HERMES_MONITOR_DIR": str(live),
            "HERMES_MONITOR_UPSTREAM_URL": str(official_origin),
            "HERMES_MONITOR_LOG": str(log),
            "HERMES_MONITOR_STATE": str(state),
            "HERMES_MONITOR_DRY_RUN_OUTPUT": str(output),
        }
    )
    proc = run("bash", str(SCRIPT), cwd=ROOT, env=env)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "behind=1" in proc.stdout
    assert field(payload, "Runtime MGS").find(installed[:7]) >= 0
    assert field(payload, "Upstream oficial").find(upstream[:7]) >= 0
    assert field(payload, "Atualizações acumuladas").endswith("1 commits pendentes no runtime")
    assert not state.exists(), "dry-run must not mutate the configured state file"


def test_production_path_posts_via_injected_transport_and_updates_state(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    live = tmp_path / "active-runtime"
    state = tmp_path / "state.json"
    log = tmp_path / "monitor.log"
    capture = tmp_path / "curl-args.txt"
    fake_curl = tmp_path / "fake-curl.sh"

    origin.mkdir()
    git("init", "--bare", "--initial-branch=main", cwd=origin)
    seed.mkdir()
    git("init", "--initial-branch=main", cwd=seed)
    (seed / "marker.txt").write_text("installed\n", encoding="utf-8")
    git("add", "marker.txt", cwd=seed)
    git("commit", "-m", "feat: installed baseline", cwd=seed)
    installed = git("rev-parse", "HEAD", cwd=seed)
    git("remote", "add", "origin", str(origin), cwd=seed)
    git("push", "-u", "origin", "main", cwd=seed)
    run("git", "clone", str(origin), str(live), cwd=tmp_path)
    git("checkout", "--detach", installed, cwd=live)

    (seed / "marker.txt").write_text("upstream\n", encoding="utf-8")
    git("commit", "-am", "fix: upstream change", cwd=seed)
    upstream = git("rev-parse", "HEAD", cwd=seed)
    git("push", "origin", "main", cwd=seed)

    fake_curl.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$HERMES_MONITOR_CAPTURE\"\nprintf '200'\n",
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "HERMES_MONITOR_DRY_RUN": "0",
            "HERMES_MONITOR_SKIP_ENV_LOAD": "1",
            "HERMES_MONITOR_DIR": str(live),
            "HERMES_MONITOR_UPSTREAM_URL": str(origin),
            "HERMES_MONITOR_LOG": str(log),
            "HERMES_MONITOR_STATE": str(state),
            "HERMES_MONITOR_CURL_BIN": str(fake_curl),
            "HERMES_MONITOR_CAPTURE": str(capture),
            "DISCORD_BOT_TOKEN": "fixture-token",
        }
    )
    run("bash", str(SCRIPT), cwd=ROOT, env=env)

    saved = json.loads(state.read_text(encoding="utf-8"))
    args = capture.read_text(encoding="utf-8")
    assert saved["last_notified_upstream"] == upstream
    assert saved["commits_behind"] == 1
    assert "Authorization: Bot fixture-token" in args
    assert "Hermes Agent — update disponível" in args
    assert "OK notified" in log.read_text(encoding="utf-8")
