#!/usr/bin/env python3
"""MGS Grok/xAI media generator.

Operational wrapper for Ares/Zeus to call Grok Imagine via Hermes-managed
xAI OAuth (preferred) or XAI_API_KEY fallback without changing the active
Hermes image provider. This lets Ares use GPT/OpenAI-Codex through
`image_generate` and Grok through this explicit wrapper in the same workflow.

No secrets are printed. Outputs are downloaded to a local file and a JSON
summary is printed to stdout.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import shutil
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _bootstrap_active_hermes() -> None:
    """Use the published launcher contract, retaining legacy venv compatibility."""
    hermes_cmd = shutil.which("hermes")
    if not hermes_cmd:
        raise SystemExit("Hermes CLI not found in PATH")
    hermes_exe = Path(hermes_cmd).resolve()
    if hermes_exe.parent.name != "bin":
        raise SystemExit(f"Unable to resolve active Hermes checkout from {hermes_exe}")
    layout = hermes_exe.parent.parent.name
    checkout = hermes_exe.parent.parent.parent
    if layout == ".hermes":
        import subprocess
        # In a bootstrapped child the selected dependency generation is already leased.
        bootstrap = sys.modules.get("hermes_bootstrap")
        if bootstrap is not None and Path(bootstrap.__file__).resolve() == checkout / "hermes_bootstrap.py":
            if str(checkout) not in sys.path:
                sys.path.insert(0, str(checkout))
            return
        try:
            resolved = subprocess.run(
                [str(hermes_exe), "--print-runtime-command"],
                check=True, capture_output=True, text=True, timeout=20,
                env=os.environ.copy(),
            )
            command = json.loads(resolved.stdout)
            if not isinstance(command, list) or len(command) != 4 or not all(isinstance(x, str) for x in command) or command[1:3] != ["-I", "-c"]:
                raise ValueError("invalid installation-bound runtime command")
            python = Path(command[0])
            if not python.is_absolute() or not python.is_file():
                raise ValueError("installation-bound interpreter is absent")
        except (subprocess.SubprocessError, OSError, ValueError, json.JSONDecodeError) as error:
            raise SystemExit("Unable to resolve installation-bound Hermes runtime command") from error
        script = str(Path(__file__).resolve())
        # Do not persist/capture a dependency-generation path. Native bootstrap owns selection.
        code = (
            "import os,sys,runpy;"
            "os.environ.pop('PYTHONHOME',None);os.environ.pop('PYTHONPATH',None);"
            "os.environ.pop('VIRTUAL_ENV',None);"
            f"sys.path.insert(0,{str(checkout)!r});"
            "import hermes_bootstrap;"
            f"sys.path.insert(0,{str(Path(script).parent)!r});"
            f"sys.argv=[{script!r},*sys.argv[1:]];"
            f"runpy.run_path({script!r},run_name='__main__')"
        )
        os.execve(str(python), [str(python), "-I", "-c", code, *sys.argv[1:]], os.environ.copy())
        raise SystemExit("Hermes runtime re-exec returned unexpectedly")
    if layout not in {".venv", "venv"}:
        raise SystemExit(f"Unable to resolve active Hermes checkout from {hermes_exe}")
    python = hermes_exe.with_name("python")
    if Path(sys.executable).resolve() != python.resolve():
        os.execve(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]], os.environ.copy())
    if str(checkout) not in sys.path:
        sys.path.insert(0, str(checkout))


_bootstrap_active_hermes()

DEFAULT_BASE_URL = "https://api.x.ai/v1"


def _set_profile(profile: str) -> None:
    import re
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", profile):
        raise ValueError("Invalid media profile")
    home = Path("/root/.hermes/profiles") / profile
    os.environ["HERMES_HOME"] = str(home)
    # Hermes 0.3.x may install a context-local profile override before this
    # wrapper reaches main(). The context override wins over HERMES_HOME, so
    # set both or an explicit --profile can silently resolve another agent's
    # auth store.
    import importlib

    importlib.import_module("hermes_constants").set_hermes_home_override(home)


def _creds() -> tuple[str, str, str]:
    from tools.xai_http import resolve_xai_http_credentials

    data = resolve_xai_http_credentials()
    api_key = str(data.get("api_key") or "").strip()
    if not api_key:
        raise SystemExit("No xAI credentials available for this profile")
    return api_key, str(data.get("base_url") or DEFAULT_BASE_URL).rstrip("/"), str(data.get("provider") or "xai")


def _headers(api_key: str) -> dict[str, str]:
    try:
        from tools.xai_http import hermes_xai_user_agent

        ua = hermes_xai_user_agent()
    except Exception:
        ua = "MGS-Grok-Wrapper/1.0"
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": ua,
    }


def _json_request(method: str, url: str, api_key: str, payload: dict | None = None, timeout: int = 120) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = _headers(api_key)
    if method.upper() == "POST":
        headers["x-idempotency-key"] = str(uuid.uuid4())
    req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")[:1200]
        raise RuntimeError(f"HTTP {e.code} from xAI: {text}") from e


def _download(url: str, output: Path, timeout: int = 180) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "MGS-Grok-Wrapper/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    output.write_bytes(data)
    return len(data)


def _media_roots(profile: str = "ares") -> list[Path]:
    import re
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", profile):
        raise ValueError("Invalid media profile")
    home = Path("/root/.hermes/profiles") / profile
    # Fixed operational roots; caller-provided directories/env cannot grant
    # permission to upload auth stores, backups, private data or browser state.
    return [home / "artifacts", home / "workspace", home / "work",
            Path("/root/mgs-agent/data/generated"),
            Path("/root/mgs-agent/data/ares/creative-ops")]


def _image_ref(value: str, profile: str = "ares") -> str:
    import io
    import stat
    import subprocess
    from PIL import Image

    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://", "data:image/")):
        # Remote-download policy is a separate, unapproved item5.
        return value
    try:
        path = Path(value).expanduser().resolve(strict=True)
    except OSError as error:
        raise ValueError("Local image is absent or cannot be resolved") from error
    roots = [root.resolve() for root in _media_roots(profile)]
    if not any(path.is_relative_to(root) for root in roots):
        raise ValueError("Local image is outside the authorized media workspace")
    if any(part.lower() in {".secrets", "private", "backups", "browser-profiles", "sessions"} for part in path.parts):
        raise ValueError("Private paths cannot be uploaded as local images")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        opened_path = Path(os.readlink(f"/proc/self/fd/{stream.fileno()}"))
        if not any(opened_path.is_relative_to(root) for root in roots):
            raise ValueError("Local image parent changed outside the media workspace")
        if any(part.lower() in {".secrets", "private", "backups", "browser-profiles", "sessions"} for part in opened_path.parts):
            raise ValueError("Opened image is in a private path")
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 25 * 1024 * 1024:
            raise ValueError("Local image must be a regular file up to25MiB")
        data = stream.read(25 * 1024 * 1024 + 1)
    if len(data) != info.st_size:
        raise ValueError("Local image changed during read")
    try:
        with Image.open(io.BytesIO(data)) as picture:
            mime = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif"}.get(picture.format)
            picture.verify()
    except Exception as error:
        raise ValueError("Local reference is not a valid supported image") from error
    if not mime:
        raise ValueError("Unsupported local image format")
    # Production encoding and reverse hashes are produced by shell utilities.
    encoded = subprocess.run(["base64", "-w", "0"], input=data, capture_output=True, check=True).stdout
    reversed_data = subprocess.run(["base64", "--decode"], input=encoded, capture_output=True, check=True).stdout
    original_hash = subprocess.run(["sha256sum"], input=data, capture_output=True, check=True).stdout.split()[0]
    reverse_hash = subprocess.run(["sha256sum"], input=reversed_data, capture_output=True, check=True).stdout.split()[0]
    if original_hash != reverse_hash:
        raise RuntimeError("Local image encoding roundtrip hash mismatch")
    return f"data:{mime};base64,{encoded.decode('ascii')}"


def image(args: argparse.Namespace) -> dict:
    _set_profile(args.profile)
    api_key, base_url, provider = _creds()
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
    }
    body = _json_request("POST", f"{base_url}/images/generations", api_key, payload, timeout=args.timeout)
    item = (body.get("data") or [{}])[0]
    url = item.get("url") or body.get("url")
    b64 = item.get("b64_json") or body.get("b64_json")
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = Path(args.output_dir).expanduser() / f"grok-image-{ts}.img"
    if url:
        size = _download(url, out, timeout=args.timeout)
    elif b64:
        out.parent.mkdir(parents=True, exist_ok=True)
        raw = base64.b64decode(b64)
        out.write_bytes(raw)
        size = len(raw)
    else:
        raise RuntimeError(f"xAI image response has no url/b64_json: {json.dumps(body)[:800]}")

    # xAI may return JPEG bytes even for OpenAI-compatible image endpoints.
    # Rename by magic bytes so Drive/Discord consumers see the correct type.
    head = out.read_bytes()[:12]
    ext = ".jpg" if head.startswith(b"\xff\xd8\xff") else ".png" if head.startswith(b"\x89PNG") else ".img"
    final = out.with_suffix(ext)
    if final != out:
        out.replace(final)
        out = final
    return {
        "ok": True,
        "kind": "image",
        "provider": provider,
        "model": args.model,
        "path": str(out),
        "bytes": size,
        "prompt": args.prompt,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
    }


def video(args: argparse.Namespace) -> dict:
    _set_profile(args.profile)
    image_ref = _image_ref(args.image_url, args.profile) if args.image_url else None
    reference_refs = [_image_ref(x, args.profile) for x in (args.reference_image_url or [])]
    api_key, base_url, provider = _creds()
    payload: dict = {
        "model": args.model,
        "prompt": args.prompt,
        "duration": args.duration,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
    }
    if image_ref:
        payload["image"] = {"url": image_ref}
    if reference_refs:
        payload["reference_images"] = [{"url": x} for x in reference_refs]
    body = _json_request("POST", f"{base_url}/videos/generations", api_key, payload, timeout=60)
    request_id = body.get("request_id")
    if not request_id:
        raise RuntimeError(f"xAI video response missing request_id: {json.dumps(body)[:800]}")
    deadline = time.time() + args.timeout
    last = {}
    while time.time() < deadline:
        last = _json_request("GET", f"{base_url}/videos/{urllib.parse.quote(request_id)}", api_key, None, timeout=30)
        status = str(last.get("status") or "").lower()
        if status == "done":
            video_obj = last.get("video") or {}
            url = video_obj.get("url")
            if not url:
                raise RuntimeError(f"xAI video done without URL: {json.dumps(last)[:800]}")
            ts = time.strftime("%Y%m%d-%H%M%S")
            out = Path(args.output_dir).expanduser() / f"grok-video-{ts}.mp4"
            size = _download(url, out, timeout=300)
            return {
                "ok": True,
                "kind": "video",
                "provider": provider,
                "model": last.get("model") or args.model,
                "request_id": request_id,
                "path": str(out),
                "bytes": size,
                "duration": video_obj.get("duration") or args.duration,
                "aspect_ratio": args.aspect_ratio,
                "resolution": args.resolution,
                "prompt": args.prompt,
            }
        if status in {"failed", "error", "expired", "cancelled"}:
            raise RuntimeError(f"xAI video failed: {json.dumps(last)[:1200]}")
        time.sleep(args.poll_interval)
    raise RuntimeError(f"Timed out waiting for xAI video {request_id}; last={json.dumps(last)[:800]}")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate image/video with Grok Imagine via xAI OAuth/API key")
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--profile", default="ares", help="Hermes profile holding xAI OAuth tokens")
    common.add_argument("--prompt", required=True)
    common.add_argument("--output-dir", default="/root/mgs-agent/data/generated/grok")
    common.add_argument("--timeout", type=int, default=300)
    img = sub.add_parser("image", parents=[common])
    img.add_argument("--model", default="grok-imagine-image-quality")
    img.add_argument("--aspect-ratio", default="1:1")
    img.add_argument("--resolution", default="1k")
    vid = sub.add_parser("video", parents=[common])
    vid.add_argument("--model", default="grok-imagine-video")
    vid.add_argument("--image-url", help="Image URL/path for image-to-video")
    vid.add_argument("--reference-image-url", action="append", help="Reference image URL/path; repeat up to 7")
    vid.add_argument("--duration", type=int, default=8)
    vid.add_argument("--aspect-ratio", default="16:9")
    vid.add_argument("--resolution", default="720p")
    vid.add_argument("--poll-interval", type=int, default=5)
    args = p.parse_args()
    try:
        result = image(args) if args.cmd == "image" else video(args)
    except ValueError as error:
        print(json.dumps({"status": "rejected", "error": str(error)}, ensure_ascii=False))
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
