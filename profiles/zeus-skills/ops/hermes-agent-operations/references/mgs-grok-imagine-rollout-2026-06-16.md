# MGS Grok Imagine rollout — image/video/avatar

Use this reference when Rodolfo asks to implement Grok/xAI for image/video/avatar generation across MGS agents.

## Session context

Rodolfo upgraded to SuperGrok and asked to implement Grok for the whole operation, not just a small sandbox. The operational target is still role-based: agente legado owns creative production, Ares consumes/searches campaign creatives, Zeus audits/configures/monitors, and Atena should not become a general creative agent.

## Durable findings from live Hermes/MGS inspection

- Hermes has bundled xAI providers for:
  - `image_gen.provider: xai` via `plugins/image_gen/xai` using `grok-imagine-image` / `grok-imagine-image-quality`.
  - `video_gen.provider: xai` via `plugins/video_gen/xai` using `grok-imagine-video` / `grok-imagine-video-1.5-preview`.
  - `x_search` via xAI/Grok OAuth or `XAI_API_KEY`.
- `video_gen` is disabled by default in Hermes toolsets and must be explicitly enabled per profile/platform.
- xAI auth routes supported by Hermes:
  - xAI Grok OAuth through `hermes model` / `hermes auth add xai-oauth` (SuperGrok / Premium+ path).
  - `XAI_API_KEY`, preferably stored in 1Password and injected/sourced without printing.
- `video_generate` supports a unified surface:
  - text-to-video: `prompt` only.
  - image-to-video: `prompt` + `image_url`.
  - reference images: `reference_image_urls` where supported; xAI supports up to 7 and clamps reference-image duration to 10s.

## Recommended rollout sequence

1. **Credential first**
   - Preferred for production stability: create xAI API key at `https://console.x.ai` and store in 1Password vault `MGS Conteúdo` as item `xAI API - MGS`, field `api key`.
   - Alternative: authenticate via OAuth/SuperGrok with `hermes model` or `hermes auth add xai-oauth` if Rodolfo can complete browser login.
   - Never print the key/token. Report only item name and secret length/presence.

2. **Role-based enablement**
   - agente legado: enable `image_gen` + `video_gen`; set image/video providers to `xai` when Grok is the desired creative backend.
   - Ares: enable `x_search` and, if needed, `video_gen` for campaign creative iteration/analysis; do not let Ares own Creative Ops or campaign-adjacent systems outside its scope.
   - Zeus: enable only as needed for smoke tests/audit; Zeus is not the daily creative producer.
   - Atena: keep out of general Grok creative production by default; content/editorial image flows remain Atena-specific unless Rodolfo approves an exception.

3. **Smoke tests before declaring production-ready**
   - Generate one simple image and validate returned file/URL.
   - Generate one short text-to-video clip and validate downloadable video metadata.
   - Generate one avatar/reference-to-video from an approved test image and validate likeness/consistency manually.
   - Record cost estimate, duration, provider/model, output path/URL, and any safety refusal.

4. **Operational guardrails**
   - Put budget/cost limits in the wrapper/reporting layer before broad usage.
   - Log every generation request with requester, profile, provider, model, duration/resolution, output path/URL, and estimated cost.
   - For real-person avatars/likeness, require explicit permission/approved source image.
   - Clean metadata before Drive/handoff using the existing Creative Ops sanitizer.

## Common pitfall

Do not stop at “SuperGrok plan exists”. Hermes still needs either xAI OAuth tokens in the relevant profile auth store or an `XAI_API_KEY` reachable by the gateway/profile. The first implementation step is credential registration, not editing prompts or asking agente legado to try generation blindly.
