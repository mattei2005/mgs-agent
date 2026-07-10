# Caso: monitor Hermes updates abortava antes de logar estado

## Sintoma

`monitor-cron-stale-logs.sh` alertava `monitor-hermes-updates.sh` como `STALE`; o log-alvo estava vazio/antigo, mas o cron existia e o `flock` não estava preso.

## Diagnóstico reutilizável

1. Validar sintaxe: `bash -n scripts/monitor-NOME.sh`.
2. Rodar manualmente com timeout e checar exit code.
3. Se aborta cedo sem log útil, criar cópia instrumentada temporária com trap de erro:

```bash
trap 'rc=$?; echo "ERR line=${LINENO} rc=${rc}" >&2' ERR
```

4. Corrigir a linha apontada; repetir até `exit=0`.
5. Rodar o watchdog em dry-run para confirmar que o stale desapareceu.

## Causas encontradas neste caso

- `git log ... --grep="security\\|sec(" -iE` falhava por regex/flag inválida.
- `git log ... | head -5 | sed ...` falhava com `rc=141` sob `set -euo pipefail` por SIGPIPE do `head`.
- O script só escrevia log no fim; quando abortava antes, parecia que o cron nunca tinha rodado.

## Correção padrão

- Usar flags longas do Git: `--regexp-ignore-case --extended-regexp`.
- Proteger pipelines truncados:

```bash
TOP_ITEMS=$( { comando-produtor | head -5 | sed '...'; } || true )
```

- Logar início logo após definir a função de log:

```bash
log "START monitor-NOME"
```

## Validação esperada

```text
bash -n scripts/monitor-NOME.sh                      -> exit 0
scripts/monitor-NOME.sh                              -> exit 0
scripts/monitor-cron-stale-logs.sh --dry-run         -> monitor-NOME | OK
```
