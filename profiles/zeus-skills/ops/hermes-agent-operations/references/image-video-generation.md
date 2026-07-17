# Image and Video Generation Providers

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 4. Image generation / OpenAI-Codex OAuth

Use quando um agente MGS, especialmente agente legado/Creative Ops, já conversa em `gpt-5.5` via `openai-codex`, mas falha ao gerar imagem ou pede `OPENAI_API_KEY`/`FAL_KEY`. Também use em revisões gerais tipo “confere tudo” para validar que o perfil esperado para imagem (agente legado) consegue gerar um arquivo real.

Para rollout Grok/xAI com OAuth SuperGrok em Creative Ops, mantendo GPT e Grok disponíveis por pedido natural (“faz com GPT”, “faz com Grok”, “faz nos dois”), use `references/grok-xai-oauth-creative-media-rollout-2026-06-16.md`. Regra central: não trocar automaticamente o provider de imagem padrão da agente legado se o objetivo é ter GPT + Grok lado a lado; manter `image_gen.provider: openai-codex` para GPT e usar wrapper explícito/`video_gen.provider: xai` para Grok imagem/vídeo/avatar.

Validação prática preferida para smoke test de imagem: depois do `hermes -p legacy-agent -t image_gen ...` retornar um caminho, verificar arquivo com `stat` e dimensões via Python/Pillow (`Image.open(path).width/height/format`). Não depender de utilitários opcionais como `file`; a evidência suficiente é path existente, tamanho >0 e dimensões/formato válidos.

Regra MGS de papel: geração de criativos/imagens é responsabilidade da agente legado. Zeus é GM/admin e não precisa de `image_gen`; ausência de `image_gen` no Zeus é estado esperado, não falha funcional. Só configurar Zeus para imagem se Rodolfo pedir explicitamente que Zeus passe a gerar imagem.

Não rodar smoke test de `image_generate` no perfil Zeus por padrão: isso aciona o fallback FAL sem chave, registra erro esperado nos logs e gera ruído de diagnóstico. Para validar imagem, usar agente legado (`hermes -p legacy-agent -t image_gen ...`) ou apenas verificar a config se o objetivo for revisar Zeus.

Regra principal: **chat/raciocínio e geração de imagem são configurações separadas**. `model.provider: openai-codex` não seleciona automaticamente o backend de imagem. Se `image_gen.provider` estiver ausente, o Hermes mantém fallback histórico para FAL mesmo com plugin `openai-codex` registrado.

Config MGS recomendada para agente legado:

```yaml
image_gen:
  provider: openai-codex
  model: gpt-image-2-medium
  openai-codex:
    model: gpt-image-2-medium
```

Depois de alterar, reiniciar/recarregar o gateway e fazer teste real com o toolset de imagem, por exemplo:

```bash
hermes -p legacy-agent -t image_gen -z "Teste interno: use image_generate para gerar uma imagem quadrada simples. Responda apenas com o caminho do arquivo gerado ou o erro."
```

Só reportar sucesso depois de verificar arquivo gerado/dimensões. Não pedir `OPENAI_API_KEY` se o provider `openai-codex` de imagem estiver disponível e o profile já tiver OAuth Codex válido. Detalhes e pitfalls: `references/hermes-image-gen-openai-codex-mgs.md`.

## 4.1 xAI/Grok Imagine rollout for image, video, and avatars

Use when Rodolfo wants Grok/xAI used for Creative Ops, especially image/video/avatar generation across MGS.

Key operational rule: **SuperGrok subscription is not enough by itself**. Hermes must have usable xAI credentials in the profile/gateway context: either xAI Grok OAuth (`xai-oauth`, via `hermes model` / `hermes auth add xai-oauth`) or `XAI_API_KEY` sourced securely. For production, prefer storing an API key in 1Password (`MGS Conteúdo` → `xAI API - MGS` → field `api key`) and injecting it without printing.

Hermes has bundled xAI providers:

```text
Capability      Provider/config              Models / surface
--------------  ---------------------------  ----------------------------------
Image           image_gen.provider: xai       grok-imagine-image, quality
Video           video_gen.provider: xai       grok-imagine-video, 1.5 preview
X Search        x_search toolset              Grok/X search via xAI creds
```

Rollout pattern:

1. Verify credential presence without exposing secrets: auth status for `xai-oauth`, `XAI_API_KEY` presence/len, or 1Password item/field presence.
2. Configure by role, not by blanket behavior:
   - agente legado owns creative production; enable `image_gen`/`video_gen` for Grok production.
   - Ares can consume/search/iterate campaign creatives but does not become Creative Ops owner.
   - Zeus may enable for audit/smoke tests, not daily creative work.
   - Atena stays out of generic Grok creative production unless explicitly approved.
3. Enable `video_gen` per profile/platform; it is disabled by default.
4. Run real smoke tests before declaring production-ready: one image, one text-to-video, one avatar/reference-to-video using an approved test image.
5. Log requester/profile/provider/model/duration/resolution/output/estimated cost and enforce budget guardrails before broad team usage.
6. For real-person avatar/likeness, require approved source image and permission; clean metadata before Drive/handoff.

Detailed session/runbook: `references/mgs-grok-imagine-rollout-2026-06-16.md`.
