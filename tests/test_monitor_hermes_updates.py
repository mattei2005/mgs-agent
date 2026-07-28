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
    assert field(payload, "Versão local").find(installed[:7]) >= 0
    assert field(payload, "Upstream").find(upstream[:7]) >= 0
    assert field(payload, "Atraso").endswith("1 commits atrás")
    assert field(payload, "Resumo") == "Features 0 | Fixes 1 | Perf 0 | Security 0 | Breaking 0"
    assert not state.exists(), "dry-run must not mutate the configured state file"
    assert "state_unchanged=true discord_post=false" in log.read_text(encoding="utf-8")
