# Hermes script-only timeout guard for Meta intraday crons — 2026-06-19

## Contexto

O cron `Ares Meta intraday R1-R5 dry-run` (`job_id: aa9e01a5ec4a`) começou a postar em `logs-aquisicao` erro bruto do scheduler:

```text
Cron job 'Ares Meta intraday R1-R5 dry-run' failed:
Script timed out after 120s: /root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh
```

O token Meta estava válido e o auth check read-only retornava HTTP 200. O problema era a combinação de:

- job Hermes `no_agent=true` com timeout fixo de 120s;
- runner Meta com backoff/rate-limit potencialmente maior que a janela do scheduler;
- wrapper que deixava o scheduler matar o script, gerando alerta bruto e sem contexto operacional limpo.

## Padrão aplicado

No wrapper script-only do perfil (`/root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh`):

1. Definir limites de backoff abaixo da janela do scheduler:

```bash
export ARES_META_RATE_LIMIT_MAX_TOTAL_SLEEP="${ARES_META_RATE_LIMIT_MAX_TOTAL_SLEEP:-45}"
export ARES_META_RATE_LIMIT_INITIAL_SLEEP="${ARES_META_RATE_LIMIT_INITIAL_SLEEP:-10}"
```

2. Rodar o runner sob `timeout` menor que 120s:

```bash
timeout 110s /root/mgs-agent/scripts/ares-meta-cron-runner.py \
  --job intraday \
  --operation-id OpenzedFinanzas-CC-ES \
  --account-id 1356770869843984 \
  --account-tz Europe/Madrid >"$TMP" 2>"$ERR"
```

3. Se o runner sair por timeout ou erro, substituir por mensagem sanitizada para Discord, mantendo `dry-run/read-only` explícito.
4. Se houver output, postar via `/root/mgs-agent/scripts/ares-discord-post-with-thread.py`; se esse post falhar, devolver o conteúdo sanitizado para o scheduler entregar.
5. Encerrar o wrapper com `exit 0`, porque erros operacionais já viraram alerta limpo + audit local. Isso evita que o Hermes gere `Cronjob Response ... failed` bruto.

## Validação usada

- `bash -n /root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh`
- runner bounded com `ARES_META_RATE_LIMIT_MAX_TOTAL_SLEEP=45 ARES_META_RATE_LIMIT_INITIAL_SLEEP=10 timeout 120s ...`
- audit intraday gerado com `errors=[]`, `campaigns_seen`, `insight_rows`, `candidate_count`.
- `cronjob list` para confirmar job habilitado/agendado.
- `REPORT-INFRA` no `#alerts-infra` porque script persistente foi alterado.

## Pitfall

Em crons script-only Hermes, não basta o runner tratar rate-limit internamente: se o tempo total puder passar de 120s, o scheduler interrompe antes do runner produzir erro sanitizado. O wrapper precisa controlar o tempo total e converter timeout local em mensagem operacional limpa.
