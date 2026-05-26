---
name: hermes-agent-operations
description: "Umbrella operacional para Hermes Agent no VPS MGS: updates seguros, inspeção/configuração de web tooling, providers/modelos OAuth, políticas de custo, validação de gateways Zeus/Atena e cuidados pós-migração."
tags: [hermes, operations, update, providers, oauth, web-search, web-extract, gateway, zeus, atena, mgs]
related_skills: [discord-ops, log-monitor-discord-alert]
---

# Hermes Agent Operations — MGS Umbrella

Use esta skill para qualquer operação de Hermes Agent no ambiente MGS: atualizar o Hermes, avaliar release notes, validar gateways, configurar/inspecionar web tooling, trocar providers/modelos, autenticar OpenAI Codex OAuth, auditar custo de LLM ou investigar regressões operacionais de Zeus/Atena.

## Postura operacional

- Trabalhar sempre contra o estado vivo da instalação; não responder de memória.
- Antes de ação destrutiva ou restart, checar contexto, risco e impacto nos gateways.
- Não vazar tokens/API keys. Reportar provider, item/vault/field e presença/len quando necessário.
- Separar claramente: ferramenta habilitada, backend configurado, credencial presente e backend realmente utilizável.
- Preferir output executivo em PT-BR para Rodolfo: conclusão primeiro, evidências e próximo passo concreto.

## Ambiente MGS conhecido

- Profiles principais: `/root/.hermes/profiles/zeus/` e `/root/.hermes/profiles/atena/`.
- Checkout Hermes: `/root/.hermes/hermes-agent`.
- Gateways systemd: `zeus-gateway.service` e `atena-gateway.service`.
- Projeto MGS: `/root/mgs-agent/`.
- Alguns comandos de restart em Zeus podem interromper a sessão atual; planejar janela quando necessário.

## 1. Update seguro do Hermes

Use quando Rodolfo pedir atualização do Hermes ou quando monitor detectar nova versão.

### Pré-check mínimo

```bash
hermes --version
repo=/root/.hermes/hermes-agent
git -C "$repo" fetch --quiet origin main
git -C "$repo" rev-parse --short HEAD
git -C "$repo" rev-parse --short origin/main
git -C "$repo" rev-list --count HEAD..origin/main
systemctl is-active zeus-gateway.service atena-gateway.service
hermes cron list 2>/dev/null || true
git -C "$repo" status --short
```

Para major updates ou deltas grandes, fazer backup dos profiles:

```bash
tar -czf /root/hermes-profiles-backup-$(date +%Y%m%d).tar.gz /root/.hermes/profiles/
ls -lh /root/hermes-profiles-backup-*.tar.gz
```

Erro `file changed as we read it` durante tar pode ocorrer por escrita de agente ativo; normalmente o arquivo ainda é gerado.

### Review antes de pedir aprovação

Quando a pergunta for “vale atualizar?”, fazer análise read-only antes de recomendar. Ver `references/hermes-update-pre-update-review.md`. Reportar:

- commits atrás e delta de arquivos/linhas;
- features/fixes/docs/manutenção por contagem aproximada;
- melhorias relevantes para MGS;
- risco de conflito com patches locais;
- recomendação: atualizar agora, deferir ou atualizar em janela controlada.

### Execução

```bash
hermes update 2>&1
```

Se o guardrail bloquear por reiniciar gateways/matar sessões, não tentar burlar nem repetir em loop. Reportar o backup/checks já feitos e pedir que Rodolfo rode `hermes update` manualmente no shell; depois continuar a validação com o output dele.

### Validação pós-update obrigatória

Só reportar sucesso depois de confirmar upstream, serviços, patches/smokes e testes alvo:

```bash
repo=/root/.hermes/hermes-agent
sleep 10
hermes --version 2>&1 | sed -n '1,25p'
git -C "$repo" fetch --quiet origin main
git -C "$repo" rev-parse --short HEAD
git -C "$repo" rev-parse --short origin/main
git -C "$repo" rev-list --count HEAD..origin/main
systemctl is-active zeus-gateway.service atena-gateway.service
git -C "$repo" status --short
git -C "$repo" diff --stat
py="$repo/venv/bin/python"
"$py" -m py_compile "$repo/gateway/platforms/discord.py" "$repo/gateway/run.py" "$repo/tools/discord_tool.py"
```

