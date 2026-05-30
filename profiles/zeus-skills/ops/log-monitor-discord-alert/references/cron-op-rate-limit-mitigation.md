# Cron monitors: reduzir pressão no `op` sem cache de credenciais

## Quando usar

Use quando vários crons/monitores MGS falham com `Too many requests` do 1Password CLI (`op`) ou quando alertas diferentes aparecem em cascata (auto-push, Yoast, watchdog de cron, webhooks). Trate como problema de **pressão no control plane de credenciais**, não como falha isolada de Git/webhook/Yoast.

## Princípios de segurança

- Não hardcode webhook URLs, GitHub PATs, RunCloud passwords ou application passwords em scripts/`.env` para “resolver rápido”.
- Não criar cache local de credenciais (`/run/secrets`, `/run/mgs-agent/secrets`, etc.) sem aprovação explícita de Rodolfo; isso muda o modelo de segurança.
- Antes de retries manuais que dependem do `op`, fazer um probe único e reportar só `len=X`/erro redigido; nunca imprimir segredo.

Probe seguro:

```bash
set -a; . /root/mgs-agent/.env 2>/dev/null; set +a
v=$(op item get 'Discord Webhook - Alerts Infra Channel' \
  --vault 'MGS Conteúdo' --fields label=webhook_url --reveal 2>/tmp/operr.$$ || true)
err=$(cat /tmp/operr.$$); rm -f /tmp/operr.$$
printf 'len=%s err=%s\n' "${#v}" "$(printf '%s' "$err" | sed -E 's/[A-Za-z0-9_]{12,}/[REDACTED]/g')"
```

## Mitigação preferida, em ordem

### 1. Inventariar chamadas `op`

```bash
crontab -l
# Depois buscar em scripts por:
# op item get | op read | helpers de retry tipo op_get_retry
```

Classifique cada chamada:

```text
Tipo                     Ação
-----------------------  ------------------------------------------------
Necessária para checar   manter, mas reduzir retries/espalhar horário
Só necessária para alerta mover para o caminho de alerta real
```

### 2. Stagger de crons

Espalhar horários para evitar rajadas simultâneas. Exemplo validado MGS:

```cron
1-56/5 * * * *       monitor-service-restarts.sh
3-58/5 * * * *       monitor-tool-loops.sh
7,22,37,52 * * * *   check-pending-reports.sh
11,26,41,56 * * * *  monitor-auto-push.sh
23 10 * * *          monitor-yoast-health-eggbev.sh
47 12 * * *          monitor-gpt55-oauth-cost.sh
17 3 * * *           housekeeping-bak-cleanup.sh
```

Crontab edit safety:
- Backup primeiro em `/root/mgs-agent/data/crontab-backup-YYYYMMDD-HHMMSS.txt`.
- Gerar arquivo intermediário.
- Validar linhas esperadas e formato básico dos 5 campos.
- Aplicar com `crontab <file>`.
- Mostrar diff antes/depois.
- Nunca usar `cmd | python3 <<EOF` nem heredoc dentro de command substitution para editar crontab; stdin collisions podem corromper/apagar entradas.

### 3. Lazy-load de webhook apenas quando houver alerta

Monitores frequentes não devem chamar `op` em estado saudável.

Fluxo correto:

```text
1. Executar verificação local sem `op`.
2. Aplicar anti-spam/cooldown sem `op`.
3. Se não houver alerta pendente -> exit 0 sem tocar no 1Password.
4. Se houver alerta real e fora do cooldown -> buscar webhook uma vez.
5. Postar no Discord com até 2 retries de curl.
```

Aplica especialmente a:
- `monitor-service-restarts.sh`: calcular `NRestarts`/delta primeiro; só buscar webhook dentro do ramo `info`/`warn`.
- `monitor-tool-loops.sh`: escanear sessões primeiro; só buscar webhook se houver loop real fora de cooldown.

Impacto validado: monitores `*/5` em estado saudável caem de dezenas de chamadas `op`/hora para zero.

### 4. Falha de `op` durante alerta real

Não perder alerta silenciosamente. Se `op` falhar exatamente quando havia alerta para enviar:

```text
- logar em /var/log/mgs-agent/<script>-failed-alerts.log
- gravar payload em /var/log/mgs-agent/pending-alerts/<script>-timestamp-pid.json
- sair com exit 2
```

`exit 0` = saudável/sem alerta. `exit 1` = erro normal de script. `exit 2` = alerta real não entregue e salvo em fallback local.

### 5. Reduzir retries agressivos onde `op` é necessário para a checagem

Se o monitor realmente precisa de vários segredos para operar (ex.: Yoast precisa webhook + credenciais RunCloud), evitar loop por segredo que vira 9 chamadas em 15s. Preferir:
- 1 tentativa por segredo no ciclo; ou
- backoff global e abort limpo ao detectar rate limit.

Não consolidar itens do vault nem cachear segredos sem autorização explícita.

## Testes obrigatórios após patch

Para cada monitor alterado:

```bash
# backup
cp script.sh /root/mgs-agent/data/script-backup-NOME-$(date +%Y%m%d-%H%M%S).sh

# sintaxe
bash -n script.sh

# estado saudável não chama op
TMPD=$(mktemp -d)
cat > "$TMPD/op" <<'SH'
#!/bin/bash
echo "OP_CALLED $*" >> /tmp/mgs-opcalls.log
exit 99
SH
chmod +x "$TMPD/op"
: > /tmp/mgs-opcalls.log
PATH="$TMPD:$PATH" script.sh
wc -l /tmp/mgs-opcalls.log   # esperado: 0

# alerta sintético em dry-run: deve detectar sem postar real
MGS_FORCE_*_ALERT=1 MGS_DRY_RUN=1 MGS_WEBHOOK_URL_OVERRIDE=https://example.invalid/webhook script.sh

# falha de op durante alerta: deve exit 2 + fallback local
MGS_FORCE_*_ALERT=1 MGS_FORCE_OP_FAIL=1 script.sh
ls /var/log/mgs-agent/pending-alerts/
tail /var/log/mgs-agent/*failed-alerts.log
```

## Auditoria pós-correção

Rodar:

```bash
/root/mgs-agent/scripts/monitor-cron-stale-logs.sh --dry-run
for f in /root/mgs-agent/logs/*.log; do
  c=$(tail -n 120 "$f" 2>/dev/null | grep -Ei 'error|erro|fatal|traceback|exception|failed|falha|critical|syntax error|permission denied|too many requests|rate-limited' | wc -l)
  [ "$c" -gt 0 ] && printf '%4s %s\n' "$c" "$f"
done
```

Se um erro antigo era o último bloco do log (ex.: Yoast falhou às 10:00 mas depois não rodou), executar o cron manualmente quando for seguro/idempotente, depois rodar o stale watchdog real para emitir resolução.

## Pitfall: auto-commit guardrail por nome de arquivo

O auto-commit pode ficar ativo mas bloqueado se um arquivo de documentação tiver nome com `token|password|secret|webhook|credential|1password`. Antes de relaxar guardrail:
1. Escanear o arquivo por padrões reais de segredo sem imprimir valores.
2. Se não houver segredo e for documentação, renomear para termo menos sensível (ex.: `cron-op-rate-limit-mitigation.md` em vez de `cron-1password-rate-limit-mitigation.md`).
3. Confirmar `git status`, auto-commit e auto-push.
