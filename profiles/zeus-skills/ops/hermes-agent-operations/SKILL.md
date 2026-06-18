---
name: hermes-agent-operations
description: "Umbrella operacional para Hermes Agent no VPS MGS: updates seguros, inspeção/configuração de web tooling, providers/modelos OAuth, políticas de custo, validação de gateways Zeus/Atena e cuidados pós-migração."
tags: [hermes, operations, update, providers, oauth, web-search, web-extract, gateway, zeus, atena, mgs, memory, honcho]
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
- Para bloqueios de referência YouTube/Shorts em VPS, não recomendar Browserbase/proxy pago como primeira resposta se o uso for ocasional. Validar primeiro o caminho sem custo extra: Chromium persistente, sessão/cookies persistentes uma vez, ou vídeo anexado. Browserbase/residential proxy só entra se o volume recorrente justificar custo operacional.

## Ambiente MGS conhecido

- Profiles principais: `/root/.hermes/profiles/zeus/`, `/root/.hermes/profiles/atena/` e `/root/.hermes/profiles/ares/`.
- Checkout Hermes: `/root/.hermes/hermes-agent`.
- Gateways systemd: `zeus-gateway.service`, `atena-gateway.service` e `ares-gateway.service`.
- Projeto MGS: `/root/mgs-agent/`.
- Alguns comandos de restart em Zeus podem interromper a sessão atual; planejar janela quando necessário.
- Padrão MGS para próximos restarts de Zeus/Atena/Ares: preferir `/restart` no próprio agente/thread ou restart gracioso via SIGUSR1/Hermes gateway restart, porque drena execuções em andamento e preserva melhor sessão/thread. `systemctl restart` fica como fallback para agente travado/offline, falha do `/restart` ou emergência operacional.
- Nuance validada em teste Zeus 2026-06-02: antes do patch MGS, o restart gracioso preservava a sessão/thread e retomava com o mesmo session_id após nova mensagem do usuário, mas não continuava automaticamente sozinho depois de subir. A resposta final emitida durante o drain podia não aparecer no Discord antes da desconexão.
- Patch local MGS aplicado em `gateway/run.py`: em restart planejado, manter `resume_pending` mesmo quando o drain completa limpo para sessões ativas no momento do restart. Objetivo: no startup, `_schedule_resume_pending_sessions()` sintetiza um evento interno na mesma thread e Zeus/Atena/Ares continuam sem Rodolfo precisar escrever `retoma`. Validar com `py_compile` + `tests/gateway/test_gateway_shutdown.py::test_planned_restart_keeps_resume_pending_after_graceful_drain` + `tests/gateway/test_restart_resume_pending.py`.

## 1. Update seguro do Hermes

Use quando Rodolfo pedir atualização do Hermes ou quando monitor detectar nova versão.

**Regra permanente MGS aprovada por Rodolfo:** nenhum update Hermes é considerado concluído sem backup + diff/snapshot pré-update + comparação pós-update + guard de patches/invariantes MGS + validação runtime real. O playbook canônico é `references/hermes-controlled-update-rule-mgs.md` e o script padrão é `/root/mgs-agent/scripts/run-hermes-update-controlled.sh`.

Comandos padrão:

```bash
# Pré-check/dry-run sem mutar o checkout vivo
PRECHECK_ONLY=1 /root/mgs-agent/scripts/run-hermes-update-controlled.sh

# Update controlado sem reiniciar gateways
RESTART_GATEWAYS=0 /root/mgs-agent/scripts/run-hermes-update-controlled.sh

# Update controlado com restart pós-validação
RESTART_GATEWAYS=1 /root/mgs-agent/scripts/run-hermes-update-controlled.sh
```

Falha fechada: se backup, patch guard, py_compile, comparação pós-update ou invariantes críticos falharem, não declarar sucesso e não reiniciar gateways em produção sem portar/corrigir manualmente. O script também falha antes de mutar se o dry-run de patches canônicos contra `origin/main` detectar drift; `ALLOW_PATCH_DRIFT=1` só pode ser usado após revisão/port manual explícita. Em updates com restart, o script deve gravar `final-report.md` antes do restart. Entrega Discord deve ser explícita por execução: nunca hardcodar thread antiga nem defaultar `SEND_DISCORD_REPORT=1`; passar o destino atual explicitamente ou manter artifacts locais e resumir na thread ativa. Se um finalizer detached/file-only for usado, Zeus ainda precisa providenciar follow-up limpo de validação no thread de Rodolfo; não prometer “vou retomar/validar depois” sem callback/delivery concreto. Se Zeus voltar por checkpoint de recuperação, a primeira resposta deve ler esse artefato e entregar/confirmar o relatório final, não apenas uma mensagem curta de recuperação. Detalhe: `references/hermes-update-discord-report-and-followup-2026-06-17.md`.

**Correção operacional após incidentes 2026-06-15/2026-06-17:** backup sozinho não basta, e comparar só nomes de arquivos também não basta. O update só pode ser chamado de concluído após comparar a superfície crítica viva contra o backup/pre-state e gerar evidência explícita: `post-profiles-sanitized.txt`, `post-backup-live-profile-compare.txt`, `post-readonly-invariants.txt` e comparação de markers/funções/strings introduzidos por `pre-local-diff.patch` / `pre-local-diff-cached.patch`. Escopo mínimo: `config.yaml`, `SOUL.md` e `auth.json` sanitizado para Zeus/Atena/Ares/Hera, além dos invariantes MGS em Hermes. Depois do update, o fluxo deve restaurar os diffs locais pré-update e falhar fechado se qualquer patch local não restaurar limpo ou se algum marker local sumir sem evidência de incorporação upstream equivalente. Se a comparação foi feita retroativamente, dizer que foi retroativa; não apresentar como se tivesse sido feita no fluxo original. Detalhes: `references/hermes-controlled-update-report-and-backup-compare-2026-06-15.md` e `references/hermes-local-patch-surface-guard-2026-06-17.md`.