Checklist/suite detalhada: `references/hermes-update-post-update-validation.md`.

### Pitfalls de update

- Timeout do terminal não prova falha; `hermes update` pode seguir em background. Verificar depois com versão, commits e serviços.
- Se `hermes update` oficial travar/timeoutar sem output, **não repetir em loop**. Rodar verificação de estado; se ainda estiver atrasado, executar atualização manual controlada: backup já feito → `git stash push -u` dos patches locais → `git fetch origin main` → `git pull --ff-only origin main` → restaurar stash/patch local → limpar `__pycache__` → reinstalar dependências (`venv/bin/python -m pip install -e '.[all]'`) → `npm install`/build web quando aplicável → remover `.update_check` dos profiles → validar commit HEAD/origin, `hermes --version`, `py_compile` e serviços.
- Antes de update manual com patch local MGS, salvar `git diff` em backup e testar `git apply --check` contra `origin/main` em worktree temporário. Se aplicar limpo, o risco é controlado; se não aplicar, portar patch antes de atualizar.
- Em updates de sistema junto com Hermes, tratar reboot como Critical Subset: atualizar pacotes e reiniciar serviços quando necessário, mas pedir confirmação separada para `reboot` do VPS.
- Para NPM global, priorizar CLIs operacionais (`@openai/codex`, `agent-browser`, `@anthropic-ai/claude-code`, `corepack`). Não forçar self-update major do `npm` se ele é fornecido pelo pacote NodeSource/OS e falha internamente; reportar como pendência separada em vez de substituir manualmente `/usr/lib/node_modules/npm` sem necessidade.
- Se Rodolfo confirmar explicitamente que quer fechar a pendência do `npm` mesmo assim, tratar como operação crítica por modificar `/usr/lib`: backup tar + diretório rollback, baixar tarball oficial do registry, verificar `shasum`, substituir `/usr/lib/node_modules/npm`, validar `npm -v`, `npm exec`, `npm outdated -g` e gateways. Playbook completo: `references/mgs-full-maintenance-validation-and-npm-manual-update.md`.
- Em v0.13.0+, o antigo patch local MGS `busy_input_mode: queue` foi integrado upstream. Se `grep "PATCH (MGS Digital Corp)" gateway/run.py` retornar vazio, isso é esperado; não reaplicar patch antigo.
- `hermes --version` pode manter a mesma tag quando só houve commits sem nova release; “up to date” e commit HEAD/origin são mais relevantes.
- Após restart manual, journal pode mostrar `status=1/FAILURE` para PIDs antigos encerrados; não reportar incidente se PIDs novos estão `active`, sem traceback/OOM posterior.
- Se upstream migrar o Discord adapter de `gateway/platforms/discord.py` para `plugins/platforms/discord/adapter.py`, qualquer patch local MGS em Discord falha no apply direto com “file not found”. Antes de recomendar update, gerar `git diff`, testar apply contra `origin/main`; se falhar por path migration, reescrever o path do patch para `plugins/platforms/discord/adapter.py` em worktree temporário e rodar `git apply --check` + `py_compile`. Se o port check passar, o update é viável mas exige janela controlada: update, portar patch, compilar, restart Zeus/Atena e testar thread/auto-add/send_message.

## 2. Web tooling nativo, search/extract e MCP

Use quando a pergunta envolver busca web, fetch/extract sem Playwright, MCP search servers, toolsets ativos, ou benchmark de providers para Atena/Zeus.

### Discovery workflow

```bash
# comandos e help atuais
hermes tools --help
hermes mcp --help
hermes --version

# toolsets e MCP por profile
hermes -p zeus tools list
hermes -p atena tools list
hermes -p zeus mcp list
hermes -p atena mcp list
```

Inspecionar configs sem vazar segredos:

- `/root/.hermes/profiles/zeus/config.yaml`
- `/root/.hermes/profiles/atena/config.yaml`

Campos relevantes: `toolsets`, `agent.disabled_toolsets`, `web.backend`, `web.search_backend`, `web.extract_backend`.

