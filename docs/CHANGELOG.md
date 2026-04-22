# CHANGELOG — MGS Agent

Registro cronológico de mudanças operacionais na infraestrutura de agentes (Zeus, Atena) e integrações MGS.

## 2026-04-22

### Fix: compression threshold dos agentes Hermes (Zeus + Atena)

**Problema:** Warning técnico do Hermes vazava pro canal Discord da Atena, violando a regra do SOUL.md sobre "linguagem natural com humanos":

```
⚠ Compression model (claude-haiku-4-5-20251001) context is 200,000 tokens,
but the main model's compression threshold was 500,000 tokens...
```

**Causa:**
- Main model Sonnet 4.6 tem context = 1,000,000 tokens
- `compression.threshold` default = 0.50 (= 500k tokens) excedia o context do Haiku auxiliary (200k)
- Hermes auto-reduzia o threshold na primeira sessão e emitia o warning via `status_callback("lifecycle", ...)` → enviado direto pro Discord sem filtro

**Mudança aplicada em ambos config.yaml (Atena e Zeus):**

```yaml
compression:
  enabled: true
  threshold: 0.15        # era 0.5 — reduz pra 150k tokens (cabe em Haiku 200k)
  target_ratio: 0.2
  protect_last_n: 20
```

**Backups preservados:**
- `/root/.hermes/profiles/atena/config.yaml.bak_warnings`
- `/root/.hermes/profiles/zeus/config.yaml.bak_warnings`

**Cobertura:**
- ✅ Resolve o warning específico de compression auto-lower
- ⚠️ Outros lifecycle warnings futuros (ex: retry rate limit) ainda podem vazar pro Discord

**Pendente (Opção A — se necessário no futuro):**
Patch mínimo em `gateway/run.py:9482` (`_status_callback_sync`) adicionando filtro por env var `HERMES_SUPPRESS_LIFECYCLE=true`. Permitiria silenciar lifecycle messages na Atena (user-facing) mantendo-as ativas no Zeus (admin). ~5 linhas modificadas, reversível. Só aplicar se outro warning vazar.

**Upstream (reportável ao Hermes-Agent):**
Não existe flag nativa no Hermes pra suprimir mensagens de `status_callback("lifecycle", ...)` chegando no Discord. Issue candidato: `display.show_lifecycle_in_discord: false`.

### Context adicional (infra atual)

- Anthropic API: org `9642e8be-77aa-485f-8cdf-8c231d9015a7` em Tier 1 (30k ITPM, 8k OTPM, 50 RPM)
- Main model: claude-sonnet-4-6 em ambos profiles
- Auxiliary model: claude-haiku-4-5-20251001 (vision, title_generation, compression, etc)
- Sessões acumulam histórico — quando passam de 30k tokens, cada nova msg bate no rate limit Tier 1
