# Hermes image generation via OpenAI-Codex OAuth — MGS

Use this reference when an MGS agent (especially agente legado/Creative Ops) can chat with `gpt-5.5` via `openai-codex`, but `image_generate` fails or falls back to FAL.

## Core distinction

`model.provider: openai-codex` only configures the chat/reasoning model. Image generation is selected separately via `image_gen.provider`.

If `image_gen.provider` is unset, Hermes keeps the historical in-tree FAL fallback even when other image plugins are registered. A profile can therefore be fully authenticated for GPT-5.5/Codex chat and still fail image generation with missing `FAL_KEY`.

## MGS default for agente legado-style creative image generation

Prefer Codex-backed OpenAI image generation before adding a new API key:

```yaml
model:
  default: gpt-5.5
  provider: openai-codex
  base_url: https://chatgpt.com/backend-api/codex
image_gen:
  provider: openai-codex
  model: gpt-image-2-medium
  openai-codex:
    model: gpt-image-2-medium
```

`openai-codex` image generation uses the existing ChatGPT/Codex OAuth token. Do not ask Rodolfo for `OPENAI_API_KEY` unless the Codex-backed image provider is unavailable or explicitly not desired.

## Verification workflow

1. Confirm config/auth without printing tokens:
   - profile `config.yaml`: `model.default`, `model.provider`, `image_gen.provider`, `image_gen.model`.
   - profile `auth.json`: `active_provider=openai-codex`, `auth_mode=chatgpt`, access token length, refresh token presence.
2. Restart/reload the target gateway after config change.
3. Validate logs show plugin registration such as `Plugin 'openai-codex' registered image_gen provider: openai-codex` and Discord reconnect if it is a gateway profile.
4. Run a small real tool test under the target profile, e.g. one-shot with image toolset:

```bash
hermes -p legacy-agent -t image_gen -z "Teste interno: use image_generate para gerar uma imagem quadrada simples. Responda apenas com o caminho do arquivo gerado ou o erro."
```

5. Verify the returned file exists and has expected dimensions (PNG under the profile cache is enough for the smoke test). Do not claim success from config alone.

## Operator messaging pattern

When explaining to Rodolfo or the agent channel:

- Say GPT-5.5 chat/raciocínio was already configured if logs/config prove it.
- Say the fix was the separate image backend.
- Instruct the agent not to improvise fake/generated status if the tool fails; it should report the exact technical error.
- Keep credentials out of the message.

## Pitfalls

- Do not conflate `OPENAI_API_KEY` with ChatGPT/Codex OAuth. The MGS default is OAuth when possible.
- Do not treat registered plugins as active providers. `image_gen.provider` must be explicitly set for plugin dispatch.
- Do not preserve or repost signed Discord CDN attachment URLs from imported threads; mention filenames or local evidence only.
- `gpt-image-2-medium` is the balanced default; use high only when quality requirements justify slower/costlier generation.
