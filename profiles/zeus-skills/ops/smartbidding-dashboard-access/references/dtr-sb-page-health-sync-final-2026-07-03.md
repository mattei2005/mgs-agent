# DTR → SB page health sync — fluxo final validado (2026-07-03)

## Escopo

Use para varrer DigitalTRChat e sincronizar SmartBidding Messenger Page com códigos de erro no campo `NOTES`, restrições `#2022`, reconferência de páginas já restritas e reavaliação segura de `Blocked`.

## Nomes canônicos

- **Dashboard da SB**: `https://app.smartbiddingdigital.com` e API `https://api.jbfdigital.com.br/campaigns/Messenger`.
- **Dashboard do Bot**: `https://digitaltrchat.com` e derivados.

## Fonte de escopo

1. Ler a planilha live `gid=562940072`.
2. Incluir só bot users ativos.
3. Ignorar `Removidos acumulado = X`.
4. Se o `X` for removido depois, o usuário volta ao escopo no próximo run.
5. 1Password não define escopo; só fornece credenciais para usuários ativos da planilha.

## Rota correta na Dashboard do Bot

Para cada bot user ativo:

1. Logar na Dashboard do Bot.
2. Enumerar todos os seguradores/contas do topo.
3. Trocar segurador e validar que o contexto muda. Se campanhas/páginas ficam idênticas, não confiar nessa dimensão.
4. Listar páginas reais pelo seletor `search_page_id`.
5. Para cada página, consultar campanhas com `search_page_id=<page>`.
6. Pegar apenas o último campaign/report `Completed`.
7. Abrir `campaign_sent_status_data` e classificar o retorno.

Nunca usar varredura global de campanhas sem `search_page_id` para contar páginas ou rotular segurador. HTTP 200 no `account_switch` não prova que o dataset mudou.

## Classificação

- `Sent`: envio OK. Não escrever nada no `NOTES`.
- `#2022`: restrição temporária.
- `#2022 + outros`: restrição temporária + erro misto.
- `#10`, `#100`, `#551`, `PERMISSION`, `TOKEN`, `APP_DELETED`, `OTHER`.
- `SEM_COMPLETED`: sem último Completed/report válido.

## Atualização do NOTES

Regra validada por Rodolfo:

- Em 100% das páginas encontradas na varredura do Bot, todos os status da SB entram no escopo para anotação.
- Se o último report for `Sent`: não alterar `NOTES`.
- Se aparecer qualquer outro retorno/código/status: adicionar ao final do `NOTES` somente o código/status curto.
- Não apagar texto existente.
- Não duplicar código já presente no `NOTES`.

Exemplos:

```text
... - #2022
... - #10 - #100
... - PERMISSION
... - SEM_COMPLETED
```

Pitfalls técnicos validados:

- `PUT /campaigns/Messenger/update-many` persiste `STATUS`/`RESTRICTED_UNTIL`, mas pode ignorar `NOTES` silenciosamente. Para `NOTES`, usar a rota de save do modal: `POST /campaigns/Messenger` com os campos editáveis da linha obtida por `GET /campaigns/Messenger/{ID}`, depois validar readback.
- O save do modal pode retornar `201 Created`; tratar `200` e `201` como sucesso, desde que o readback confirme.
- Em algumas linhas `Blocked`, salvar `NOTES` e `STATUS=Broadcast` juntos via `POST /campaigns/Messenger` retorna HTTP 500. Fluxo seguro: primeiro salvar `NOTES` mantendo o status atual; depois aplicar `STATUS`/`RESTRICTED_UNTIL` via `update-many`; por fim validar readback.
- Usuário ativo na planilha com item 1Password sem campo de senha não deve derrubar o lote. Registrar erro de credencial para aquele usuário, pular e continuar.
- Lotes grandes precisam de checkpoints visíveis por usuário e por bloco de writes (`user_start`, `user_done`, `user_write N/total`) e opção de retomada (`--start-at`) para evitar execução cega e reprocessamento desnecessário. O append de `NOTES` deve ser idempotente para permitir retomada sem duplicar código.

## RESTRICTED_UNTIL

- Só aplicar se o último report do Bot tiver `#2022`.
- Vale para `#2022` puro e `#2022 + outros`.
- Aplicar:
  - `STATUS = Broadcast`
  - `RESTRICTED_UNTIL = mesma data informada pelo Bot`
- Não aplicar `RESTRICTED_UNTIL` para erro sem `#2022`.
- Não aplicar `RESTRICTED_UNTIL` para `Sent`.
- Validar readback.

## Reconferência das páginas já restricted na SB

1. Buscar na SB páginas com `STATUS=Broadcast` e `RESTRICTED_UNTIL >= hoje`.
2. Revalidar na Dashboard do Bot pelo método correto.
3. Se não tiver mais `#2022` no último report e houver evidência confiável (`Sent` ou erro sem `#2022`), limpar `RESTRICTED_UNTIL`.
4. Não limpar quando `SEM_COMPLETED`, sem match ou contexto ambíguo.

## On-hold

- Pela regra do Ciro, `On-hold` não envia broadcast.
- Não reativar automaticamente `On-hold` por DTR.
- Atualizar `NOTES` se houver erro/código aplicável.
- Se houver `#2022` em `On-hold`, reportar/tratar como caso separado antes de forçar status.

## Blocked

- Não reativar automaticamente por DTR.
- Para decidir se saiu de `Blocked`, abrir `https://www.facebook.com/{FB_PAGE_ID}`.
- Se a página abrir normalmente: pode mudar `STATUS=Broadcast`.
- Se aparecer “This content isn't available right now” ou equivalente: manter `Blocked`.
- Se ambíguo/falha: não mudar status, reportar.
- Ainda assim, atualizar `NOTES` com erro/código se houver. Se for `Sent`, não adicionar nota.

## Execução segura

1. Backup local da linha SB antes de cada write.
2. Canário obrigatório com write real + readback.
3. Só seguir lote após canário OK.
4. Se write retorna sucesso mas readback não bate, parar e corrigir endpoint. Não assumir sucesso.
5. Gerar Excel/JSON final com evidência por página.
6. Em lote full, imprimir checkpoints por usuário e por bloco de writes; se precisar interromper, retomar com `--start-at <email>`.
7. Cron só depois do lote validado.

## Script canônico

- `/root/mgs-agent/scripts/dtr-sb-page-health-sync.py`
- Wrapper: `/root/mgs-agent/scripts/dtr-sb-page-health-sync.sh`
- State: `/root/mgs-agent/data/dtr-sb-page-health-sync-state.json`
- Reports: `/root/mgs-agent/reports/dtr-sb-page-health-sync-*.xlsx`
- Logs: `/root/mgs-agent/logs/dtr-sb-page-health-sync.log`

Modo canário:

```bash
/root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply --user usuario@gmail.com --limit-accounts 1 --limit-pages 5 --max-writes 1
```

Modo full apply:

```bash
/root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply
```

Retomada depois de interrupção controlada:

```bash
/root/mgs-agent/scripts/dtr-sb-page-health-sync.sh --apply --start-at usuario@gmail.com
```

Cron futuro deve usar `flock`, reler planilha live e ficar quieto em no-op.
