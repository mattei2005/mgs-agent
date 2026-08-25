# Contrato genérico de relatórios Meta Ads

Este arquivo define somente a apresentação e as evidências mínimas. Métricas, horários, thresholds e ações vêm do contrato da operação.

## Cabeçalho obrigatório

```text
<Alias da conta> — <dd/mm/yyyy> — <HH:MM timezone da conta> — <tipo do relatório>
Período: <início–fim> | Moeda: <currency> | Fontes: <Meta e fontes externas aprovadas>
Modo: <read_only | dry_run | controlled_write>
```

## Conteúdo mínimo por campanha

```text
Camp | Nome operacional | Status | Início | Spend | Métrica principal | Custo/resultado | Ação | Motivo
```

Regras:

- Usar o alias curto da conta no título; IDs técnicos ficam no audit.
- `Camp` usa o identificador humano definido pela operação; nunca inventar número ausente.
- `Início` é data real `dd/mm/yyyy` no timezone da conta.
- Status operacional vem do nível campanha; inconsistência de adset/ad aparece como observação quando relevante.
- Métrica principal e custo/resultado usam os nomes e fórmulas do contrato da operação.
- Em `read_only/dry_run`, a ação deve ser simulada: `observaria`, `manteria`, `pausaria`, `reativaria`, `criaria` ou `não agiria`.
- Em `controlled_write`, mostrar ação executada e resultado do GET/readback.
- Sem ação/erro, o cron pode ficar silencioso quando o contrato permitir.
- Quando houver receita/ROI externo, declarar atraso da fonte, moeda, revenue share e fórmula líquida usada.
- Campanhas e linhas visíveis devem ter contagem reconciliada; não declarar totais que divergem da enumeração.

## Discord

- Usar bloco `text` com colunas alinhadas para consolidação desktop.
- Para operação que exigir visualização móvel, acrescentar cards verticais responsivos sem eliminar a tabela consolidada.
- Dividir mensagens por capacidade real do Discord sem cortar uma linha no meio.
- Usar a thread fixa do tipo de relatório quando registrada no contrato.
- Wrapper que publica diretamente usa cron `deliver=local` e stdout vazio para evitar duplicidade.
- Erro visível deve ser curto e sanitizado; detalhes técnicos ficam no audit/REPORT-INFRA.

## Audit mínimo

```text
operation_id, account_id, account_alias, mode, period, timezone, currency,
source_readbacks, campaigns_considered, rows_reported, action_candidates,
writes_attempted, writes_confirmed, errors, created_at
```

Nunca salvar token, cookie, senha ou payload secreto.
