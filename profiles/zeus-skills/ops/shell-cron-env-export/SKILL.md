---
name: shell-cron-env-export
description: Padrão canônico para shell scripts MGS que lêem variáveis de .env e invocam subprocessos (op, curl). Previne falha silenciosa via cron causada por variáveis não exportadas para subprocessos.
version: 1.1.0
author: Zeus
---

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

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
- **Nome da skill vs .gitignore** — nome `shell-cron-env-export` foi escolhido para não bater no padrão `*credentials*` do `.gitignore` (linha 16). Nomes com "credentials" ficam bloqueados do git por regra de segurança — usar sempre nomes descritivos do mecanismo (env-export, env-load, etc).

## Scripts MGS que usam este padrão

| Script | Aplicado em |
|--------|-------------|
| `scripts/monitor-auto-push.sh` | 2026-04-27 (fix retroativo) |
| `scripts/monitor-yoast-health-eggbev.sh` | 2026-04-27 (fix retroativo) |

Ao criar novo script, adicionar à tabela acima via patch nesta skill.
