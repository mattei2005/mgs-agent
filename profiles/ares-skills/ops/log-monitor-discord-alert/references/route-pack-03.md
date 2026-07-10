## Triage operacional de alertas já disparados

Quando Rodolfo pedir para "resolver um por um" alertas de Discord/cron/infra, não assumir que todos ainda estão ativos. Fazer triagem read-only primeiro e classificar cada alerta como **ativo**, **resolvido**, **histórico** ou **teste/layout** antes de mexer em scripts.

Checklist validado:

```bash
# Estado atual do monitor e últimos eventos
tail -80 /root/mgs-agent/logs/monitor-NOME.log
jq . /root/mgs-agent/data/NOME-state.json 2>/dev/null || true

# Se for script shell, validar sintaxe de todos os monitors tocados
bash -n /root/mgs-agent/scripts/monitor-NOME.sh

# Executar manualmente só quando for seguro/idempotente; usar --dry-run quando existir
/root/mgs-agent/scripts/monitor-NOME.sh --dry-run
/root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1

# Confirmar resolução pelo log/state após a execução
tail -20 /root/mgs-agent/logs/monitor-NOME.log
```

Padrão de resposta para o CEO: tabela curta com `Item | Status agora | Decisão`. Separar claramente pendências deliberadas (ex: update Hermes em outro tópico) de problemas resolvidos. Se um erro apareceu em log mas `bash -n` e execução real passam depois, reportar como "não reproduzido no estado atual" e citar a validação feita, sem inventar causa.

---
## Atualizar infra-inventory.json

Após criar os artefatos, atualizar manualmente 3 seções do inventário:

```json
// crons: adicionar
{
  "entry": "*/15 * * * * /root/mgs-agent/scripts/monitor-NOME.sh >> /root/mgs-agent/logs/monitor-NOME.log 2>&1",
  "description": "Monitor de ..."
}

// scripts: adicionar
{
  "path": "/root/mgs-agent/scripts/monitor-NOME.sh",
  "size_bytes": N,
  "modified_at": "TIMESTAMP",
  "description": "..."
}

// data_files: adicionar
{
  "path": "/root/mgs-agent/data/NOME-monitor.json",
  "description": "Estado do monitor. Campos: last_check, consecutive_failures, last_alert_sent, last_failure_details.",
  "modified_at": "TIMESTAMP"
}
```

---
## Pitfalls

1. **`notify_on_complete=true` envia output bruto diretamente no canal Discord** — ao rodar scripts com `terminal(background=true, notify_on_complete=true)`, a plataforma Hermes entrega automaticamente o output completo do processo no canal assim que termina, **sem passar pelo agente**. Isso polui o canal com logs brutos. Usar sempre `process(action='wait')` ou `process(action='poll')` manualmente e sumarizar o resultado em 1-2 linhas. Nunca usar `notify_on_complete=true` para processos verbosos no canal de conversa.

   **Causa raiz mais profunda:** mesmo *sem* `notify_on_complete=true`, o gateway Hermes tem um watcher assíncrono que entrega o output de *qualquer* background process no canal quando `background_process_notifications != "off"`. Configurável em:
   - `~/.hermes/profiles/zeus/config.yaml` → `display.background_process_notifications: error` (só alerta em falha)
   - Env var: `HERMES_BACKGROUND_NOTIFICATIONS=error`
   
   Modos disponíveis: `all` (padrão — sempre entrega), `result` (só ao terminar), `error` (só se exit ≠ 0), `off` (silêncio total). O modo `error` é o ideal para o canal Zeus: silêncio em sucesso, alerta em falha. Código em `gateway/run.py` → `_load_background_notifications_mode()`.

2. **`os.environ` em `execute_code` não propaga para `terminal()`** — variáveis setadas com `os.environ[...] = ...` em Python NÃO chegam nos subprocessos do `terminal()`. Para credenciais 1Password dentro de `execute_code`, chamar `terminal("op item get ... --reveal")` diretamente e usar o output como string Python. Não tentar setar via `os.environ` e usar em `terminal()` subsequente.

2. **Campo do webhook no 1Password é `webhook_url`, não `url`** — os itens "Discord Webhook - Alerts Infra Channel" e "Discord Webhook - Zeus Channel" usam campo `label=webhook_url`. Para REPORT-INFRA/alertas, usar Alerts Infra. Usar `--fields label=webhook_url --reveal` (não `--fields label=url`).

3. **Sempre exportar `OP_SERVICE_ACCOUNT_TOKEN` antes do `op` em scripts shell** — scripts executados via cron não têm a env do `.env` carregada automaticamente. O `source "${BASE_DIR}/.env"` no início do script é obrigatório. Usar o padrão `set -a / source / set +a` descrito em `references/shell-env-crontab-patterns.md` (padrão canônico MGS para scripts que invocam `op`). Para segurança ao modificar crontab via script, ver a seção "Padrão Proibido" no mesmo arquivo.

4. **WINDOW_LINES pode estar vazio se o log não tem entradas recentes** — tratar o caso sem erro (script deve terminar normalmente com "OK: zero falhas").

5. **`jq -r '.field // 0'` para campos numéricos** — se o state file tiver `"consecutive_failures": null`, o `// 0` garante fallback para 0. Sem isso, aritmética bash pode falhar.