### Matriz de providers a validar no código vivo

| Provider | Search | Extract/fetch | Requisito típico |
|---|---:|---:|---|
| Firecrawl | sim | sim | `FIRECRAWL_API_KEY` ou gateway Nous |
| Parallel | sim | sim | `PARALLEL_API_KEY` |
| Tavily | sim | sim | `TAVILY_API_KEY` |
| Exa | sim | sim | `EXA_API_KEY` |
| SearXNG | sim | não | `SEARXNG_URL` |
| Brave-free | sim | não | `BRAVE_SEARCH_API_KEY` |
| DDGS | sim | não | pacote `ddgs` |

Providers só de search não substituem extração de conteúdo; combinar com `web_extract`, HTTP direto/Python/curl ou browser conforme a página.

### Brave Search MGS

Item conhecido no 1Password:

```text
Vault default: ${OP_DEFAULT_VAULT:-MGS Conteúdo}
Item: Brave Search API - MGS
Field label: api key
Required: --reveal
```

Pitfalls: `--fields api_key` está errado; usar `--fields "api key"`. Sem `--reveal`, 1Password retorna placeholder. Não imprimir a key.

Probe determinístico:

```bash
bash /root/.hermes/profiles/zeus/skills/ops/hermes-agent-operations/scripts/test-brave-search-mgs.sh \
  "AIB Visa Gold credit card UK official"
```

Ver detalhes: `references/hermes-web-brave-search-mgs-2026-05-17.md` e `references/hermes-web-tooling-2026-05-17.md`.

### Recomendação MGS padrão

| Necessidade | Caminho preferido |
|---|---|
| Descobrir URL oficial/source | `web_search` + Brave primeiro |
| Descobrir imagens candidatas | endpoint Brave Images direto |
| Fetch de URL estática | Python/curl/HTTP direto quando suficiente |
| Extração estruturada | `web_extract` com provider de extract |
| JS-heavy/visual | Browser/Playwright |
| Fallback durante benchmark | fluxo Playwright/Bing atual |

## 3. Providers, modelos e OpenAI Codex OAuth

Use quando Rodolfo quiser trocar provider de Zeus/Atena, usar GPT via assinatura ChatGPT, reduzir custo Anthropic/Claude, autenticar `openai-codex`, validar cron jobs após migração, ou auditar chamadas LLM pagas.

### Fatos essenciais

- Endpoint Codex: `https://chatgpt.com/backend-api/codex` (não `api.openai.com`).
- Auth: OAuth device-code via assinatura ChatGPT; tokens em `auth.json`.
- Billing Hermes: `openai-codex` deve aparecer como `subscription_included`/included, sem pay-per-token.
- Modelo MGS atual conhecido: `gpt-5.5` via plano ChatGPT.
- Política operacional MGS: zero Anthropic/Claude API pay-per-token por padrão, salvo autorização explícita de Rodolfo.

### Login inicial

```bash
hermes model
# selecionar openai-codex, abrir URL, inserir device code e autorizar
```

O login no perfil raiz atualiza `~/.hermes/auth.json`; profiles Zeus/Atena usam seus próprios `auth.json` e precisam receber as credenciais.

### Copiar credenciais para Zeus/Atena

```bash
python3 - <<'EOF'
import json
with open('/root/.hermes/auth.json') as f:
    root = json.load(f)
codex_creds = root['providers']['openai-codex']
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

Formato esperado em cada `config.yaml`:

```yaml
model:
  default: gpt-5.5
  provider: openai-codex
  base_url: 'https://chatgpt.com/backend-api/codex'
```

### Verificação sem vazar tokens

```bash
python3 - <<'EOF'
import json
for path in ['/root/.hermes/auth.json', '/root/.hermes/profiles/zeus/auth.json', '/root/.hermes/profiles/atena/auth.json']:
    print(path)
    with open(path) as f:
        d=json.load(f)
    p=d.get('providers',{}).get('openai-codex',{})
    tokens=p.get('tokens',{}) if isinstance(p,dict) else {}
    print('  active_provider:', d.get('active_provider'))
    print('  auth_mode:', p.get('auth_mode') if isinstance(p,dict) else None)
    print('  access_token_len:', len(tokens.get('access_token','')))
    print('  refresh_token_present:', bool(tokens.get('refresh_token')))
