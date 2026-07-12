#!/root/.hermes/hermes-agent/venv/bin/python3
"""MGS Grok/xAI media generator.

Operational wrapper for Hera/Zeus to call Grok Imagine via Hermes-managed
xAI OAuth (preferred) or XAI_API_KEY fallback without changing the active
Hermes image provider. This lets Hera use GPT/OpenAI-Codex through
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
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path("/root/.hermes/hermes-agent")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_BASE_URL = "https://api.x.ai/v1"


def _set_profile(profile: str) -> None:
    os.environ["HERMES_HOME"] = f"/root/.hermes/profiles/{profile}"


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


def _image_ref(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://", "data:image/")):
        return value
    path = Path(value).expanduser()
    if not path.is_file():
        return value
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


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
    api_key, base_url, provider = _creds()
    payload: dict = {
        "model": args.model,
        "prompt": args.prompt,
        "duration": args.duration,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
    }
    if args.image_url:
        payload["image"] = {"url": _image_ref(args.image_url)}
    if args.reference_image_url:
        payload["reference_images"] = [{"url": _image_ref(x)} for x in args.reference_image_url]
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
    result = image(args) if args.cmd == "image" else video(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