**Git hygiene obrigatório antes de gerar artifacts:** update reports/backups não são código. Antes de rodar ou validar fluxo que cria `/root/mgs-agent/reports/hermes-updates/` ou `*.tar.gz`, garantir `.gitignore` cobrindo esses paths e pausar `mgs-autocommit.service` se o fluxo ainda está em desenvolvimento/teste. Se artifacts pesados/sensíveis entrarem no Git, tratar como incidente: parar autocommit, resetar para commit limpo, force-push com lease exato só após aprovação explícita de Rodolfo, `git reflog expire` + `git gc --prune=now`, validar disco e reativar autocommit. Detalhe: `references/hermes-controlled-update-git-hygiene-2026-06-15.md`.

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

Só reportar sucesso depois de confirmar upstream, serviços, patches/smokes e testes alvo.

**Regra MGS pós-update:** toda conclusão de update deve incluir automaticamente, sem Rodolfo precisar pedir: (1) se deu tudo certo ou pendências, (2) status vivo dos gateways, (3) validação OpenAI Codex auth em root + Zeus/Atena/Ares sem imprimir tokens, (4) backup criado/apagado e disco, (5) delta desde a versão/commit anterior — commits aplicados, highlights por impacto MGS, e o que não mudou. Também incluir inventário de backups/reports gerados e recomendação de limpeza segura quando o disco passar de ~75% ou quando o update criar múltiplos tarballs >1GB; manter o backup canônico pré-update e patches pequenos, e preferir apagar backups redundantes de pré-check/pós-validação antes de mexer em safety backups.

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

Quando Rodolfo pedir uma **revisão geral pós-update** (funcionalidades, crons, patches locais, padrões dos agentes e novidades), usar também `references/hermes-post-update-full-system-review.md`. Esse playbook amplia a validação para crons MGS/Hermes, logs, smoke tests reais (Brave/TTS/Hera image_gen), comparação live config vs. mirror/snapshot, política GPT-5.5/OpenAI-Codex e resumo de release notes/Ubuntu security updates.

### Pitfalls de update

