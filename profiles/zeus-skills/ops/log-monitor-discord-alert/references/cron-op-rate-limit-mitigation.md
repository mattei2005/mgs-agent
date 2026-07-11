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

## Monitor canônico de rate limit do Service Account

Use `op service-account ratelimit --format=json` como probe oficial. Ele retorna budgets independentes de leitura horária por token, escrita horária por token e leitura/escrita diária por conta. No plano Business, os limites são 10.000 leituras/hora, 1.000 escritas/hora e 50.000 requisições/dia por conta.

Padrão recomendado:

- Executar a cada 15 minutos, com minuto escalonado e `flock -n`.
- Alertar amarelo em 70% e crítico em 90%, separando budget horário e diário.
- Persistir state e cooldown; só reenviar ao cruzar faixa, após cooldown ou na resolução.
- Enviar pelo bot Zeus/Discord REST usando a credencial já local do profile, não buscar o webhook no próprio 1Password. Um monitor dependente do `op` para obter o canal falha justamente quando o limite esgota.
- Nunca imprimir token ou valores de itens; reportar apenas `used`, `limit`, `remaining`, percentual e horário de reset.
- Antes de instalar: backup do crontab, arquivo intermediário validado, smoke test real, atualização de `docs/CRONS.md`, inventário, audit log e REPORT-INFRA.

### Diagnóstico de consumo acelerado

A documentação oficial do CLI informa:

- `op item get` por nome: 3 leituras; com IDs do item e vault: 1.
- `op read` por nome: 3 leituras; com IDs: 1.
- `op item list --vault <nome>`: até 3 leituras; com vault ID: 2.

Se o contador subir rapidamente, não atribuir automaticamente ao monitor. Inspecionar processos `op` ativos e sua árvore de pais para localizar uma operação concorrente. Em loops/batches, resolver vault/item IDs uma vez e reutilizá-los; não fazer probes de vários campos com chamadas separadas.

### Migração para conta Business

Um token criado na conta pessoal não acessa vaults da Business. Criar um novo Service Account dentro da Business, conceder somente os vaults necessários e permissões mínimas de leitura, desabilitar criação de vaults e atualizar `OP_SERVICE_ACCOUNT_TOKEN` no env central. Acesso e permissões são imutáveis; se faltar vault ou permissão, é necessário criar outro Service Account.

Validar sem expor segredos: identidade, vault visível, contagem de itens, uma leitura real reportada apenas por status/comprimento e o budget de 50.000/dia. Criar outro token só contorna limite horário por token; não contorna limite diário por conta.

## Pitfall: auto-commit guardrail por nome de arquivo

O auto-commit pode ficar ativo mas bloqueado se um arquivo de documentação tiver nome com `token|password|secret|webhook|credential|1password`. Antes de relaxar guardrail:
1. Escanear o arquivo por padrões reais de segredo sem imprimir valores.
2. Se não houver segredo e for documentação, renomear para termo menos sensível (ex.: `cron-op-rate-limit-mitigation.md` em vez de `cron-1password-rate-limit-mitigation.md`).
3. Confirmar `git status`, auto-commit e auto-push.

## Monitor dedicado MGS — conta Business

Artefatos canônicos:

- Script: `/root/mgs-agent/scripts/monitor-op-rate-limit.py`
- State: `/root/mgs-agent/data/op-rate-limit-monitor.json`
- Log: `/root/mgs-agent/logs/monitor-op-rate-limit.log`
- Canal Discord: `1passw-rate-limit` (`1525311777208926398`)
- Cron: `9,24,39,54 * * * *` com `flock -n`

Política confirmada por Rodolfo em 2026-07-10:

- Primeiro alerta somente quando qualquer janela atingir **50%**.
- Alerta crítico com mention em **90%**.
- Alertar apenas em transição de estado; emitir resolução quando voltar abaixo de 50%.
- A consulta `op service-account ratelimit` consome uma requisição simples. A cada 15 minutos, o monitor adiciona no máximo 96 requisições/dia, ou 0,192% do limite Business de 50.000.
- Enviar pelo token local do bot Zeus, não por webhook buscado no próprio 1Password; o alerta precisa continuar funcionando mesmo quando o 1Password estiver bloqueado.
- O smoke test real deve validar `message_id` e `channel_id` retornados pela API Discord sem imprimir tokens.
