# Hera Creative Ops calibration + xAI auth recovery — 2026-06-17

Use when Rodolfo says Hera feels lost/low-quality, asks why Hera did not use tools for references, or asks to fix Grok/GPT creative generation.

## Durable lesson

A Creative Ops agent can have the right identity and toolsets but still behave like a generic chatbot if the SOUL/skill does not enforce production gates.

For Hera-style creative work, the operational standard is:

1. Treat Hera as a creative producer / art director, not only a prompt assistant.
2. If a user supplies a creative reference link/image/video/ad, analyze the reference first with available tools before rendering the final asset.
3. If the requested provider is part of the deliverable (GPT, Grok, or both), validate provider auth/output before claiming completion.
4. If a required reference or provider is blocked, stop before final generation and report the blocker + next action. Do not produce an approximate final “inspired by” asset in the dark.
5. Validate outputs as real files: image dimensions/format or video ffprobe; sanitize metadata for final creative deliverables.

## xAI/Grok auth recovery pattern

If Hera has `xai-oauth` present but unusable (`access_len=0`, no refresh token), and another MGS profile has valid xAI OAuth:

- Copy only the `providers.xai-oauth` auth entry from the valid profile into Hera's `auth.json`.
- Preserve Hera's `active_provider` as `openai-codex`; xAI is the media/search provider, not the chat provider.
- Never print token values; report token length and refresh presence only.
- Run `hermes -p hera auth status xai-oauth` and real media smoke tests before declaring fixed.

Expected validation shape:

```text
hera auth: active=openai-codex, xai access_len>0, refresh=true
Grok image smoke: file exists, bytes>0, image opens with dimensions
Grok video smoke: MP4 exists, ffprobe shows H.264/duration/dimensions
Sanitizer: clean=true, harmful_tags_after=0
GPT image smoke: file exists, image opens with dimensions
hera-gateway: active/running after safe restart
```

## Skill/SOUL patch points

Patch Hera's SOUL and Creative Ops skill to include:

- hard gate for external references: analyze first, render later;
- hard gate for GPT+Grok comparison: deliver both real provider outputs or report blocker;
- explicit prohibition on labeling local/GPT fallback as Grok;
- professional creative sequence: reference analysis → visual language extraction → storyboard/plan → render → visual validation → metadata clean → delivery.

## Reporting nuance

If this task modifies Hera SOUL, skills, auth/config, or infra inventory, it is infra-affecting. Sync/version the profile where applicable, restart Hera safely/detached if runtime prompt/auth changed, append audit, and update inventory/report infra before saying done.