- Quando Hermes mostrar profiles com `_config_version` antigo após update, usar migração controlada por profile: backup pequeno de `config.yaml`/`SOUL.md`/`auth.json`, `hermes -p <profile> config migrate`, validação provider/model/auth/gateways/patch guard, sync dos mirrors em `/root/mgs-agent/profiles/`, restart gracioso só dos gateways migrados e audit log. Playbook: `references/hermes-profile-config-migration-mgs.md`.
- Pós-update com restart dos gateways MGS: quando o comando roda dentro do próprio Zeus, `systemctl restart zeus-gateway.service ...` pode timeoutar ou deixar Zeus em `deactivating` porque a conversa/tool atual mantém o processo antigo vivo. Não reportar falha sem checar estado vivo. Validar Atena/Ares, agendar finalização externa via `systemd-run` se necessário, depois diferenciar falhas históricas do restart de erros pós-start. Playbook: `references/post-update-gateway-restart-validation.md`.
- **Anti-loop de restart multiagente:** não disparar repetidas tentativas de restart Zeus/Atena/Ares/Hera a partir da própria conversa do Zeus em retomada. Use um único finalizer externo, idempotente e com lock; Zeus por último; depois pare e leia o log antes de qualquer nova tentativa. Antes de novo restart após retomada, checar audit/log/HEAD/status para não reprocessar o mesmo `Execute`. Em revisão pós-recovery, comparar root crontab contra `/root/mgs-agent/docs/CRONS.md`, mas tratar cron/monitor comentado como **decisão operacional possível**, não falha automática: reportar drift e pedir confirmação antes de religar/desarmar. Se Rodolfo ou outro operador corrigiu backups/crons fora do Zeus durante o incidente, revalidar o estado vivo antes de repetir números de relatório anterior. Ver `references/hermes-restart-loop-and-cron-drift-2026-06-11.md` e `references/hermes-post-update-full-system-review.md`.
- **Pós-update com banner/units/alertas ambíguos:** se Git mostra `HEAD == origin/main` e `behind=0`, mas `hermes --version` ainda diz “Update available”, limpar `.update_check` de root/profiles e validar de novo. Se finalizer/transient unit ficou `failed` por reiniciar o próprio conjunto de gateways, não repetir update/restart: inspecionar estado vivo, rodar patch guard, resetar failed unit histórico e reportar. Em scripts futuros, usar `systemctl restart --no-block` para gateways. Se Rodolfo reclamar que não recebeu alertas, validar cron daemon + journal + mtimes/logs de monitores e explicar que silêncio pode ser “nenhuma condição de alerta”, não falha. Detalhe: `references/hermes-update-2026-06-12-stale-cache-cron-alerts.md`.
- Update parcial com `ENOSPC`: se o disco enche durante `hermes update`, não repetir às cegas. Checar HEAD/upstream/behind, limpar backups redundantes mantendo o backup mais recente, reparar dependências (`uv pip install -e '.[all]'`, `npm install`, `ui-tui npm install`) sem reiniciar serviços, compilar arquivos críticos, e só então dar o comando separado de restart. Playbook: `references/hermes-update-enospc-controlled-recovery.md`.
- Após `hermes update`, `systemd` pode mostrar falhas `status=1/FAILURE` durante restart controlado. Diferenciar incidente ativo de histórico: confirmar PIDs atuais, uptime do serviço, memória atual/peak, logs posteriores e se há novo traceback/OOM. Só alertar como loop se houver falhas repetidas depois do novo start.
- Timeout do terminal não prova falha; `hermes update` pode seguir em background. Verificar depois com versão, commits e serviços.
- Se `hermes update` falhar por `ENOSPC`/disco cheio, **não repetir update às cegas**. Primeiro checar `df -h /`, `df -ih /`, maiores diretórios, logs do update, HEAD/origin/behind, `git status`, stashes e serviços. O repo pode já estar em `behind: 0` com patches locais restaurados, enquanto npm/dependências falharam e os gateways ainda rodam PIDs antigos. Liberar espaço (alvo 8–10G livres; backups redundantes de profiles são candidatos comuns), reparar dependências com `uv pip install --python "$repo/venv/bin/python" -e '.[all]'` + `npm install --no-fund --no-audit` (+ `ui-tui` se existir), compilar arquivos críticos, e só então reiniciar/validar gateways. Playbook: `references/hermes-update-enospc-partial-update-recovery.md`.
- If `hermes update` official travar/timeoutar sem output, **não repetir em loop**. Rodar verificação de estado; se ainda estiver atrasado, executar atualização manual controlada: backup já feito → `git stash push -u` dos patches locais → `git fetch origin main` → `git pull --ff-only origin main` → restaurar stash/patch local → limpar `__pycache__` → reinstalar dependências (`venv/bin/python -m pip install -e '.[all]'`) → `npm install`/build web quando aplicável → remover `.update_check` dos profiles → validar commit HEAD/origin, `hermes --version`, `py_compile` e serviços.
- Ao reiniciar Zeus a partir da própria thread com auto-retomada ativa, **não reexecutar a mesma ordem `Execute` sem checar idempotência**. Antes de qualquer novo restart após retomada, consultar `events-audit.jsonl`, `/root/mgs-agent/logs/mgs-direct-hermes-restart-latest.log`, `systemctl show` e o HEAD atual; se já há `hermes_direct_*completed` para o mesmo pedido/HEAD e gateways estão ativos, parar e reportar. Sem esse guard, a retomada da mesma mensagem pode virar loop de restart: Zeus relê `Execute`, agenda novo restart, derruba a si mesmo e repete.
- Quando a ordem for **atualizar sem restart automático**, não usar o caminho oficial `hermes update` como execução principal porque ele auto-reinicia gateways no final. Usar o playbook `references/hermes-manual-no-restart-update-patch-drift.md`: backup + salvar `git diff`, `git reset --hard`, `git pull --ff-only`, reaplicar/validar patches MGS, reinstalar deps/builds, limpar `.update_check`, validar e só então pedir autorização separada para restart gracioso.
- Antes de update manual com patch local MGS, salvar `git diff` em backup e testar `git apply --check` contra `origin/main` em worktree temporário. Se aplicar limpo, o risco é controlado; se não aplicar, portar patch antes de atualizar. Se `git apply --reverse --check` false-falhar porque um patch composto já está presente com contexto driftado, validar por invariantes + `py_compile` em vez de tratar como ausência de patch.
- Patches locais críticos MGS devem ser preservados por `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh`. Esse guard aplica/valida os patches canônicos em `/root/mgs-agent/patches/hermes/`, compila `plugins/platforms/discord/adapter.py` + `gateway/run.py` + `gateway/platforms/base.py`, e falha se invariants como `_auto_thread_name_from_message`, `DISCORD_THREAD_AUTO_ADD_USERS`, `Auto-thread member sync`, planned restart auto-resume, author suffix, anti-loop/Codex noise, local-file auto-attach gate ou Discord `delete_message` sumirem. O script controlado `/root/mgs-agent/scripts/run-hermes-update-controlled.sh` chama esse guard após update e também deve restaurar/validar `pre-local-diff.patch` + `pre-local-diff-cached.patch`; file-level compare não basta. Antes de mutar o checkout em update futuro, validar se o diff local vivo aplicaria em `origin/main` — se não aplicar, falhar fechado e exigir port manual. O repo Hermes também tem hook local `.git/hooks/post-merge` chamando o guard; se update upstream sobrescrever/resetar algo, o merge falha ou reaplica antes de restart. Há também watchdog Hermes cron `44671121f3cc` (`Hermes MGS patch watchdog`) a cada 6h, script-only/silencioso em sucesso, alertando a origem se o guard falhar. Detalhe da correção pós-incidente: `references/hermes-update-local-patch-surface-fail-closed-2026-06-17.md`.
- Pitfall pós-update validado: patch existir em `/root/mgs-agent/patches/hermes/` **não significa** que está protegido. Todo patch local novo que altera runtime Hermes precisa ser promovido para a lista canônica tanto em `ensure-hermes-mgs-patches.sh` quanto no precheck de `/root/mgs-agent/scripts/run-hermes-update-controlled.sh`, com invariantes específicos. Exemplo: `discord-thread-title-author-suffix.patch` podia aplicar limpo após o update, mas ficou ausente do runtime porque não estava no guard; o update validou patches antigos e deixou passar a regressão. Em auditoria pós-update, além de rodar o guard, comparar todos os `.patch` relevantes: `git apply --reverse --check` = aplicado, `git apply --check` = ausente mas reaplicável, falha = drift/corrompido/upstream absorvido. Reportar qualquer `can_apply` como patch local perdido, não como OK.
- Em update Hermes MGS, tratar **Zeus + Atena + Ares** como conjunto afetado se os três gateways estiverem ativos. O script controlado pode reiniciar só Zeus/Atena dependendo da versão; validar/reiniciar Ares separadamente ou atualizar o script antes de reportar sucesso. Ver `references/hermes-update-2026-06-04-all-agents-test-env.md`.
- Ao rodar pytest pós-update, executar a partir de `/root/.hermes/hermes-agent` ou usar `workdir` nesse repo. Testes `tests/gateway/...` falham como “file not found” se lançados de `/root/mgs-agent`. Em shell vivo do gateway, isolar/limpar variáveis `DISCORD_*` de produção quando testes upstream-ish dependem de defaults; preserve/assert apenas invariantes MGS. Se um nodeid antigo não existir mais, rode `pytest --collect-only -q` ou execute o arquivo alvo inteiro antes de concluir falha. Se patches locais MGS mudaram intencionalmente o comportamento, alinhe os testes locais à política MGS e então valide. Exemplo 2026-06-09: `discord.free_response_channels` não força inline; `DISCORD_NO_THREAD_CHANNELS` é o controle inline, e channel backfill deve carregar cabeçalho read-only/non-actionable. Ver `references/hermes-update-2026-06-04-all-agents-test-env.md` e `references/hermes-maintenance-2026-06-09-system-and-test-drift.md`.
- Em updates de sistema junto com Hermes, tratar reboot como Critical Subset: atualizar pacotes e reiniciar serviços quando necessário, mas pedir confirmação separada para `reboot` do VPS.
- Quando o usuário pedir “confere tudo” depois de update, não responder só com `active`/`version`. Fazer revisão em camadas: serviços, crons root + Hermes cron, logs recentes, patch guard + testes alvo, configs/padrões dos profiles, auth Codex sanitizado, smoke tests funcionais e delta de release notes. Referência: `references/hermes-post-update-full-system-review.md`.
- Se Hermes já estiver em `HEAD == origin/main`/`behind 0`, não encerrar a manutenção automaticamente: ainda verificar `apt list --upgradable` e `npm outdated -g --depth=0`, atualizar Node/npm/Codex/Corepack e pacotes Ubuntu quando aplicável, e validar gateways/patches/auth. Se `hermes update` for bloqueado pelo guardrail por reiniciar gateways, não repetir nem tentar burlar; validar o estado vivo do repo e seguir com o caminho não-Hermes. Referência: `references/hermes-maintenance-2026-06-09-system-and-test-drift.md`.
- Para NPM global, priorizar CLIs operacionais (`@openai/codex`, `agent-browser`, `corepack`). Não atualizar `@anthropic-ai/claude-code` por padrão na MGS: política operacional é zero Claude/Anthropic salvo autorização explícita do Rodolfo. Não forçar self-update major do `npm` se ele é fornecido pelo pacote NodeSource/OS e falha internamente; reportar como pendência separada em vez de substituir manualmente `/usr/lib/node_modules/npm` sem necessidade.
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

