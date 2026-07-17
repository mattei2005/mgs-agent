# Grok/xAI OAuth for MGS creative media rollout — 2026-06-16

Use this reference when Rodolfo wants Grok/SuperGrok integrated into MGS agents for image/video/avatar generation, especially agente legado Creative Ops, while keeping GPT/OpenAI-Codex available.

## Durable lesson

Hermes now supports xAI/Grok media through built-in provider plugins:

- image backend: `plugins/image_gen/xai`, selected by `image_gen.provider: xai` or called through an explicit wrapper.
- video backend: `plugins/video_gen/xai`, selected by `video_gen.provider: xai` and exposed via `video_generate`.
- X search: `x_search`, using the same xAI auth resolver.

For MGS, do **not** blindly switch agente legado's default image provider away from OpenAI-Codex. Rodolfo's intended workflow is natural tool choice:

```text
“agente legado, faz com GPT”       → GPT/OpenAI-Codex image generation.
“agente legado, faz com Grok”      → Grok/xAI explicit image/video wrapper or xAI video_gen.
“Faz nos dois e compara” → generate one GPT variant + one Grok variant and compare.
“Anima esse avatar”      → prefer Grok/xAI image-to-video/reference-to-video.
```

## OAuth setup pattern

Preferred user-facing path when Rodolfo chooses OAuth/SuperGrok:

```bash
hermes -p legacy-agent auth add xai-oauth --type oauth --manual-paste
```

Operational behavior:

1. Hermes prints an `https://auth.x.ai/oauth2/authorize?...` URL.
2. Rodolfo opens it and authorizes.
3. The browser either redirects to a failing `http://127.0.0.1:<port>/callback?...` URL or shows a bare code.
4. Paste the full callback URL or bare code into the waiting terminal/process.
5. Validate without printing secrets:

```bash
hermes -p legacy-agent auth status xai-oauth
```

If the OAuth was done for one profile and MGS needs shared operational access, copy only the `providers.xai-oauth` auth entry to the other profiles with backups, while preserving their `active_provider` as `openai-codex`. Never print token values; report token length and refresh-token presence only.

## Role-based rollout used for MGS

Recommended default scope:

```text
agente legado   xAI OAuth + video_gen + x_search; GPT remains default image provider.
Zeus   xAI OAuth + x_search/video smoke for audit; not day-to-day creative production.
Ares   xAI OAuth + x_search only; do not make Ares owner of creative generation.
Atena  xAI OAuth may be present for future auth reuse, but do not enable creative/search by default.
```

Config pattern for agente legado when GPT should remain default but Grok is also available:

```yaml
image_gen:
  provider: openai-codex
  model: gpt-image-2-medium
  openai-codex:
    model: gpt-image-2-medium
  xai:
    model: grok-imagine-image-quality
    resolution: 1k
video_gen:
  provider: xai
  model: grok-imagine-video
  xai:
    model: grok-imagine-video
    image_to_video_model: grok-imagine-video-1.5-preview
    resolution: 720p
    duration: 8
```

Toolsets can be enabled with:

```bash
hermes -p legacy-agent tools enable --platform discord video_gen x_search
hermes -p legacy-agent tools enable --platform cli video_gen x_search
hermes -p ares tools enable --platform discord x_search
hermes -p ares tools enable --platform cli x_search
```

## Explicit wrapper pattern

When the active Hermes `image_generate` provider remains GPT/OpenAI-Codex, use an explicit MGS wrapper for Grok image/video calls. This avoids flipping the global image provider back and forth.

Validated wrapper path from the rollout:

```text
/root/mgs-agent/scripts/mgs-grok-generate.py
```

Expected modes:

```bash
/root/mgs-agent/scripts/mgs-grok-generate.py image \
  --profile legacy-agent \
  --prompt '...' \
  --aspect-ratio 1:1 \
  --resolution 1k \
  --output-dir /root/mgs-agent/data/generated/grok

/root/mgs-agent/scripts/mgs-grok-generate.py video \
  --profile legacy-agent \
  --prompt '...' \
  --duration 8 \
  --aspect-ratio 16:9 \
  --resolution 720p \
  --output-dir /root/mgs-agent/data/generated/grok
```

The wrapper should:

- call `tools.xai_http.resolve_xai_http_credentials()` so OAuth refresh works;
- never print tokens;
- download output to a local file;
- print JSON summary with path/bytes/model/request_id;
- detect image extension by magic bytes, because xAI image endpoints may return JPEG bytes even when a `.png` name was initially chosen.

## Smoke validation pattern

Do not claim success from config alone. Run real media generation and validate output:

```bash
# Image smoke
/root/mgs-agent/scripts/mgs-grok-generate.py image --profile legacy-agent --prompt 'Internal smoke test...' --output-dir /root/mgs-agent/data/generated/grok-smoke

# Validate image dimensions/format
python3 - <<'PY'
from PIL import Image
from pathlib import Path
p = Path('/path/to/output')
im = Image.open(p)
print(p.exists(), p.stat().st_size, im.format, im.size)
PY

# Video smoke; background is fine because it may take >1 minute
/root/mgs-agent/scripts/mgs-grok-generate.py video --profile legacy-agent --prompt 'Internal smoke test...' --duration 2 --resolution 480p --output-dir /root/mgs-agent/data/generated/grok-smoke

# Validate video if ffprobe exists
ffprobe -v error -show_entries format=duration,size -show_streams -of json /path/to/output.mp4
```

Validated result shape from rollout:

```text
image: provider=xai-oauth, grok-imagine-image-quality, 1024x1024 file generated.
video: provider=xai-oauth, grok-imagine-video, H.264 MP4, 848x480, ~2.04s generated.
```

## Git/autocommit pitfall

Generated media files under `/root/mgs-agent/data/generated/` are outputs, not code. Add/keep this in `.gitignore` before running smoke tests in an auto-commit repo:

```gitignore
# Generated AI media artifacts (local smoke/ops outputs)
data/generated/
```

If auto-commit already versioned smoke media, remove it from Git with `git rm --cached` and commit a cleanup while keeping the local file.

## Gateway restart rule

Config/SOUL/toolset changes may require gateway reload/restart before Discord sees them. Do not restart Zeus/agente legado/Ares from an active Discord tool-call thread. Use the safe detached restart finalizer (`/root/mgs-agent/scripts/mgs-gateway-restart-safe.sh`) and report cleanly before scheduling.
