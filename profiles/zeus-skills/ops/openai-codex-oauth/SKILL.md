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
| Zeus (`profiles/zeus/`) | openai-codex | gpt-5.5 | ✅ Migrado |
| Atena (`profiles/atena/`) | openai-codex | gpt-5.5 | ✅ Migrado |

Modelos auxiliares (compressão, summarização): mantidos em `claude-haiku-4-5` — não migrar, custo é mínimo e o haiku é estável.

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

## Migração completa: todos os agentes para GPT OAuth

### Passo 1 — Login no perfil raiz (uma vez)

```bash
hermes model
# → Selecionar "openai-codex" → device code flow → autorizar no browser
# Tokens salvos em ~/.hermes/auth.json
```

### Passo 2 — Copiar credenciais para cada perfil (Zeus, Atena)

O login via `hermes model` atualiza **apenas o perfil raiz**. Os perfis Zeus/Atena têm `auth.json` próprio e precisam receber as credenciais:

```bash
python3 - <<'EOF'
import json

# Ler credenciais do perfil raiz
with open('/root/.hermes/auth.json') as f:
    root = json.load(f)
codex_creds = root['providers']['openai-codex']

# Copiar para cada perfil
for profile in ['zeus', 'atena']:
    path = f'/root/.hermes/profiles/{profile}/auth.json'
    with open(path) as f:
        d = json.load(f)
    d['providers']['openai-codex'] = codex_creds
    d['active_provider'] = 'openai-codex'
    with open(path, 'w') as f:
        json.dump(d, f, indent=2)
    print(f'{profile}: OK')
EOF
```

### Passo 3 — Atualizar config.yaml de cada perfil

```bash
# Zeus
sed -i 's/provider: anthropic/provider: openai-codex/' /root/.hermes/profiles/zeus/config.yaml
sed -i 's/default: claude-sonnet.*/default: gpt-5.5/' /root/.hermes/profiles/zeus/config.yaml
# Adicionar base_url se não existir (usar patch ao invés de sed para precisão)

# Atena
sed -i 's/provider: anthropic/provider: openai-codex/' /root/.hermes/profiles/atena/config.yaml
sed -i 's/default: claude-sonnet.*/default: gpt-5.5/' /root/.hermes/profiles/atena/config.yaml
```

Formato correto no config.yaml:
```yaml
model:
  default: gpt-5.5
  provider: openai-codex
  base_url: 'https://chatgpt.com/backend-api/codex'
```

### Passo 4 — Modelos auxiliares: MANTER haiku

Os modelos auxiliares (compressão de contexto, summarização, etc.) estão configurados como `claude-haiku-4-5` em múltiplos pontos do config. **Não migrar** — o haiku é barato, estável, e não afeta custo mensal significativamente.

### Passo 5 — Reiniciar gateways

```bash
systemctl restart atena-gateway.service
sleep 5
systemctl restart zeus-gateway.service   # reiniciar Zeus interrompe a sessão atual
sleep 10
systemctl is-active zeus-gateway.service atena-gateway.service
```

**⚠️ Reiniciar Zeus via terminal desconecta a sessão atual** — o gateway para e recomeça, interrompendo qualquer conversa ativa com Zeus. Isso é esperado.

### Verificação final

```bash
grep "provider:\|default:" /root/.hermes/profiles/zeus/config.yaml /root/.hermes/profiles/atena/config.yaml | grep -v "auto\|haiku\|edge\|local"
```

Saída esperada:
```
zeus/config.yaml:  default: gpt-5.5
zeus/config.yaml:  provider: openai-codex
atena/config.yaml:  default: gpt-5.5
atena/config.yaml:  provider: openai-codex
```

---

## Referências

- `references/cost-monitoring-gpt-oauth.md` — abordagem de estimativa de custo pós-migração OAuth (sem Admin API)
- `references/cron-model-pinning.md` — política MGS para pin explícito de modelo/provider em cron jobs após migração para Codex

---

## Política de cron jobs após migração para Codex

