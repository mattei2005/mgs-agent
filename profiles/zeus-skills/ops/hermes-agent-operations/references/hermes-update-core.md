# Hermes Update — Core Workflow

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 1. Update seguro do Hermes

Use quando Rodolfo pedir atualização do Hermes ou quando monitor detectar nova versão.

**Regra permanente MGS aprovada por Rodolfo:** nenhum update Hermes é considerado concluído sem backup + diff/snapshot pré-update + comparação pós-update + guard de patches/invariantes MGS + validação runtime real. O playbook canônico é `references/hermes-controlled-update-rule-mgs.md` e o script padrão é `/root/mgs-agent/scripts/run-hermes-update-controlled.sh`.

**Bundled skills após update:** quando `hermes update` reportar `user-modified bundled skill(s)`, não restaurar tudo às cegas. Auditar por profile (`root`, Zeus, Atena, Ares, agente legado), gerar diffs, classificar cada skill em restore stock / limpar artifact / manter e rebaseline / merge manual. Para merges, começar do stock atual em `/root/.hermes/hermes-agent/skills/...`, reinserir só o conteúdo local útil, rebaselinear o manifest e validar que `hermes skills list-modified` retorna “No user-modified bundled skills” em todos os profiles. Playbook: `references/hermes-bundled-skill-sync-merge-2026-07-05.md`.

**Guard contra precheck canônico stale:** o precheck nunca pode manter nome hardcoded de um patch runtime antigo enquanto `ensure-hermes-mgs-patches.sh` já promoveu outro mais novo. `run-hermes-update-controlled.sh` deve descobrir o `mgs-runtime-customizations-*.patch` mais recente, verificar que o guard o referencia e testar esse mesmo artefato contra `origin/main`. Drift de patch antigo não representa o risco atual e pode bloquear/enganar a decisão de port. Quando um port novo for criado, promover o patch no guard antes do precheck final; a checagem deve falhar fechado se latest patch e guard divergirem. Além do artifact runtime mais recente, o updater deve derivar do guard/manifesto a cobertura completa dos patches suplementares, ou validar igualdade exata entre os dois conjuntos; um guard com patches novos e um precheck hardcoded menor é gate vermelho. Antes de portar, rodar baseline ampla sobre todos os módulos/testes locais modificados: suíte estreita verde não compensa fixture incompatível ou teste fora da lista. Procedimento: `references/hermes-update-preport-baseline-and-patch-coverage.md`. O padrão validado, junto com manutenção VPS em lotes, backup npm/Corepack e boundary de update Hermes sem restart, está em `references/vps-and-hermes-staged-maintenance-2026-07-10.md`. A execução detalhada v0.18.2 — stash reversível, worktree, bundled-skill artifact cleanup e finalizer com readiness por offsets de `agent.log` — está em `references/hermes-update-2026-07-10-controlled-no-restart.md`.

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

**Correção operacional após incidentes 2026-06-15/2026-06-17:** backup sozinho não basta, e comparar só nomes de arquivos também não basta. O update só pode ser chamado de concluído após comparar a superfície crítica viva contra o backup/pre-state e gerar evidência explícita: `post-profiles-sanitized.txt`, `post-backup-live-profile-compare.txt`, `post-readonly-invariants.txt` e comparação de markers/funções/strings introduzidos por `pre-local-diff.patch` / `pre-local-diff-cached.patch`. Escopo mínimo: `config.yaml`, `SOUL.md` e `auth.json` sanitizado para Zeus/Atena/Ares/agente legado, além dos invariantes MGS em Hermes. Depois do update, o fluxo deve restaurar os diffs locais pré-update e falhar fechado se qualquer patch local não restaurar limpo ou se algum marker local sumir sem evidência de incorporação upstream equivalente. Se a comparação foi feita retroativamente, dizer que foi retroativa; não apresentar como se tivesse sido feita no fluxo original. Detalhes: `references/hermes-controlled-update-report-and-backup-compare-2026-06-15.md` e `references/hermes-local-patch-surface-guard-2026-06-17.md`.

- **Git hygiene obrigatório antes de gerar artifacts:** update reports/backups não são código. Antes de rodar ou validar fluxo que cria `/root/mgs-agent/reports/hermes-updates/` ou `*.tar.gz`, garantir `.gitignore` cobrindo esses paths e pausar `mgs-autocommit.service` se o fluxo ainda está em desenvolvimento/teste. Se artifacts pesados/sensíveis entrarem no Git, tratar como incidente: parar autocommit, resetar para commit limpo, force-push com lease após aprovação explícita de Rodolfo, `git reflog expire` + `git gc --prune=now`, validar disco e reativar autocommit. Detalhe: `references/hermes-controlled-update-git-hygiene-2026-06-15.md`.

- **Discord MGS tool progress é preferência operacional ativa, não constante fixa:** em profiles MGS, `display.platforms.discord.tool_progress` tem precedência sobre `display.tool_progress`. A preferência já mudou em sessões diferentes: em 2026-06-30 Zeus desligou por cautela após ruído/travamento; em 2026-07-05 Rodolfo pediu religar para Zeus/Atena/Ares/agente legado. Não interpretar reclamação genérica de ruído como autorização permanente para desligar breadcrumbs; se a intenção for ambígua, perguntar antes de mudar uma preferência visual global. Para religar o comportamento antigo: live profiles + mirrors com `display.tool_progress: all`, `display.platforms.discord.tool_progress: all`, `tool_preview_length: 40`, `cleanup_progress: true`; validar via `resolve_display_setting(..., 'discord', 'tool_progress') == 'all'`. Para desligar, usar `off`/`0` e validar igual. Mudança de display normalmente vale no próximo turno e não exige restart; só reiniciar gateways se a próxima tool call não refletir a configuração. Detalhes: `references/mgs-discord-tool-progress-and-backup-retention-2026-06-30.md` e `references/mgs-discord-tool-progress-toggle-2026-07-05.md`.