## 4. Image generation / OpenAI-Codex OAuth

Use quando um agente MGS, especialmente Hera/Creative Ops, já conversa em `gpt-5.5` via `openai-codex`, mas falha ao gerar imagem ou pede `OPENAI_API_KEY`/`FAL_KEY`. Também use em revisões gerais tipo “confere tudo” para validar que o perfil esperado para imagem (Hera) consegue gerar um arquivo real.

Para rollout Grok/xAI com OAuth SuperGrok em Creative Ops, mantendo GPT e Grok disponíveis por pedido natural (“faz com GPT”, “faz com Grok”, “faz nos dois”), use `references/grok-xai-oauth-creative-media-rollout-2026-06-16.md`. Regra central: não trocar automaticamente o provider de imagem padrão da Hera se o objetivo é ter GPT + Grok lado a lado; manter `image_gen.provider: openai-codex` para GPT e usar wrapper explícito/`video_gen.provider: xai` para Grok imagem/vídeo/avatar.

Validação prática preferida para smoke test de imagem: depois do `hermes -p hera -t image_gen ...` retornar um caminho, verificar arquivo com `stat` e dimensões via Python/Pillow (`Image.open(path).width/height/format`). Não depender de utilitários opcionais como `file`; a evidência suficiente é path existente, tamanho >0 e dimensões/formato válidos.

Regra MGS de papel: geração de criativos/imagens é responsabilidade da Hera. Zeus é GM/admin e não precisa de `image_gen`; ausência de `image_gen` no Zeus é estado esperado, não falha funcional. Só configurar Zeus para imagem se Rodolfo pedir explicitamente que Zeus passe a gerar imagem.

Não rodar smoke test de `image_generate` no perfil Zeus por padrão: isso aciona o fallback FAL sem chave, registra erro esperado nos logs e gera ruído de diagnóstico. Para validar imagem, usar Hera (`hermes -p hera -t image_gen ...`) ou apenas verificar a config se o objetivo for revisar Zeus.

Regra principal: **chat/raciocínio e geração de imagem são configurações separadas**. `model.provider: openai-codex` não seleciona automaticamente o backend de imagem. Se `image_gen.provider` estiver ausente, o Hermes mantém fallback histórico para FAL mesmo com plugin `openai-codex` registrado.

Config MGS recomendada para Hera:

```yaml
image_gen:
  provider: openai-codex
  model: gpt-image-2-medium
  openai-codex:
    model: gpt-image-2-medium
```

Depois de alterar, reiniciar/recarregar o gateway e fazer teste real com o toolset de imagem, por exemplo:

