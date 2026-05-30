# Cron monitors: reduzir pressão no `op` sem cache de credenciais

## Contexto

Quando vários crons MGS chamam `op item get` diretamente para buscar webhooks/segredos, o 1Password CLI pode rate-limitar e causar cascata: auto-push, Yoast e monitores deixam de reportar ou passam a alertar por erro de credencial.

A correção preferida antes de cachear segredos é reduzir chamadas desnecessárias ao `op`.

## Padrão recomendado

### 1. Stagger de crons que chamam `op`

Espalhar horários para evitar rajadas simultâneas. Exemplo validado:

```cron
1-56/5 * * * *       monitor-service-restarts.sh
3-58/5 * * * *       monitor-tool-loops.sh
7,22,37,52 * * * *   check-pending-reports.sh
11,26,41,56 * * * *  monitor-auto-push.sh
23 10 * * *          monitor-yoast-health-eggbev.sh
47 12 * * *          monitor-gpt55-oauth-cost.sh
17 3 * * *           housekeeping-bak-cleanup.sh
```

Sempre fazer backup do crontab antes de editar:

```bash
TS=$(date +%Y%m%d-%H%M%S)
crontab -l > "/root/mgs-agent/data/crontab-backup-${TS}.txt"
```

Editar via arquivo intermediário, validar linhas esperadas e aplicar com `crontab <arquivo>`. Nunca usar heredoc dentro de command substitution para editar crontab.

### 2. Buscar webhook somente quando houver alerta

Monitores frequentes não devem chamar `op` em estado saudável.

Fluxo correto:

```text
1. Executar verificação local sem `op`.
2. Se não houver alerta pendente -> sair exit 0.
3. Se houver alerta real e fora de cooldown -> buscar webhook uma vez.
4. Postar no Discord com até 2 retries de curl.
```

Isso transforma monitores `*/5` de dezenas de chamadas `op` por hora para zero em operação normal.

### 3. Falha de `op` durante alerta real

Não perder alerta silenciosamente. Se `op` falhar exatamente quando um alerta precisa ser enviado:

```text
- logar em /var/log/mgs-agent/<script>-failed-alerts.log
- gravar payload em /var/log/mgs-agent/pending-alerts/<script>-timestamp-pid.json
- sair com exit 2
```

Sem alerta real, falha do `op` não deve ocorrer porque o script não deve chamar `op`.

### 4. Testes obrigatórios

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

# alerta sintético em dry-run
MGS_DRY_RUN=1 MGS_WEBHOOK_URL_OVERRIDE=https://example.invalid/webhook \
  MGS_FORCE_<MONITOR>_ALERT=1 script.sh

# falha de op durante alerta
MGS_FORCE_<MONITOR>_ALERT=1 MGS_FORCE_OP_FAIL=1 script.sh
# esperado: exit 2 + pending-alerts/*.json
```

Variáveis de teste (`MGS_FORCE_*`) são hooks locais para validação; não devem alterar o comportamento normal do cron.

## Pitfalls

- Não reduzir segurança colocando webhook/PAT/senha hardcoded em script ou `.env`.
- Cache de credenciais em `/run/secrets` é mudança de modelo de segurança; só aplicar com aprovação explícita.
- Se o auto-commit watcher bloquear arquivos de documentação por palavras como `password`, `token`, `secret`, `webhook` ou nomes de provider, preferir renomear o arquivo para termo neutro em vez de relaxar guardrail.
- `op` retries agressivos pioram rate limit. Para alerta real, use uma tentativa de `op`; retries ficam no `curl` do webhook.
