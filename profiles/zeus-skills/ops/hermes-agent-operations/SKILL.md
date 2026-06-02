---
name: hermes-agent-operations
description: "Umbrella operacional para Hermes Agent no VPS MGS: updates seguros, inspeção/configuração de web tooling, providers/modelos OAuth, políticas de custo, validação de gateways Zeus/Atena e cuidados pós-migração."
tags: [hermes, operations, update, providers, oauth, web-search, web-extract, gateway, zeus, atena, mgs]
related_skills: [discord-ops, log-monitor-discord-alert]
---

# Hermes Agent Operations — MGS Umbrella

Use esta skill para qualquer operação envolvendo Hermes Agent no VPS MGS: update, rollback, configuração, providers/modelos, OAuth, web tooling, gateway Discord, health-checks, migração de runtime e troubleshooting operacional.

Referência rápida adicionada: `references/hermes-staged-update-validation-mgs.md` cobre o workflow MGS de update/restart em fases: pré-check read-only, backup, preservação/compatibilidade de patches locais, validação de gateways/crons/testes e relatório executivo com ressalvas.

## Postura operacional

- Trabalhar sempre contra o estado vivo da instalação; não responder de memória.
- Antes de ação destrutiva ou restart, checar contexto, risco e impacto nos gateways.
- Não vazar tokens/API keys. Reportar provider, item/vault/field e presença/len quando necessário.
- Separar claramente: ferramenta habilitada, backend configurado, credencial presente e backend realmente utilizável.
- Preferir output executivo em PT-BR para Rodolfo: conclusão primeiro, evidências e próximo passo concreto.

## Ambiente MGS conhecido

- Profiles principais: `/root/.hermes/profiles/zeus/`, `/root/.hermes/profiles/atena/` e `/root/.hermes/profiles/ares/`.
- Checkout Hermes: `/root/.hermes/hermes-agent`.
- Gateways systemd: `zeus-gateway.service`, `atena-gateway.service` e `ares-gateway.service`.
- Projeto MGS: `/root/mgs-agent/`.
- Alguns comandos de restart em Zeus podem interromper a sessão atual; planejar janela quando necessário.
- Padrão MGS para próximos restarts de Zeus/Atena/Ares: preferir `/restart` no próprio agente/thread ou restart gracioso via SIGUSR1/Hermes gateway restart, porque drena execuções em andamento e preserva melhor sessão/thread. `systemctl restart` fica como fallback para agente travado/offline, falha do `/restart` ou emergência operacional.
- Nuance validada em teste Zeus 2026-06-02: o restart gracioso preservou a sessão/thread e retomou com o mesmo session_id após nova mensagem do usuário, mas não continuou automaticamente sozinho depois de subir. A resposta final emitida durante o drain pode não aparecer no Discord antes da desconexão. Procedimento prático: após `/restart`, enviar uma mensagem curta tipo `retoma` e validar PID/start/session_id.

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

When Rodolfo says the backup/update is already done, stop recommending an update window and switch directly to post-update verification. See `references/hermes-v15-post-update-validation-2026-05-28.md` for the v15 validation evidence shape and path-migration pitfall.

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

- Pós-update com restart dos gateways MGS: quando o comando roda dentro do próprio Zeus, `systemctl restart zeus-gateway.service ...` pode timeoutar ou deixar Zeus em `deactivating` porque a conversa/tool atual mantém o processo antigo vivo. Não reportar falha sem checar estado vivo. Validar Atena/Ares, agendar finalização externa via `systemd-run` se necessário, depois diferenciar falhas históricas do restart de erros pós-start. Playbook: `references/post-update-gateway-restart-validation.md`.
- Update parcial com `ENOSPC`: se o disco enche durante `hermes update`, não repetir às cegas. Checar HEAD/upstream/behind, limpar backups redundantes mantendo o backup mais recente, reparar dependências (`uv pip install -e '.[all]'`, `npm install`, `ui-tui npm install`) sem reiniciar serviços, compilar arquivos críticos, e só então dar o comando separado de restart. Playbook: `references/hermes-update-enospc-controlled-recovery.md`.
- Pós-update de Discord/thread MGS: não validar apenas com `grep modify_thread`. O patch antigo pode ter sido substituído por rename-on-create determinístico em `plugins/platforms/discord/adapter.py` (`_auto_thread_name_from_message`, `_auto_create_thread`) e auto-add (`_auto_add_parent_channel_members_to_thread`). Validar a capability real: scan por helpers/comentários `PATCH (MGS Digital Corp)`, `py_compile`, serviço ativo, e variáveis `DISCORD_THREAD_AUTO_ADD_USERS` nos profiles/processos vivos de Zeus/Atena/Ares. Se `modify_thread=0` mas esses helpers existem, não reportar “patch perdido” sem checar o novo caminho.
- Após `hermes update`, `systemd` pode mostrar falhas `status=1/FAILURE` durante restart controlado. Diferenciar incidente ativo de histórico: confirmar PIDs atuais, uptime do serviço, memória atual/peak, logs posteriores e se há novo traceback/OOM. Só alertar como loop se houver falhas repetidas depois do novo start.
- Timeout do terminal não prova falha; `hermes update` pode seguir em background. Verificar depois com versão, commits e serviços.
- Se `hermes update` falhar por `ENOSPC`/disco cheio, **não repetir update às cegas**. Primeiro checar `df -h /`, `df -ih /`, maiores diretórios, logs do update, HEAD/origin/behind, `git status`, stashes e serviços. O repo pode já estar em `behind: 0` com patches locais restaurados, enquanto npm/dependências falharam e os gateways ainda rodam PIDs antigos. Liberar espaço (alvo 8–10G livres; backups redundantes de profiles são candidatos comuns), reparar dependências com `uv pip install --python "$repo/venv/bin/python" -e '.[all]'` + `npm install --no-fund --no-audit` (+ `ui-tui` se existir), compilar arquivos críticos, e só então reiniciar/validar gateways. Playbook: `references/hermes-update-enospc-partial-update-recovery.md`.
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