```bash
hermes -p hera -t image_gen -z "Teste interno: use image_generate para gerar uma imagem quadrada simples. Responda apenas com o caminho do arquivo gerado ou o erro."
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
   - Hera owns creative production; enable `image_gen`/`video_gen` for Grok production.
   - Ares can consume/search/iterate campaign creatives but does not become Creative Ops owner.
   - Zeus may enable for audit/smoke tests, not daily creative work.
   - Atena stays out of generic Grok creative production unless explicitly approved.
3. Enable `video_gen` per profile/platform; it is disabled by default.
4. Run real smoke tests before declaring production-ready: one image, one text-to-video, one avatar/reference-to-video using an approved test image.
5. Log requester/profile/provider/model/duration/resolution/output/estimated cost and enforce budget guardrails before broad team usage.
6. For real-person avatar/likeness, require approved source image and permission; clean metadata before Drive/handoff.

Detailed session/runbook: `references/mgs-grok-imagine-rollout-2026-06-16.md`.

## 5. Context compression / Codex gpt-5.5 notices

Use quando Rodolfo perguntar sobre mensagens do Hermes como:

```text
ℹ Codex gpt-5.5 caps context at 272K, so auto-compaction was raised to 85% (from X%)...
```

Interpretação correta: isso é um aviso de inicialização/primeiro turno, não erro e não alerta de que a thread já chegou a 85%. O Hermes detecta `openai-codex/gpt-5.5` e auto-eleva o threshold de compactação para 85% porque a rota Codex limita a janela em ~272K tokens; a mensagem apenas explica que mudou de `compression.threshold` antigo para `0.85`.

Workflow recomendado MGS:

1. Explicar de forma executiva: auto-compaction resume a conversa só quando o contexto fica grande; 85% usa mais janela antes de resumir.
2. Se Rodolfo quiser manter o comportamento mas remover o aviso repetitivo, **não desativar a compactação** e **não desligar o auto-raise como primeira opção**. Definir o threshold global do profile para o mesmo valor do auto-raise:

```bash
hermes config set compression.threshold 0.85
```

3. Validar no arquivo do profile, porque versões atuais do CLI têm `hermes config show`, mas não necessariamente `hermes config get`:

```bash
grep -n -A8 '^compression:' /root/.hermes/profiles/zeus/config.yaml
hermes config check
```

4. Se Rodolfo pedir explicitamente 90%/95%, aí desligar o auto-raise e setar manualmente:

```bash
hermes config set compression.codex_gpt55_autoraise false
hermes config set compression.threshold 0.90   # ou 0.95
```

Pitfalls:

- Não confundir “auto-compaction was raised” com “a compactação acabou de rodar”. É startup notice.
- Para MGS, 85% é a recomendação segura: em 272K, compacta em ~231K e deixa ~40.8K de folga. 90% deixa ~27.2K; 95% só ~13.6K e é arriscado com tool outputs/system prompt.
- Se uma sessão já aberta ainda mostrar o aviso, validar em nova sessão/novo init antes de concluir que a configuração falhou.

## 6. Reporting templates

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

Use **blocos simples sem language tag** ou bullets curtos para qualquer matriz de status/validação/novidades. Não usar tabela Markdown crua (`|---|---|`) em Discord: Rodolfo considera visualmente regressivo e já corrigiu esse padrão. Não usar fences com linguagem como ` ```text`, ` ```bash` ou ` ```json` em respostas Discord: em algumas renderizações isso vaza uma linha solta `text` e quebra a leitura. Cabeçalhos devem nascer do contexto real do update; não copiar exemplos. Se houver drift de estilo ou dúvida sobre renderização de tabelas, ver `references/discord-table-format-and-standards-drift.md`.

Regra de anexos para Rodolfo: **nunca enviar arquivo/anexo por iniciativa própria**. Se ele pedir “mostra por aqui”, “no chat” ou apenas pedir explicação/review, responder inline. Só enviar `MEDIA:/...`/anexo quando ele pedir explicitamente arquivo/anexo. Para documentos longos, oferecer resumo inline e perguntar se quer anexo. O guard local `/root/mgs-agent/scripts/discord-response-lint.py --check` deve acusar language-tagged fences, linha solta `text`, tabela Markdown crua e diretivas `MEDIA:/...` em drafts.

Quando a resposta longa foi redigida em arquivo/stdin antes de enviar, validar quando prático com:

```bash
python3 /root/mgs-agent/scripts/discord-response-lint.py --check < draft.md
```

**Se Rodolfo apontar regressão visual/legibilidade após update** (ex.: “por que não está em tabela?” ou “voltou aos padrões?”), não trate como mera preferência de resposta. Faça auditoria de padrões: config viva dos profiles, backups/snapshots, SOUL/style rules, gateways e patch guard. Se o problema for regra permissiva no SOUL, fortaleça a regra para “não usar tabela Markdown crua no Discord; usar bloco `text` alinhado” nos agentes afetados. Detalhe em `references/discord-table-format-and-standards-drift-2026-06-09.md`.

```text
Resumo: atualizar agora / deferir / janela controlada.
Evidências: commits atrás, highlights, risco local, backup/checks.
Impacto: gateways offline ~1-2 min; Zeus pode interromper sessão ativa.
Próximo passo: comando exato ou validação pendente.
```

Exemplo de matriz final:

```text
Item                    | Estado
------------------------|-------------------------------
Hermes                  | v0.16.0 / behind 0
Gateways                | Zeus/Atena/Ares/Hera active
Patches MGS             | guard OK / py_compile OK
Backup                  | removido ou path preservado
Pendência               | nenhuma ou ação concreta
```

## 7. Full MGS VPS migration / restore

Use `references/mgs-full-vps-migration-hostinger-2026-06-18.md` when Rodolfo asks to move the MGS/Hermes operation to a new VPS or asks whether to use `hermes backup/import` for migration. Core rule: `hermes backup/import` is the fast path for Hermes state, but a complete MGS migration also requires `/root/mgs-agent`, systemd gateway units, root crontab, OS packages/base tools, 1Password/uv/Node/Python, validation, REPORT-INFRA and updated infra inventory.