Depois que um perfil Hermes é migrado para `openai-codex` + `gpt-5.5`, cron jobs agent-based sem override próprio de `model`/`provider` herdam esse default. Portanto:

1. **Interação principal Zeus/Atena:** manter `openai-codex` + `gpt-5.5`.
2. **Auxiliares Hermes:** manter `claude-haiku-4-5-20251001` salvo exceção explícita.
3. **Cron agent-based:** criar/atualizar com pin explícito em Haiku:
   - `provider: anthropic`
   - `model: claude-haiku-4-5-20251001`
4. **Cron determinístico/watchdog:** preferir `script` + `no_agent: true` para não chamar LLM.
5. **Antes de reativar cron existente:** verificar se `model` ou `provider` estão nulos; se sim, aplicar override antes de `resume/run`.

Regra operacional curta: **cron novo = Haiku por padrão, salvo exceção explícita; script-only = `no_agent: true`.**

---

## Considerações antes de migrar Zeus/Atena

1. **Rate limit da assinatura** — verificar se o plano aguenta volume de tool calls (agentes fazem muitas chamadas seguidas). Testar isolado antes de migrar produção.

2. **Prompt caching** — Claude tem prompt caching que reduz custo em 50-80% para system prompts grandes. GPT via OAuth não tem custo por token, então isso não se aplica — mas o comportamento de tool calling pode ser diferente.

3. **SOUL.md e memories tuned para Claude** — Zeus e Atena têm instruções e memórias otimizadas para Claude. Após migração, pode ser necessário ajustar tom/instruções para GPT.

4. **Skills em PT-BR** — Skills estão escritas para Claude. GPT segue as instruções mas pode ter comportamentos ligeiramente diferentes em edge cases.

5. **Modelo gpt-5.5** — modelo disponível via endpoint Codex. Pode mudar conforme OpenAI atualiza o plano.

---

## Pitfalls

1. **Perfil raiz ≠ perfil do agente** — configurar via `hermes model` no terminal raiz atualiza `~/.hermes/config.yaml` e `~/.hermes/auth.json`, mas NÃO os perfis Zeus/Atena em `profiles/*/config.yaml` e `profiles/*/auth.json`. Os gateways dos agentes usam seus próprios perfis. Sempre copiar credenciais manualmente (Passo 2 acima).

2. **Token expira** — access_token JWT expira (tipicamente em horas/dias). O Hermes faz refresh automático usando o refresh_token. Se o refresh falhar, rodar `hermes model` novamente para re-autenticar e repetir o Passo 2 para os perfis.

3. **`hermes model --status` não existe** — para verificar provider ativo, usar `grep` no config.yaml ou inspecionar auth.json diretamente.

4. **Endpoint Codex ≠ API OpenAI** — algumas ferramentas/integrações que esperam `api.openai.com` não funcionam com o endpoint Codex. O Hermes suporta nativamente via `codex_responses` transport.

5. **Modelos do endpoint Codex não são listáveis via API** — `GET /codex/models` retorna 400, `/backend-api/models` retorna 403. Não é possível listar modelos disponíveis programaticamente. Usar `gpt-5.5` que está disponível no plano $100/mês.

6. **Custo no Hermes aparece como "included"** — o `usage_pricing.py` detecta `openai-codex` e retorna `billing_mode=subscription_included`. O resumo de sessão no Discord vai mostrar "custo: included" em vez de valor monetário. Normal e correto.

7. **Scripts de monitoramento de custo Anthropic ficam obsoletos** — após migração, `monitor-gpt55-oauth-cost.sh` e `track-article-cost.sh` usam estimativa via api_calls, não Anthropic Admin API. Ver `references/cost-monitoring-gpt-oauth.md` para a abordagem atual.

8. **Cron sem pin herda o provider do perfil** — após migrar Zeus/Atena para Codex, qualquer cron agent-based com `model: null` ou `provider: null` passa a herdar `openai-codex` + `gpt-5.5`. Auditar e pinçar explicitamente em Haiku antes de reativar/rodar. Ver `references/cron-model-pinning.md`.
