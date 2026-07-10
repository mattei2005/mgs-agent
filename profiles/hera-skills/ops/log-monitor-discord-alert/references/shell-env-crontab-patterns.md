# Shell Scripts com .env — Padrão de Export Canônico MGS

## Quando usar

Qualquer script shell MGS que:
- Lê credenciais de `/root/mgs-agent/.env` via `source`
- Invoca `op item get` (1Password CLI) como subprocesso
- Roda via cron (não apenas manualmente)

## O Problema

`source .env` carrega variáveis na shell atual, mas **não as exporta** para subprocessos. Quando o script invoca `op item get`, o `op` não vê `OP_SERVICE_ACCOUNT_TOKEN` e retorna `"not signed in"`. Com `set -euo pipefail`, o script morre silenciosamente — sem log, sem erro visível.

**Por que não aparece em testes manuais:** Em sessão interativa, a sessão `op` pode estar cacheada no ambiente atual. Via cron, o ambiente é limpo — `op` sempre precisa do token explicitamente exportado.

## A Solução: set -a / set +a

```bash
# ─── Credenciais via 1Password ────────────────────────────────
# shellcheck source=/dev/null
set -a                                        # auto-export tudo que seguir
source "${BASE_DIR}/.env" 2>/dev/null || true # carrega + exporta variáveis
set +a                                        # desliga auto-export
```

`set -a` faz com que toda variável atribuída (ou carregada via source) seja automaticamente exportada para subprocessos. `set +a` restaura o comportamento padrão.

## Template de Cabeçalho Canônico

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/..)" && pwd)"

# ─── Credenciais via 1Password ────────────────────────────────
# shellcheck source=/dev/null
set -a
source "${BASE_DIR}/.env" 2>/dev/null || true
set +a

# A partir daqui, OP_SERVICE_ACCOUNT_TOKEN e demais vars estão
# disponíveis para qualquer subprocesso (op, curl, etc.)
```

## Como Validar (cron-like)

Simular ambiente limpo do cron antes de confiar que funciona:

```bash
# Teste cron-like — deve retornar Exit 0 sem erro de "not signed in"
env -i HOME=/root PATH=/usr/bin:/bin:/usr/local/bin bash /root/mgs-agent/scripts/meu-script.sh 2>&1 | head -10
echo "Exit: $?"
```

**Não confiar** em testes com `bash meu-script.sh` direto — sessão `op` cacheada mascara o bug.

## Pitfalls

- **Testes manuais passam, cron falha** — causa sempre é `source` sem `set -a`. O `op` usa sessão cacheada do ambiente interativo.
- **Falha silenciosa com `set -euo pipefail`** — variável vazia em expansão (`${WEBHOOK_URL}`) mata o script sem mensagem se `nounset` estiver ativo.
- **`set -a` deve ficar antes do source, `set +a` depois** — não depois de outras atribuições que você não quer exportar.
- **Aplicar em TODOS os scripts MGS que usam `op`** — não apenas nos monitorados. Bug recorrente: `monitor-auto-push.sh` e `monitor-yoast-health-eggbev.sh` foram afetados (2026-04-27).
- **Nome da skill vs .gitignore** — nomes com "credentials" ficam bloqueados do git por regra de segurança — usar sempre nomes descritivos do mecanismo (env-export, env-load, etc).

## 🚨 Padrão Proibido — Configs Críticas (crontab, etc.)

**NUNCA usar heredoc dentro de `$()` seguido de operação destrutiva:**

```bash
# PADRÃO PERIGOSO — incidente MGS 02/05/2026:
NEW=$(crontab -l | python3 << EOF
...código Python...
EOF)
echo "$NEW" | crontab -   # SE $NEW vazio -> apaga tudo sem erro!
```

**Por que falha:** Python heredoc dentro de `$()` pode falhar silenciosamente → `$NEW` fica vazio → `echo "" | crontab -` aceita stdin vazio sem aviso e apaga o crontab inteiro.

**Padrão seguro obrigatório para configs críticas (crontab, systemd, nginx, etc.):**

```bash
# PADRÃO SEGURO:
BACKUP="/tmp/crontab-$(date +%Y%m%d_%H%M%S).bak"
crontab -l > "$BACKUP"                        # 1. backup com timestamp
[[ -s "$BACKUP" ]] || { echo "ERRO: backup vazio"; exit 1; }

# Gerar novo conteúdo em arquivo intermediário (NUNCA em $())
python3 script.py < "$BACKUP" > /tmp/crontab-new.txt

# 2. Validar antes de aplicar
NEW_SIZE=$(wc -c < /tmp/crontab-new.txt)
OLD_SIZE=$(wc -c < "$BACKUP")
[[ $NEW_SIZE -gt $((OLD_SIZE - 100)) ]] || { echo "ERRO: tamanho suspeito"; exit 1; }
[[ $(wc -l < /tmp/crontab-new.txt) -ge $(wc -l < "$BACKUP") ]] || { echo "ERRO: linhas reduziram"; exit 1; }

# 3. Mostrar diff antes de aplicar
diff "$BACKUP" /tmp/crontab-new.txt || true

# 4. Aplicar so apos validacao
crontab /tmp/crontab-new.txt
```

Mesma logica se aplica a: overwrite de `.env`, substituicao de configs systemd — qualquer operacao onde "arquivo vazio = desastre".

## Scripts MGS que usam este padrão

| Script | Aplicado em |
|--------|-------------|
| `scripts/monitor-auto-push.sh` | 2026-04-27 (fix retroativo) |
| `scripts/monitor-yoast-health-eggbev.sh` | 2026-04-27 (fix retroativo) |