Preferred workflow: prepare target VPS → backup Hermes + `/root/mgs-agent` + units + crontab → transfer full runtime → restore Hermes/import → validate offline with gateways disabled → detached cutover finalizer stops old crons/gateways, final-syncs, installs crontab on target, then starts Ares/Hera/Atena before Zeus → validate live host/IP/services/logs. If copied Hermes venv fails with `cannot execute: required file not found`, check uv-managed Python symlinks and run `uv python install <missing-version>` on the target before retrying `hermes --version`.

## 7. Full VPS migration / Hostinger cutover

When Rodolfo wants to migrate the whole MGS/Hermes operation to a new VPS, use `references/mgs-full-vps-migration-hostinger-2026-06-18.md`. Core rule: `hermes backup/import` is the backbone for Hermes state, but full MGS migration also requires `/root/mgs-agent`, systemd units, crontab, local Hermes checkout/patches, 1Password validation, final delta sync, target startup validation, and old-VPS standby audit. Prefer **full mirror + controlled cutover** over piecemeal agent migration when Rodolfo's concern is future drift.

Do not call the cutover complete until the target has Zeus/Atena/Ares/Hera `active` + `enabled`, crons active, Codex auth present, patch guard OK, and the old VPS has gateways inactive/disabled, crontab empty, and zero Hermes/gateway processes. Validate `mgs-autocommit.service` separately; post-commit auto-push existing is not enough if the watcher service is missing.

When Rodolfo asks for a persistent “compare TUDO” verification after migration, run the deep manifest workflow in `references/mgs-vps-migration-deep-file-comparison.md`: compare `/root/mgs-agent`, Hermes profiles, Hermes checkout, systemd units and crontabs by SHA256/size; copy any historical old-VPS-only `backups/`, `tmp/` or `data/backups/` artifacts to production; disable **all** old-VPS services including `mgs-autocommit`; then classify remaining differences as runtime-only vs. risky before final reporting.

Post-migration finalization must also close the Git/runtime loop: install `inotify-tools` if needed, recreate/enable `/etc/systemd/system/mgs-autocommit.service`, secret-scan dirty files before staging, commit/push controlled migration state, clean or ignore runtime artifacts, and prove end-to-end with a create/delete auto-commit + auto-push smoke test. Detailed playbook: `references/mgs-hostinger-post-migration-autocommit-finalization-2026-06-18.md`.

## 8. New MGS agent bootstrap

When Rodolfo asks to start a new MGS agent/profile (Ares, Hera or future agents), use `references/mgs-new-agent-bootstrap.md`. Core rule: clone profile/config as needed, but immediately blank any inherited Discord bot token; do not create/enable the systemd gateway until the agent has its own dedicated bot token and Rodolfo confirms the Critical Subset system-file write.

When Rodolfo provisions a fresh Hostinger VPS for migration, use `references/hostinger-vps-agent-migration-bootstrap.md`. Default recommendation is Ares as the canary, Zeus last, Atena only after the new host is proven. First do read-only inventory; then get explicit confirmation before installing packages or changing system config. Initial bootstrap should avoid firewall/SSH hardening unless Rodolfo explicitly requests it.

After the profile/SOUL/config exist and Rodolfo has created the Discord application/bot, use `references/mgs-new-agent-discord-bot-token-gateway.md` for the live activation path: Discord OAuth permissions, 1Password token retrieval via MGS service-account env, token/API validation without leaking secrets, channel `403 Missing Access` diagnosis, Message Content Intent pitfall, systemd service creation, and end-to-end Discord validation.

Additional validated Hera bootstrap notes live in `references/mgs-hera-discord-bootstrap-2026-06-06.md`: 1Password token retrieval with project service-account env, channel `403 Missing Access` validation/fix, Discord Developer Portal `Message Content Intent` requirement, and stopping/disabling the service to avoid restart loops until privileged intents are enabled.

Critical pitfalls for new Discord agent gateways:

- Do **not** blindly sync inherited bundled/vendor skill categories into `/root/mgs-agent/profiles/<agent>-skills/`; add the new profile to SOUL/config sync first, and only add selective MGS-specific skill sync after deciding the category is genuinely custom/operational.
- Validate bot token internally without printing it: token length, decoded bot/application ID, and Discord API `/users/@me`.
- A bot can be valid and in the guild but still fail `GET /channels/<channel_id>` with `403 Missing Access`; fix channel/category permissions before starting the gateway.
- Hermes Discord gateway needs Discord Developer Portal → Bot → Privileged Gateway Intents → **Message Content Intent = ON**. If absent, logs show `discord.errors.PrivilegedIntentsRequired`; stop/disable/reset-failed the service until Rodolfo enables it, then start again.
- Only report end-to-end success after a real Discord mention test in the new agent channel produces an agent response, not just because systemd is `active`.

After the Discord application/bot exists and the token is stored securely, use `references/mgs-new-agent-discord-bot-token-gateway.md` for the phase-2 workflow: record app/bot IDs and permissions integer, fetch the token via 1Password service-account env without printing it, validate `/users/@me`, validate guild/channel access, handle `403 Missing Access`, then request explicit Critical Subset confirmation before creating systemd.

Session-specific Hera bootstrap notes live in `references/mgs-new-agent-bootstrap-hera-2026-06-06.md`, including the confirmed Hera channel ID, bot IDs, safe Phase 1 validation shape, and the pitfall that broad inherited skill sync can accidentally version hundreds of bundled creative skills.