- **Retenção de backups Hermes update:** o housekeeping genérico de `.bak/.backup/.old/.orig/~` não cobre sozinho os tarballs grandes `reports/hermes-updates/**/hermes-profiles-backup-*.tar.gz`. Manter política explícita `keep_latest=1`: criar e validar integralmente o sucessor, preservar o mais recente globalmente e só então remover os anteriores. `mgs-safety-backup.sh` segue a mesma troca segura por família e pode tratar `tar rc=1` por `file changed as we read it` como WARN se o archive existe e `tar -tzf` passa. Validar ambos os scripts por dry-run e readback dos arquivos retidos. Detalhe histórico: `references/mgs-discord-tool-progress-and-backup-retention-2026-06-30.md`; a decisão institucional vigente está registrada em `context/mgs-os-map.md` e `data/knowledge-registry.json`.

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

Quando a pergunta for “vale atualizar?”, fazer análise read-only antes de recomendar. Ver `references/hermes-update-pre-update-review.md`. Se outro operador já estiver executando o precheck, ou se o escopo proibir fetch, artifacts, testes e worktrees, usar `references/hermes-readonly-delta-review-no-worktree.md`: revisar apenas refs já presentes, separar release commit de commits pós-release sob a mesma versão, fazer scan exato dos hunks em memória e distinguir risco textual, semântico e operacional. Reportar:

- commits atrás e delta de arquivos/linhas;
- features/fixes/docs/manutenção por contagem aproximada;
- melhorias relevantes para MGS;
- SHA exato revisado e, quando aplicável, release boundary vs. `origin/main` móvel;
- risco textual de patches separado do risco semântico em lifecycle/Discord e do risco operacional do updater;
- recomendação: atualizar agora, deferir ou atualizar em janela controlada.

#### Contagem sem ambiguidade em upstream móvel

Nunca apresentar uma contagem isolada de commits como “as atualizações” sem nomear a base. Em toda revisão, separar explicitamente:

1. **Novos desde a revisão/plano anterior:** `<sha-anterior>..origin/main`.
2. **Pendentes no runtime instalado:** `HEAD..origin/main` — esta é a dimensão do update operacional.
3. **Desde a última tag pública:** `<tag>..origin/main` — mostra quanto do `main` ainda não virou release.

Sequenciar a medição: primeiro `git fetch origin main --tags`; depois capturar uma única vez `HEAD`, `origin/main`, tag e timestamp; só então calcular ancestry, contagens e shortstats. Não rodar o fetch em paralelo com `hermes version` ou contagens, pois commits entrando durante a coleta produzem números internamente inconsistentes. Antes da resposta final, fazer uma atualização curta da ref; se o SHA mudou, recalcular e dizer quantos commits chegaram durante a análise.

Validar `merge-base --is-ancestor` antes de usar intervalos de um plano anterior. Cruzar a contagem com a comparação Git/GitHub quando disponível. O grafo Git bruto é a evidência primária; `hermes version` é um indicador conveniente e pode refletir cache, filtro ou snapshot diferente. Se divergir, reportar ambos e a lacuna em vez de escolher silenciosamente um número. Exemplo de linguagem correta: “55 novos desde o plano anterior; 269 pendentes no checkout instalado; 455 desde a última tag pública”.

### Execução

```bash
hermes update 2>&1
```

Se o guardrail bloquear por reiniciar gateways/matar sessões, não tentar burlar nem repetir em loop. Reportar o backup/checks já feitos e pedir que Rodolfo rode `hermes update` manualmente no shell; depois continuar a validação com o output dele.

### Validação pós-update obrigatória

When Rodolfo says the backup/update is already done, stop recommending an update window and switch directly to post-update verification. See `references/hermes-v15-post-update-validation-2026-05-28.md` for the v15 validation evidence shape and path-migration pitfall.

Antes da ativação, trate checkout atualizado, dependências preparadas e runtime carregado como três estados separados. Se existir `venv-next-*`, compare o Python, versões dos pacotes críticos e o `pip freeze` completo com o `venv` ativo. Quando forem idênticos, não faça uma troca de venv sem necessidade: mantenha o ambiente ativo e limite a ativação ao restart controlado. O finalizer deve preservar a ordem explícita dos agentes não-Zeus, sempre forçar Zeus por último e derivar a cobertura de snapshot/`py_compile` de todos os módulos runtime realmente alterados; uma lista fixa menor que o diff é gate vermelho. Inclua também no snapshot qualquer skill/referência estrutural alterada que precise entrar ativa após o restart; escrita tardia exige regenerar o snapshot antes de agendar. Após staging manual, o banner de `hermes --version` pode reutilizar `.update_check` e exibir uma contagem antiga até o TTL expirar: use `HEAD`, `origin/main` e `HEAD..origin/main` como evidência primária, e não apague o cache sem a confirmação destrutiva aplicável. Revisão delegada interrompida, expirada ou sem parecer substantivo não conta como validação nem como ausência de achado.

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

Quando Rodolfo pedir uma **revisão geral pós-update** (funcionalidades, crons, patches locais, padrões dos agentes e novidades), usar também `references/hermes-post-update-full-system-review.md`. Esse playbook amplia a validação para crons MGS/Hermes, logs, smoke tests reais (Brave/TTS/agente legado image_gen), comparação live config vs. mirror/snapshot, política GPT-5.5/OpenAI-Codex e resumo de release notes/Ubuntu security updates.
