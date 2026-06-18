# Meta Ads crons — dry-run, logging e token watchdog (2026-06-17)

## Contexto

Rodolfo ativou a operação inicial para `OpenzedFinanzas-CC-ES` com:

- intraday R1-R5 a cada 30 minutos;
- reativar-todas todos os dias às 00:30 no timezone da conta Meta (`Europe/Madrid`);
- logs no Discord `logs-aquisicao` (`1516887105543077949`);
- alerta de expiração do token Meta em `alerts-infra` (`1498132022634483894`).

## Padrão operacional validado

Os crons começam como **script-only / no_agent / dry-run**. Eles fazem leitura Meta, salvam audit local e só imprimem stdout quando houver ação candidata ou erro. Em estado saudável sem ação, ficam silenciosos para não poluir o canal.

```text
Cron                         | Padrão
-----------------------------|------------------------------------------------------------
Intraday R1-R5               | every 30m, deliver logs-aquisicao, dry_run_no_write
Reativar-todas               | daily 00:30 Europe/Madrid, deliver logs-aquisicao, dry_run_no_write
Token expiry watchdog        | daily, deliver alerts-infra, alerta só se inválido/<=7 dias
```

## Arquivos/scripts atuais

```text
Arquivo                                                              | Uso
---------------------------------------------------------------------|---------------------------------------------
/root/mgs-agent/scripts/ares-meta-cron-runner.py                     | runner comum dos crons Meta dry-run
/root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh       | wrapper Hermes script-only do intraday
/root/.hermes/profiles/ares/scripts/ares-meta-reactivate-all-cron.sh | wrapper Hermes script-only do reativar-todas
/root/mgs-agent/scripts/ares-meta-token-expiry-alert.py              | watchdog de expiração do token Meta
/root/.hermes/profiles/ares/scripts/ares-meta-token-expiry-alert.sh  | wrapper Hermes script-only do watchdog
```

## Jobs criados na sessão

```text
Job                                      | ID           | Destino
-----------------------------------------|--------------|-----------------------------
Ares Meta intraday R1-R5 dry-run         | aa9e01a5ec4a | discord:1516887105543077949
Ares Meta reativar-todas dry-run         | c6c737070d3f | discord:1516887105543077949
Ares Meta token expiry alert             | 709a29c99b3f | discord:1498132022634483894
```

IDs são evidência histórica; sempre use `cronjob(action="list")` antes de alterar/remover jobs, não confie em IDs antigos.

## Validação mínima antes de declarar sucesso

1. `python3 -m py_compile /root/mgs-agent/scripts/ares-meta-cron-runner.py`.
2. `bash -n` nos wrappers em `~/.hermes/profiles/ares/scripts/`.
3. Smoke intraday manual: deve salvar audit JSON; se não houver candidato, stdout deve ser vazio.
4. Smoke reativar-todas manual: deve listar candidatas em dry-run se houver campanhas pausadas; nunca executar write.
5. `cronjob(action="list")` para confirmar `repeat=forever`, `no_agent=True`, `deliver` correto.
6. Enviar `[REPORT-INFRA]` ao `alerts-infra` quando criar/modificar cron/script/data.

## Pitfalls aprendidos

- `schedule="30m"` no `cronjob.create` pode virar one-shot (`repeat=once`). Para recorrência, usar explicitamente `schedule="every 30m"` e validar `repeat=forever` via `cronjob(action="list")`.
- Para `reactivate-all` às 00:30 da conta, converter para o scheduler local/current offset. Em junho, `00:30 Europe/Madrid` = `18:30 America/New_York`, então cron `30 18 * * *`. Revalidar offset/DST se migrar para outra conta ou época do ano.
- Hermes cron script path deve ser relativo ao diretório `~/.hermes/profiles/ares/scripts/`; para scripts em `/root/mgs-agent/scripts/`, criar wrapper no diretório do profile.
- Não entregar logs a cada 30 minutos se nada aconteceu. O watchdog clássico é stdout vazio = silêncio; stdout não-vazio = mensagem entregue.
- Até Rodolfo aprovar `controlled_write`, os crons devem continuar sem write implementado. Write real precisa API POST + GET pós-ação + audit por campanha.