Use quando Rodolfo quiser trocar provider de Zeus/Atena/Ares, usar GPT via assinatura ChatGPT, reduzir custo Anthropic/Claude, autenticar `openai-codex`, validar cron jobs após migração, ou auditar chamadas LLM pagas.

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

### Purge total Anthropic/Claude quando Rodolfo exigir GPT-5.5 para tudo

Quando Rodolfo disser “GPT-5.5 pra tudo”, “zero Anthropic”, “deleta de tudo” ou equivalente, usar o playbook `references/openai-codex-gpt55-all-profiles-purge.md`. Regra operacional: depois de confirmação crítica, limpar **root + profiles + backups/snapshots**, não só `config.yaml`. Validar `providers.anthropic=false`, `credential_pool.anthropic=false`, `active_provider=openai-codex`, auxiliares pinados em `openai-codex/gpt-5.5`, scan de `sk-ant-*` real igual a zero fora do código-fonte/testes/docs upstream, e gateways reconectados.

### Pitfalls de provider/OAuth

- `hermes model --status` não existe; verificar config/auth diretamente.
- Endpoint Codex não lista modelos via API (`/codex/models` pode retornar 400; `/backend-api/models` 403).
- Token expira; refresh deve ser automático, mas falhas exigem novo `hermes model` e recópia para profiles.
- Não manter Claude/Haiku como fallback silencioso após decisão de custo.
- Quando limpar Anthropic/Claude, remover também `credential_pool.anthropic`, root `~/.hermes/auth.json`, root `~/.hermes/.env`, snapshots/backups com credenciais e espelhos versionados em `/root/mgs-agent/profiles/`; só limpar `providers.anthropic` nos profiles é insuficiente.
- Alguns serviços fora do gateway podem continuar chamando Anthropic mesmo depois de migrar Zeus/Atena/Ares.
- OpenHands “funcionando” não basta: se wrapper/trajectory usa `anthropic/claude-*` + API key 1Password, isso é uma falha de custo/governança salvo autorização explícita de Rodolfo. Diagnóstico canônico: `references/atena-openhands-provider-diagnostic.md`.
- Para OpenHands na Atena/Zeus, a política correta é **GPT-5.5/OpenAI-Codex OAuth para tudo por padrão**. Não sugerir “backend não-Anthropic aprovado” genérico, OpenRouter, Haiku ou Claude como workaround. Se OpenHands precisar de compatibilidade com Codex, forçar `openai/gpt-5.5`, usar OAuth do profile sem imprimir token e validar o modelo real no output. Playbook: `references/openhands-gpt55-codex-wrapper.md`.

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
- `references/hermes-update-enospc-partial-update-recovery.md` — recuperar update parcial após `ENOSPC`: liberar espaço, distinguir repo atualizado vs. dependências falhas, reparar npm/uv, compilar e só então reiniciar gateways.
- `references/post-update-gateway-restart-validation.md` — validar update/restart Zeus+Atena+Ares quando Zeus reinicia a si mesmo; finalizer via systemd-run, distinção entre falha histórica de restart e erro ativo pós-start.
- `references/hermes-update-enospc-controlled-recovery.md` — recuperar update parcial após `No space left on device`: inventário/limpeza de backups, reparo de Python/npm sem restart, validação e restart separado.
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
- `references/atena-openhands-provider-diagnostic.md` — diagnosticar OpenHands da Atena: funcionalidade vs. provider/modelo/custo, wrapper e trajectories sem vazar credenciais
- `references/openhands-gpt55-codex-wrapper.md` — padrão MGS para OpenHands com GPT-5.5/OpenAI-Codex OAuth, bloqueio de fallback provider e validação real do runtime model