6. **Arquivo `.tmp` intermediário no jq** — sempre usar `jq ... "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"` para evitar truncar o state file em caso de erro do jq.

7. **Regex `[a-f0-9]+` falha silenciosamente em IDs não-hex** — o padrão `grep -oP 'commit=\K[a-f0-9]+'` retorna vazio (e dispara `|| continue`) quando o ID começa com caractere não-hex (ex: `test001` → `t` não é hex → zero match → falha ignorada silenciosamente). Em testes de stress, usar sempre IDs com prefixo hex válido (ex: `dead001`, `cafe001`, `beef001`). Em produção, hashes git reais são sempre hex — não é bug do script, é armadilha nos testes.

8. **Não adicionar o cron manualmente ao crontab** — usar `(crontab -l 2>/dev/null; echo "ENTRY") | crontab -` para preservar entradas existentes. `crontab -l > /tmp/crontab_current.txt && echo "..." >> /tmp/crontab_current.txt && crontab /tmp/crontab_current.txt` também funciona (alternativa usada em 2026-04-26).

9. **`grep -c ... || echo 0` gera bug de `0\n0`** — `grep -c` imprime `0` quando não acha match, mas sai com código 1; o `|| echo 0` imprime outro zero. Em variável usada como número, quebra com `syntax error in expression`. Usar `grep -c ... || true` e fallback separado. Ver `references/cron-semantic-error-audit.md`.

10. **`set -euo pipefail` + pipelines com `head` podem matar monitor antes de logar erro** — comandos como `git log ... | head -5 | sed ...` podem sair com `141`/SIGPIPE por causa do `head`, e com `pipefail` isso aborta o script inteiro. Em monitores de cron, proteger pipelines de listagem/truncamento com bloco tolerante: `VAR=$( { comando | head -5 | sed ...; } || true )`. Também preferir `log "START ..."` logo após definir a função de log para stale-log distinguir “nunca rodou” de “rodou e abortou cedo”.

11. **Flags combinadas de `git log --grep` não são portáveis como esperado** — `git log ... -iE` pode falhar como `fatal: unrecognized argument: -iE`; usar flags longas separadas para regex/case-insensitive: `--regexp-ignore-case --extended-regexp`. Se o regex usa parênteses/alternância, validar isoladamente; regex inválida com stderr redirecionado vira abort silencioso sob `set -e`.

10. **Stale-log monitor não detecta cron rodando com erro** — `mtime` recente só prova execução. Para cron crítico, adicionar semantic scan de `syntax error|traceback|exception|fatal:|critical|erro crítico|error token|command not found|permission denied|no such file or directory` nas últimas linhas. Quando houver marcador de início (`start`, `iniciando`, `===`), escanear só o bloco da execução mais recente para não alertar erro antigo já resolvido.

11. **Redirect do crontab pode divergir do log interno do script** — se o cron tem `>> logs/foo.log` mas o script escreve heartbeat em `LOG=logs/bar.log`, o stale monitor tende a observar `foo.log` e gerar falso STALE. `CUSTOM_LOG` não corrige quando há redirect explícito, porque o parser já encontrou um log. Corrigir padronizando um único log canônico, de preferência o redirect do crontab, manter heartbeat de no-op saudável e validar com `monitor-cron-stale-logs.sh --dry-run` antes de limpar state. Ver `references/cron-log-path-canonicalization.md`.

12. **Crons shell com `set -euo pipefail` podem morrer antes de atualizar log/state** — se o script só loga no fim, o watchdog acusa stale sem revelar causa. Em monitors críticos, logar `START` imediatamente após criar o log e antes de comandos frágeis. Ao usar `git log ... | head`, proteger contra SIGPIPE/exit 141 com bloco `{ ... | head ...; } || true`. Não usar flags agrupadas inválidas como `git log -iE`; para grep case-insensitive + regex em git, preferir `--regexp-ignore-case --extended-regexp`. Validar com `bash -n`, execução manual real e depois `monitor-cron-stale-logs.sh --dry-run` para confirmar que o item saiu de STALE.

12. **Snapshots de canal/Discord/API salvos em `data/` são runtime local, não inventário** — se criar arquivo como `data/alerts-infra-last100.json` para análise temporária, adicionar padrão local-only ao `.gitignore` antes de deixar o auto-commit watcher rodar; caso versione por acidente, remover e commitar a remoção.

13. **Auto-commit watcher com `git add .` precisa guardrail de segredo**

12. **Hardening SSH incremental para monitors via jump host** — quando um monitor usa `expect` + senha + `ssh/scp -J`, não trocar direto para chave permanente sem autorização explícita do Rodolfo. Primeiro remover `StrictHostKeyChecking` desativado e usar `StrictHostKeyChecking=accept-new` com `UserKnownHostsFile=/root/.ssh/known_hosts_mgs`, `mktemp -d` local com `chmod 700`, `trap cleanup EXIT`, script remoto único (`/tmp/name_$$.sh`) e remoção remota após execução. Validar com execução real controlada e confirmar que não houve post Discord indevido. Ver `references/cron-ssh-hardening-2026-05-16.md`.

---

---
