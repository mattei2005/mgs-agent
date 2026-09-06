from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "monitor-hermes-updates.sh"
EXPLAINER = ROOT / "scripts" / "hermes-news-explainer.py"


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
    git("tag", "v2026.1.1", installed, cwd=seed)
    git("remote", "add", "origin", str(origin), cwd=seed)
    git("push", "-u", "origin", "main", "--tags", cwd=seed)

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
    assert "stable_update=false" in proc.stdout
    assert "stable_pending=0" in proc.stdout
    assert "main_post_release=1" in proc.stdout
    assert "discord_post=false" in proc.stdout
    assert field(payload, "Runtime MGS").find(installed[:7]) >= 0
    assert field(payload, "Última release oficial").find(installed[:7]) >= 0
    assert field(payload, "Main de desenvolvimento").find(upstream[:7]) >= 0
    assert field(payload, "Atualização estável").startswith("Nenhuma")
    assert "1 commit no grafo" in field(payload, "Main de desenvolvimento")
    assert field(payload, "Como ler as contagens") == (
        "Atualização estável = release oficial ainda não contida no runtime\n"
        "Main pós-release = desenvolvimento ainda sem release; não é pendência operacional\n"
        "Novos = avanço do main desde o alerta anterior"
    )
    assert field(payload, "Resumo do main pós-release") == "Features 0 | Fixes 1 | Perf 0 | Security 0 | Breaking 0"
    assert "Nenhuma atualização estável pendente" in field(payload, "Ação MGS")
    assert payload["embeds"][0]["title"] == "Hermes Agent — novidades em desenvolvimento"
    assert "commits pendentes no runtime" not in output.read_text(encoding="utf-8")
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
    git("tag", "v2026.1.1", cwd=seed)
    git("remote", "add", "origin", str(origin), cwd=seed)
    git("push", "-u", "origin", "main", "--tags", cwd=seed)

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
    git("tag", "v2026.1.1", installed, cwd=seed)
    git("remote", "add", "frozen", str(frozen_origin), cwd=seed)
    git("remote", "add", "official", str(official_origin), cwd=seed)
    git("push", "frozen", "main", "--tags", cwd=seed)
    git("push", "official", "main", "--tags", cwd=seed)

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
    assert "stable_pending=0" in proc.stdout
    assert "main_post_release=1" in proc.stdout
    assert field(payload, "Runtime MGS").find(installed[:7]) >= 0
    assert field(payload, "Última release oficial").find(installed[:7]) >= 0
    assert field(payload, "Main de desenvolvimento").find(upstream[:7]) >= 0
    assert field(payload, "Atualização estável").startswith("Nenhuma")
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
    git("tag", "v2026.1.1", installed, cwd=seed)
    git("remote", "add", "origin", str(origin), cwd=seed)
    git("push", "-u", "origin", "main", "--tags", cwd=seed)
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
    assert saved["schema_version"] == 2
    assert saved["stable_update_available"] is False
    assert saved["stable_commits_pending"] == 0
    assert saved["main_post_release_commits"] == 1
    assert saved["commits_behind"] == 0
    assert f"Authorization: Bot {env['DISCORD_BOT_TOKEN']}" in args
    assert "Hermes Agent — novidades em desenvolvimento" in args
    assert "commits pendentes no runtime" not in args
    assert "OK notified" in log.read_text(encoding="utf-8")


def test_new_release_is_the_only_case_labeled_as_stable_update(tmp_path: Path) -> None:
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
    (seed / "marker.txt").write_text("release one\n", encoding="utf-8")
    git("add", "marker.txt", cwd=seed)
    git("commit", "-m", "feat: release one", cwd=seed)
    release_one = git("rev-parse", "HEAD", cwd=seed)
    git("tag", "v2026.1.1", release_one, cwd=seed)
    git("remote", "add", "origin", str(origin), cwd=seed)
    git("push", "-u", "origin", "main", "--tags", cwd=seed)

    run("git", "clone", str(origin), str(live), cwd=tmp_path)
    git("checkout", "--detach", release_one, cwd=live)

    (seed / "marker.txt").write_text("release two\n", encoding="utf-8")
    git("commit", "-am", "fix: release two", cwd=seed)
    release_two = git("rev-parse", "HEAD", cwd=seed)
    git("tag", "v2026.1.2", release_two, cwd=seed)
    (seed / "dev.txt").write_text("post release\n", encoding="utf-8")
    git("add", "dev.txt", cwd=seed)
    git("commit", "-m", "feat: post release development", cwd=seed)
    main_head = git("rev-parse", "HEAD", cwd=seed)
    git("push", "origin", "main", "--tags", cwd=seed)

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
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert "stable_update=true" in proc.stdout
    assert "stable_pending=1" in proc.stdout
    assert "main_post_release=1" in proc.stdout
    assert payload["embeds"][0]["title"] == "Hermes Agent — atualização estável disponível"
    assert field(payload, "Última release oficial").find(release_two[:7]) >= 0
    assert field(payload, "Main de desenvolvimento").find(main_head[:7]) >= 0
    assert field(payload, "Atualização estável").startswith("Disponível: 1 commit")
    assert field(payload, "Resumo da atualização estável") == (
        "Features 0 | Fixes 1 | Perf 0 | Security 0 | Breaking 0"
    )
    assert "Atualização estável disponível" in field(payload, "Ação MGS")
    assert "commits pendentes no runtime" not in output.read_text(encoding="utf-8")
    assert not state.exists(), "dry-run must not mutate the configured state file"


def test_explainer_cannot_recommend_main_as_a_stable_update() -> None:
    source = EXPLAINER.read_text(encoding="utf-8")
    assert "main pós-release” é desenvolvimento ainda sem release" in source
    assert "não recomende atualizar" in source
    assert "Nunca trate commits do main pós-release como atraso do runtime" in source