EOF

grep "provider:\|default:" /root/.hermes/profiles/zeus/config.yaml /root/.hermes/profiles/atena/config.yaml | grep -v "auto\|haiku\|edge\|local"
```

### Cron jobs e custo após migração

- Cron agent-based sem override herda provider/model do perfil. Após migração para Codex, jobs com `model/provider: null` passam a herdar `openai-codex` + `gpt-5.5`.
- Preferir `script` + `no_agent: true` para watchdogs determinísticos.
- Antes de reativar cron antigo, auditar model/provider e evitar fallback Anthropic acidental.
- Procurar `ANTHROPIC_API_KEY`, `api.anthropic.com`, `anthropic.Anthropic`, `claude-*`, `provider: anthropic` em serviços/repos ativos.

Referências: `references/openai-codex-cron-model-pinning.md`, `references/openai-codex-anthropic-api-decommission.md`, `references/openai-codex-cost-monitoring-gpt-oauth.md`.

### Pitfalls de provider/OAuth

- `hermes model --status` não existe; verificar config/auth diretamente.
- Endpoint Codex não lista modelos via API (`/codex/models` pode retornar 400; `/backend-api/models` 403).
- Token expira; refresh deve ser automático, mas falhas exigem novo `hermes model` e recópia para profiles.
- Não manter Claude/Haiku como fallback silencioso após decisão de custo.
- Alguns serviços fora do gateway podem continuar chamando Anthropic mesmo depois de migrar Zeus/Atena.

## 4. Reporting templates

### Resposta executiva para tooling web

```text
Pergunta                                      Resposta
──────────────────────────────────────────── ─────────────────────────────
1. Tem web_search nativo?                    Sim/Não + tool name
2. Tem web_fetch nativo?                     Sim/Não + web_extract mapping
3. MCP de busca configurado?                 Sim/Não + profile results
4. Versão trouxe capability nova?            Versão + delta conciso
5. Toolsets ativos Zeus/Atena                tabela abaixo
```

Depois: tabela de toolsets, tabela de backends, recomendação direta e `Próximo passo pendente:`.

### Resposta executiva para update

```text
Resumo: atualizar agora / deferir / janela controlada.
Evidências: commits atrás, highlights, risco local, backup/checks.
Impacto: gateways offline ~1-2 min; Zeus pode interromper sessão ativa.
Próximo passo: comando exato ou validação pendente.
```

## 5. New MGS agent bootstrap

When Rodolfo asks to start a new MGS agent/profile (Ares or future agents), use `references/mgs-new-agent-bootstrap.md`. Core rule: clone profile/config as needed, but immediately blank any inherited Discord bot token; do not create/enable the systemd gateway until the agent has its own dedicated bot token and Rodolfo confirms the Critical Subset system-file write.

## 6. References and support files

Para manutenção de VPS/update com backup, recuperação manual de npm quando self-update quebra, e política de retenção/limpeza de backups, ver `references/vps-update-npm-backup-retention-2026-05-24.md`.

Esta umbrella absorveu as antigas skills especializadas abaixo. Conteúdo detalhado e histórico foi preservado nos arquivos de suporte:

- `references/hermes-update-original-skill.md`
- `references/hermes-update-post-update-validation.md`
- `references/hermes-update-pre-update-review.md`
- `references/hermes-update-2026-05-16-mgs-relevance.md`
- `references/mgs-full-maintenance-validation-and-npm-manual-update.md` — full post-maintenance validation checklist + safe manual npm replacement/rollback pattern
- `references/hermes-web-tooling-original-skill.md`
- `references/hermes-web-tooling-2026-05-17.md`
- `references/hermes-web-brave-search-mgs-2026-05-17.md`
- `scripts/test-brave-search-mgs.sh`
- `references/openai-codex-oauth-original-skill.md`
- `references/openai-codex-cron-model-pinning.md`
- `references/openai-codex-anthropic-api-decommission.md`
- `references/openai-codex-cost-monitoring-gpt-oauth.md`
