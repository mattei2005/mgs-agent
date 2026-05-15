---
name: openai-codex-oauth
description: "Configurar e gerenciar o provider openai-codex via OAuth ChatGPT no Hermes MGS: autenticação por assinatura (sem custo por token), troca de provider, validação e migração."
tags: [hermes, openai, gpt, oauth, provider, custo, migração]
related_skills: [hermes-update, discord-ops]
---

# OpenAI Codex OAuth — Provider GPT via Assinatura ChatGPT

## Quando usar

Rodolfo quer trocar o provider de um agente (Zeus/Atena) de Anthropic pay-per-token para GPT via assinatura ChatGPT — sem custo por token, usando a assinatura mensal.

## Contexto de negócio

- **Endpoint:** `chatgpt.com/backend-api/codex` (NÃO `api.openai.com`)
- **Auth:** OAuth device code — usa assinatura ChatGPT (Plus/Pro/Team), não API key
- **Custo:** fixo mensal da assinatura, sem pay-per-token
- **Modelo:** `gpt-5.5` (ou o mais recente disponível no plano)
- **Plano referência MGS:** $100/mês (plano intermediário OpenAI)
- **Configurado em:** 2026-05-15 no perfil raiz (`~/.hermes/config.yaml`)

## Estado atual (2026-05-15)

| Perfil | Provider | Modelo | Status |
|---|---|---|---|
| Raiz (`~/.hermes/`) | openai-codex | gpt-5.5 | ✅ OAuth ativo |
| Zeus (`profiles/zeus/`) | anthropic | claude-sonnet-4-6 | ⏳ pendente migração |
| Atena (`profiles/atena/`) | anthropic | claude-sonnet-4-6 | ⏳ pendente migração |

---

## Como fazer login (device code flow)

```bash
hermes model
# → Selecionar "openai-codex" na lista de providers
# → Hermes exibe código de 8 letras + URL
# → Abrir URL no browser, inserir código, autorizar com conta OpenAI
# → Token salvo automaticamente em ~/.hermes/auth.json
```

O Hermes cria sessão própria — independente do Codex CLI ou VS Code.

---

## Verificar credenciais após login

```bash
# Verificar auth.json
python3 -c "
import json
with open('/root/.hermes/auth.json') as f:
    d = json.load(f)
print('active_provider:', d.get('active_provider'))
providers = d.get('providers', {})
for k in providers:
    p = providers[k]
    if isinstance(p, dict):
        print(f'provider: {k}')
        print(f'  auth_mode: {p.get(\"auth_mode\")}')
        tokens = p.get('tokens', {})
        print(f'  access_token: len={len(tokens.get(\"access_token\",\"\"))}')
        print(f'  refresh_token: presente={bool(tokens.get(\"refresh_token\"))}')
"

# Verificar config ativo
grep -A4 "^model:" ~/.hermes/config.yaml
```

**Saída esperada:**
- `active_provider: openai-codex`
- `auth_mode: chatgpt`
- `access_token: len=XXX` (token JWT longo)
- `refresh_token: presente=True`

---

## Aplicar ao perfil de um agente (Zeus/Atena)

```bash
# Editar config do perfil Zeus
cat /root/.hermes/profiles/zeus/config.yaml | grep -A4 "^model:"
# Atualizar provider e modelo:
# model:
#   default: gpt-5.5
#   provider: openai-codex
#   base_url: https://chatgpt.com/backend-api/codex

# Copiar auth do perfil raiz para o perfil Zeus (tokens compartilhados)
# OU rodar hermes model dentro do perfil Zeus especificamente

# Reiniciar gateway após mudança
systemctl restart zeus-gateway.service
sleep 5
systemctl is-active zeus-gateway.service
```

---

## Considerações antes de migrar Zeus/Atena

1. **Rate limit da assinatura** — verificar se o plano aguenta volume de tool calls (agentes fazem muitas chamadas seguidas). Testar isolado antes de migrar produção.

2. **Prompt caching** — Claude tem prompt caching que reduz custo em 50-80% para system prompts grandes. GPT via OAuth não tem custo por token, então isso não se aplica — mas o comportamento de tool calling pode ser diferente.

3. **SOUL.md e memories tuned para Claude** — Zeus e Atena têm instruções e memórias otimizadas para Claude. Após migração, pode ser necessário ajustar tom/instruções para GPT.

4. **Skills em PT-BR** — Skills estão escritas para Claude. GPT segue as instruções mas pode ter comportamentos ligeiramente diferentes em edge cases.

5. **Modelo gpt-5.5** — modelo disponível via endpoint Codex. Pode mudar conforme OpenAI atualiza o plano.

---

## Pitfalls

1. **Perfil raiz ≠ perfil do agente** — configurar via `hermes model` no terminal raiz atualiza `~/.hermes/config.yaml`, não os perfis Zeus/Atena em `profiles/*/config.yaml`. Os gateways dos agentes usam seus próprios perfis.

2. **Token expira** — access_token JWT expira (tipicamente em horas). O Hermes faz refresh automático usando o refresh_token. Se o refresh falhar, rodar `hermes model` novamente para re-autenticar.

3. **`hermes model --status` não existe** — para verificar provider ativo, usar `grep` no config.yaml ou inspecionar auth.json diretamente.

4. **Endpoint Codex ≠ API OpenAI** — algumas ferramentas/integrações que esperam `api.openai.com` não funcionam com o endpoint Codex. O Hermes suporta nativamente via `codex_responses` transport.
