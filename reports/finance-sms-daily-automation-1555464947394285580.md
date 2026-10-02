# Finance SMS Funnel — consumo diário e crédito pré-pago

Autoridade: Rodolfo `1555464947394285580`  
Thread: `1554520572950618173`  
Período inicial: outubro/2026  
Estado: publicado e validado

## Resultado contábil

- A Dash financeira usa o total oficial consumido no SMS Funnel: **57.565 mensagens `sent=true`** em 01/10/2026.
- Custo unitário: **R$ 0,08**.
- Despesa direta reconhecida: **R$ 4.605,20**.
- O valor de **50.259 mensagens / R$ 4.020,72** vem da análise agregada por campanhas e permanece somente como conferência auxiliar do coletor legado WordPress; ele não entrou no resultado financeiro.
- A recarga de **R$ 68.000,00** foi registrada como crédito pré-pago confirmado, fora do resultado.
- Nenhum pagamento ou transferência foi executado.

## Atribuição financeira

- G001: 6.945 mensagens / R$ 555,60.
- G002: 222 mensagens / R$ 17,76, sem comissão externa.
- G003: 15.368 mensagens / R$ 1.229,44.
- G004: 6.448 mensagens / R$ 515,84.
- G005: 25.776 mensagens / R$ 2.062,08.
- G006: 2.806 mensagens / R$ 224,48.
- Fechamento: 6/6 gestores, 57.565 mensagens e R$ 4.605,20; zero sequência sem atribuição.

## Estrutura publicada

- Recarga e consumo são fatos distintos.
- `prepaid_credit` não reduz o resultado.
- `direct_daily_cost` reduz o resultado do Creditoparaveiculo e do gestor correto, sem ser mídia.
- O custo permanece fixo em BRL.
- A coluna `Despesa direta SMS` está presente no consolidado e nas telas dos cinco gestores.
- Setembro preserva o ajuste mensal no TOTAL, sem inventar um dia.
- Outubro usa consumo diário real.
- Importação financeira é idempotente, guarda `source_bundle_sha256`, revisão e audit ID.

## Automação

- Cron final: `8 9 * * *`, timezone `America/New_York`.
- Cadeia: gastos `09:03` → SMS `09:08` → receita GAM `09:22`.
- O pós-cutover global de oito dias encontrou zero colisão operacional; somente baselines contínuos de infraestrutura coincidem.
- O GAM também executa a etapa SMS de recuperação quando o state do dia não está pronto.

## Validação

- Execução natural de 02/10/2026: `SYNC_OK`.
- Readback financeiro: 57.565 mensagens, 460.520 centavos, audit `2829`, idempotente.
- Banco vivo: revisão `86`, 6 custos diários, 57.565 mensagens, R$ 4.605,20, 1 crédito pré-pago de R$ 68.000,00.
- Hashes locais e publicados: iguais nos 13 arquivos do release.
- Serviços: `mgs-finance-dash`, socket e PostgreSQL ativos.
- Testes atuais: Node 25/25 PASS; Python 7/7 PASS.
- Browser autenticado: setembro e outubro, Ícaro/Isliago/Joe/Kelly/Nicolas, desktop e mobile, 20/20 verificações, zero overflow, zero erro JavaScript e zero requisição same-origin falha.
- Interface de outubro exibiu `Créditos pré-pagos SMS Funnel`, R$ 68.000,00, `Não reduzem o resultado` e `Despesa direta SMS`.

## Evidência e rollback

- Contrato: `data/finance-sms-usage-contract.json`.
- State: `data/finance-sms-usage-state.json`.
- Evidência privada: `apps/finance-system/private/sms-usage-prepaid-1555464947394285580/`.
- Planos: `work/finance-sms-automation-20261002/`.
- Backup remoto: `/home/zeus/mgs-finance-backups/sms-usage-prepaid-1555464947394285580`.