## 8. Agent memory / conclusion layers

When Rodolfo asks to evaluate or configure external memory infrastructure such as Honcho for Zeus/Atena/Ares/Hera, use `references/honcho-managed-memory-spike.md`, `references/honcho-manual-briefing-command-2026-06-02.md`, and the session-specific coverage note `references/discord-response-lint-and-honcho-coverage-2026-06-15.md`.

Operational rule: treat Honcho-like systems as a conclusion/insight layer over sanitized history, not as source of truth. Canonical facts remain in JSON/DB/Git/WordPress/audit logs; procedures remain in Hermes skills; stable preferences remain in Hermes memory. Zeus may use Honcho to generate hypotheses, but must validate them against canonical MGS sources before reporting or acting.

Coverage audit pitfall: do not equate `honcho: {}` in a profile config with full operational integration. Check all three layers before answering whether an agent is configured: (1) profile config contains Honcho stanza, (2) agent SOUL contains the Honcho role/rules, and (3) `/root/mgs-agent/scripts/mgs-memory-copilot` / `experiments/honcho-spike/mgs_memory_copilot.py` supports that agent in `AGENT_PROFILES`. As of the 2026-06-15 audit, Zeus/Atena/Ares were supported as copilots; Hera had `honcho: {}` but lacked wrapper/SOUL integration.

Managed Honcho default for first spike: use only synthetic or sanitized data; store `HONCHO_API_KEY` in 1Password (`MGS Conteúdo` → `Honcho API - MGS` → `api key`); never paste or print the key. Self-hosting requires a separate infra decision because it introduces Docker/Postgres+pgvector/Redis/services.

Manual briefing command now exists for on-demand use only:

```bash
/root/mgs-agent/scripts/run-honcho-briefing
```

This command regenerates sanitized datasets, runs targeted Honcho rounds, builds a Zeus deterministic assessment, and renders Discord-safe Markdown. Do not schedule it as cron until each domain summarizer is deterministic enough and the final report preserves source counts/evidence. The final briefing should label Honcho outputs as hypotheses and use Zeus/canonical counters for operational conclusions.

## 9. Git / auto-commit / auto-push do `/root/mgs-agent`

Quando o GitHub `main` parecer velho apesar de haver commits/mudanças recentes no VPS, não assumir falha do GitHub. Validar a cadeia completa: branch atual, `HEAD` vs `origin/main`, dirty tree, `mgs-autocommit.service`, `scripts/auto-commit-watcher.sh`, `.git/hooks/post-commit` e `scripts/monitor-auto-push.sh`. Playbook: `references/mgs-agent-auto-commit-auto-push-repair.md`.

Pitfalls duráveis:

- Watcher `active` não significa GitHub atualizado; ele pode estar abortando por guardrail ou rodando em branch lateral.
- Hook hardcoded `git push origin main` pode registrar `Everything up-to-date` mesmo com commits novos em outra branch; em `main`, preferir `git push origin HEAD:main`, e fora de `main` logar falha explícita.
- Guardrail de nome sensível deve bloquear credenciais reais sem travar ferramentas defensivas com nomes como `*_secret_scan.py`.
- Monitor deve checar estado Git vivo, não só linhas de `auto-push.log`.

## 10. References and support files

Para manutenção de VPS/update com backup, recuperação manual de npm quando self-update quebra, e política de retenção/limpeza de backups, ver `references/vps-update-npm-backup-retention-2026-05-24.md`.

Esta umbrella absorveu as antigas skills especializadas abaixo. Conteúdo detalhado e histórico foi preservado nos arquivos de suporte:

