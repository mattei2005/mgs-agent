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

Só reportar sucesso depois de confirmar upstream, serviços, patches/smokes e testes alvo.

**Regra MGS pós-update:** toda conclusão de update deve incluir automaticamente, sem Rodolfo precisar pedir: (1) se deu tudo certo ou pendências, (2) status vivo dos gateways, (3) validação OpenAI Codex auth em root + Zeus/Atena/Ares sem imprimir tokens, (4) backup criado/apagado e disco, (5) delta desde a versão/commit anterior — commits aplicados, highlights por impacto MGS, e o que não mudou.

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
- Após `hermes update`, `systemd` pode mostrar falhas `status=1/FAILURE` durante restart controlado. Diferenciar incidente ativo de histórico: confirmar PIDs atuais, uptime do serviço, memória atual/peak, logs posteriores e se há novo traceback/OOM. Só alertar como loop se houver falhas repetidas depois do novo start.
- Timeout do terminal não prova falha; `hermes update` pode seguir em background. Verificar depois com versão, commits e serviços.
- Se `hermes update` falhar por `ENOSPC`/disco cheio, **não repetir update às cegas**. Primeiro checar `df -h /`, `df -ih /`, maiores diretórios, logs do update, HEAD/origin/behind, `git status`, stashes e serviços. O repo pode já estar em `behind: 0` com patches locais restaurados, enquanto npm/dependências falharam e os gateways ainda rodam PIDs antigos. Liberar espaço (alvo 8–10G livres; backups redundantes de profiles são candidatos comuns), reparar dependências com `uv pip install --python "$repo/venv/bin/python" -e '.[all]'` + `npm install --no-fund --no-audit` (+ `ui-tui` se existir), compilar arquivos críticos, e só então reiniciar/validar gateways. Playbook: `references/hermes-update-enospc-partial-update-recovery.md`.
- Se `hermes update` oficial travar/timeoutar sem output, **não repetir em loop**. Rodar verificação de estado; se ainda estiver atrasado, executar atualização manual controlada: backup já feito → `git stash push -u` dos patches locais → `git fetch origin main` → `git pull --ff-only origin main` → restaurar stash/patch local → limpar `__pycache__` → reinstalar dependências (`venv/bin/python -m pip install -e '.[all]'`) → `npm install`/build web quando aplicável → remover `.update_check` dos profiles → validar commit HEAD/origin, `hermes --version`, `py_compile` e serviços.
- Quando a ordem for **atualizar sem restart automático**, não usar o caminho oficial `hermes update` como execução principal porque ele auto-reinicia gateways no final. Usar o playbook `references/hermes-manual-no-restart-update-patch-drift.md`: backup + salvar `git diff`, `git reset --hard`, `git pull --ff-only`, reaplicar/validar patches MGS, reinstalar deps/builds, limpar `.update_check`, validar e só então pedir autorização separada para restart gracioso.
- Antes de update manual com patch local MGS, salvar `git diff` em backup e testar `git apply --check` contra `origin/main` em worktree temporário. Se aplicar limpo, o risco é controlado; se não aplicar, portar patch antes de atualizar. Se `git apply --reverse --check` false-falhar porque um patch composto já está presente com contexto driftado, validar por invariantes + `py_compile` em vez de tratar como ausência de patch.
- Patches locais críticos MGS devem ser preservados por `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh`. Esse guard aplica/valida os patches canônicos em `/root/mgs-agent/patches/hermes/`, compila `plugins/platforms/discord/adapter.py` + `gateway/run.py`, e falha se invariantes como `_auto_thread_name_from_message`, `DISCORD_THREAD_AUTO_ADD_USERS`, `Auto-thread member sync` ou planned restart auto-resume sumirem. O script controlado `/root/mgs-agent/scripts/run-hermes-update-controlled.sh` chama esse guard após update. O repo Hermes também tem hook local `.git/hooks/post-merge` chamando o guard; se update upstream sobrescrever/resetar algo, o merge falha ou reaplica antes de restart. Há também watchdog Hermes cron `44671121f3cc` (`Hermes MGS patch watchdog`) a cada 6h, script-only/silencioso em sucesso, alertando a origem se o guard falhar.
- Em update Hermes MGS, tratar **Zeus + Atena + Ares** como conjunto afetado se os três gateways estiverem ativos. O script controlado pode reiniciar só Zeus/Atena dependendo da versão; validar/reiniciar Ares separadamente ou atualizar o script antes de reportar sucesso. Ver `references/hermes-update-2026-06-04-all-agents-test-env.md`.
- Ao rodar pytest pós-update, executar a partir de `/root/.hermes/hermes-agent` ou usar `workdir` nesse repo. Testes `tests/gateway/...` falham como “file not found” se lançados de `/root/mgs-agent`. Em shell vivo do gateway, isolar/limpar variáveis `DISCORD_*` de produção quando testes upstream-ish dependem de defaults; preserve/assert apenas invariantes MGS. Ver `references/hermes-update-2026-06-04-all-agents-test-env.md`.
- Em updates de sistema junto com Hermes, tratar reboot como Critical Subset: atualizar pacotes e reiniciar serviços quando necessário, mas pedir confirmação separada para `reboot` do VPS.
- Para NPM global, priorizar CLIs operacionais (`@openai/codex`, `agent-browser`, `@anthropic-ai/claude-code`, `corepack`). Não forçar self-update major do `npm` se ele é fornecido pelo pacote NodeSource/OS e falha internamente; reportar como pendência separada em vez de substituir manualmente `/usr/lib/node_modules/npm` sem necessidade.
- Se Rodolfo confirmar explicitamente que quer fechar a pendência do `npm` mesmo assim, tratar como operação crítica por modificar `/usr/lib`: backup tar + diretório rollback, baixar tarball oficial do registry, verificar `shasum`, substituir `/usr/lib/node_modules/npm`, validar `npm -v`, `npm exec`, `npm outdated -g` e gateways. Playbook completo: `references/mgs-full-maintenance-validation-and-npm-manual-update.md`.
- Em v0.13.0+, o antigo patch local MGS `busy_input_mode: queue` foi integrado upstream. Se `grep "PATCH (MGS Digital Corp)" gateway/run.py` retornar vazio, isso é esperado; não reaplicar patch antigo.
- `hermes --version` pode manter a mesma tag quando só houve commits sem nova release; “up to date” e commit HEAD/origin são mais relevantes.
- Após restart manual, journal pode mostrar `status=1/FAILURE` para PIDs antigos encerrados; não reportar incidente se PIDs novos estão `active`, sem traceback/OOM posterior.
- Se upstream migrar o Discord adapter de `gateway/platforms/discord.py` para `plugins/platforms/discord/adapter.py`, qualquer patch local MGS em Discord falha no apply direto com “file not found”. Antes de recomendar update, gerar `git diff`, testar apply contra `origin/main`; se falhar por path migration, reescrever o path do patch para `plugins/platforms/discord/adapter.py` em worktree temporário e rodar `git apply --check` + `py_compile`. Se o port check passar, o update é viável mas exige janela controlada: update, portar patch, compilar, restart Zeus/Atena e testar thread/auto-add/send_message.
