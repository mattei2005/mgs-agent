# Pitfalls operacionais atuais — Meta Ads

## Conta e token

- Nunca usar token global implícito. O item 1Password vem de `accounts/<account_id>.json` ou argumento explícito.
- Cache válido não prova acesso à conta; auth check read-only precisa retornar a conta solicitada.
- Não imprimir token. Audit registra somente item, campo, comprimento, HTTP e timestamps.

## Estado e escrita

- `status=ACTIVE` em campanha não garante entrega se adset/ad estiver pausado; preservar status hierárquico no audit.
- UI e API podem representar deleted/archived de forma diferente; declarar o mapeamento específico da operação.
- Timeout de POST não é autorização para repetir. Reconciliar campanha, adset, creative e ad antes de retry.
- Objeto parcialmente criado deve ser retomado pelos IDs persistidos; cleanup nunca atinge source nem objetos de outra request.
- Campanha nova nasce PAUSED salvo autorização explícita.

## Tempo, moeda e métricas

- `today` usa timezone da conta. VPS e UTC servem só para audit.
- Confirmar unidade monetária antes de normalizar budget, spend ou balance.
- Métrica e fórmula vêm do contrato; ausência de action não pode virar zero válido sem regra explícita.
- Receita externa pode ter atraso; declarar freshness e janela do join.

## Rate limit e payload

- Começar com campos mínimos e expandir por ID/lote pequeno.
- Não pedir `object_story_spec` em massa.
- Aplicar throttle e backoff limitado; erro de parâmetro/compliance não recebe retry.

## Discord e cron

- Usar thread fixa registrada e não criar substituta por conveniência.
- Wrapper que publica diretamente usa `deliver=local`, stdout vazio e IDs persistidos para evitar duplicidade.
- Mensagem operacional não inclui path, PID, trace bruto ou rodapé automático.
- Alteração de cron exige readback de schedule, script, enabled, no_agent e deliver.