- `references/hermes-update-original-skill.md`
- `references/hermes-update-post-update-validation.md`
- `references/hermes-controlled-update-rule-mgs.md` — regra permanente MGS aprovada por Rodolfo: backup + diff/snapshot pré-update + comparação pós-update + guard de patches/invariantes + validação runtime real antes de considerar update concluído.
- `references/hermes-controlled-update-git-hygiene-2026-06-15.md` — incidente/recuperação de Git hygiene quando reports/backups de update entraram no auto-commit: pausar autocommit, ignorar artifacts antes de gerar, force-push com lease após aprovação e `git gc` para recuperar espaço.
- `references/hermes-update-discord-report-and-followup-2026-06-17.md` — lessons from update where a stale hardcoded Discord thread received a report, detached restart finalizer did not proactively follow up, and Hermes news cron confused update scope; includes opt-in Discord delivery and backup cleanup guidance.
- `references/hermes-update-local-patch-surface-fail-closed-2026-06-17.md` — post-update local patch loss case: why file-level diff comparison missed missing functions, how to restore `pre-local-diff*`, promote author suffix/anti-loop/auto-attach/delete-message invariants to the guard, clean patch archives, and fail closed before mutation when live local diff does not apply to `origin/main`.
- `references/hermes-controlled-update-report-and-backup-compare-2026-06-15.md` — incidente/lesson de update Hermes em que backup/snapshot existiam mas a comparação backup↔estado vivo e o relatório pós-restart não foram entregues corretamente; define evidências obrigatórias `post-backup-live-profile-compare.txt`, `post-profiles-sanitized.txt` e `post-readonly-invariants.txt`.
- `references/hermes-local-patch-surface-guard-2026-06-17.md` — incidente/lesson em que update preservou arquivos modificados mas perdeu funções locais não-canônicas; exige restaurar `pre-local-diff*` pós-update e comparar markers/funções/strings do diff pré-update, não só nomes de arquivos.
- `references/hermes-manual-no-restart-update-patch-drift.md` — atualização manual sem restart automático: backup/diff, pull ff-only, reaplicar patches MGS, lidar com patch context drift, limpar `.update_check`, validar testes e pedir restart separado.
- `references/hermes-update-enospc-partial-update-recovery.md` — recuperar update parcial após `ENOSPC`: liberar espaço, distinguir repo atualizado vs. dependências falhas, reparar npm/uv, compilar e só então reiniciar gateways.
- `references/post-update-gateway-restart-validation.md` — validar update/restart Zeus+Atena+Ares quando Zeus reinicia a si mesmo; finalizer via systemd-run, distinção entre falha histórica de restart e erro ativo pós-start.
- `references/hermes-restart-loop-and-cron-drift-2026-06-11.md` — incidente de loop profundo ao reiniciar Zeus/Atena/Ares/Hera a partir da própria conversa do Zeus; ensina finalizer único/idempotente, Zeus por último, inspeção de log antes de novas tentativas, e checagem de drift em root crontab vs. `docs/CRONS.md`.
- `references/hermes-update-enospc-controlled-recovery.md` — recuperar update parcial após `No space left on device`: inventário/limpeza de backups, reparo de Python/npm sem restart, validação e restart separado.
- `references/mgs-full-vps-migration-hostinger-2026-06-18.md` — full MGS/Hermes VPS migration playbook from Hetzner to Hostinger: full mirror + controlled cutover, `hermes backup/import` limitations, finalizer pattern, target validation, old-VPS standby audit, and mgs-autocommit watcher pitfall.
- `references/hermes-update-pre-update-review.md`
- `references/hermes-update-2026-05-16-mgs-relevance.md`
- `references/hermes-update-2026-06-04-all-agents-test-env.md` — all-agent restart validation for Zeus/Atena/Ares plus pytest cwd/env isolation pitfalls after Hermes updates
- `references/mgs-full-maintenance-validation-and-npm-manual-update.md` — full post-maintenance validation checklist + safe manual npm replacement/rollback pattern
- `references/hermes-web-tooling-original-skill.md`
- `references/hermes-web-tooling-2026-05-17.md`
- `references/hermes-web-brave-search-mgs-2026-05-17.md`
- `scripts/test-brave-search-mgs.sh`
- `references/hermes-profile-config-migration-mgs.md` — migração controlada de `config.yaml` por profile após update Hermes: backup pequeno, `hermes -p <profile> config migrate`, validação provider/model/auth/gateway/patch guard, sync dos mirrors MGS, restart gracioso e audit log.
- `references/discord-table-format-and-standards-drift.md` — padrão MGS para tabelas em Discord: blocos simples/alinhados sem tabela Markdown crua para respostas operacionais; inclui workflow para corrigir drift de SOUL/estilo.
- `references/discord-output-and-attachment-guard-2026-06-15.md` — correção de saída Discord quebrada por language-tagged fences/linha solta `text` e regra forte contra anexos não solicitados; inclui uso de `/root/mgs-agent/scripts/discord-response-lint.py`.
- `references/openai-codex-oauth-original-skill.md`
- `references/openai-codex-cron-model-pinning.md`
- `references/openai-codex-anthropic-api-decommission.md`
- `references/openai-codex-cost-monitoring-gpt-oauth.md`
- `references/hermes-image-gen-openai-codex-mgs.md` — configurar image generation via `openai-codex`/ChatGPT OAuth para perfis MGS como Hera; separa modelo de chat (`gpt-5.5`) de backend de imagem, evita fallback FAL sem `FAL_KEY`, e inclui smoke test real com `hermes -p <profile> -t image_gen -z ...`.
- `references/grok-xai-oauth-creative-media-rollout-2026-06-16.md` — rollout MGS de Grok/xAI via OAuth SuperGrok para Creative Ops: OAuth manual-paste, cópia segura de `providers.xai-oauth` entre profiles, configuração Hera GPT+Grok lado a lado, wrapper `/root/mgs-agent/scripts/mgs-grok-generate.py`, smoke tests reais de imagem/vídeo e pitfall de ignorar `data/generated/` no Git.
- `references/hera-creative-calibration-and-xai-auth-2026-06-17.md` — correção de Hera quando Creative Ops parece genérica/perdida: hard gates para referência externa e GPT+Grok, cópia segura de xAI OAuth válido preservando `active_provider=openai-codex`, smoke tests reais e padrão de diretora de arte/produtora.
- `references/atena-openhands-provider-diagnostic.md` — diagnosticar OpenHands da Atena: funcionalidade vs. provider/modelo/custo, wrapper e trajectories sem vazar credenciais
- `references/openhands-gpt55-codex-wrapper.md` — padrão MGS para OpenHands com GPT-5.5/OpenAI-Codex OAuth, bloqueio de fallback provider e validação real do runtime model
- `references/honcho-managed-memory-spike.md` — avaliação/configuração de Honcho como camada managed de conclusões sobre histórico sanitizado; inclui política de fonte de verdade, 1Password/API key, smoke test sintético e ingestão manual de logs sanitizados.
- `references/honcho-targeted-rounds-2026-06-02.md` — primeira rodada MGS com datasets por domínio; registra limite de 100 mensagens por batch, vantagem de agregados determinísticos sobre logs brutos, pitfall de secret-scan com placeholders e scoping de `.chat()` por sessão.
- `references/honcho-manual-briefing-command-2026-06-02.md` — comando manual `/root/mgs-agent/scripts/run-honcho-briefing`, renderer Markdown/Discord, política de on-demand only, e lessons de Zeus deterministic layer sobre Honcho hypotheses.
- `scripts/honcho_sanitized_secret_scan.py` — scanner local para barrar padrões óbvios de secrets antes de enviar dataset sanitizado ao Honcho
