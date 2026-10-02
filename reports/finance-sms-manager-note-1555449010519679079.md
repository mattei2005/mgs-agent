# Nota SMS Funnel nas telas de gestores — setembro 2026

Autoridade: Rodolfo `1555449010519679079`; thread `1554520572950618173`.

## Entrega

O card `Resultado líquido` das cinco visões de gestor agora mostra uma nota contextual no espaço vazio à direita:

- título `Ajuste SMS Funnel · setembro`;
- recarga de `R$ 95.000,00` preservada separadamente e fora do rateio das Despesas Gerais;
- consumo direto daquele gestor no Creditoparaveiculo;
- confirmação de que o custo já está descontado do resultado líquido e que a remuneração foi recalculada.

Valores exibidos, derivados do workspace vivo:

- Ícaro: `R$ 12.449,04`.
- Isliago: `R$ 30.749,04`.
- Joe: `R$ 15.972,96`.
- Kelly: `R$ 41.009,60`.
- Nicolas: `R$ 2.759,60`.

Nenhum valor foi hardcoded no navegador. A API de gestor cria `direct_cost_note` somente quando encontra `direct_monthly_cost` do gestor na competência e usa período, site, custo BRL, recarga reclassificada e autoridade do próprio workspace. Sem custo direto, o card permanece sem nota.

## Layout

- Desktop: valores à esquerda e caixa informativa azul-clara à direita dentro do card de resultado.
- Mobile: caixa abaixo dos valores.
- A nota não altera nem compete com o card `Remuneração atual`.
- Fundo `#f4f7fc`, borda discreta e barra lateral azul.

## Segurança financeira

- Implantação somente de código/UI.
- Hash financeiro de cenários, ledger e histórico permaneceu idêntico no cutover.
- Nenhuma planilha, valor, comissão, pagamento, ajuste ou ledger foi escrito.
- Gateway Hermes não foi reiniciado.

## Validação

- RED/GREEN de API e apresentação: 21 testes focados PASS.
- Stage isolado: PASS.
- Produção: cinco gestores × desktop/mobile = 10 verificações PASS.
- Zero overflow do card/nota.
- Zero erros JavaScript.
- Zero falhas same-origin.
- Serviço, socket e PostgreSQL ativos.

## Backup e rollback

- Backup local/remoto: `/home/zeus/mgs-finance-backups/sms-manager-note-1555449010519679079/code-before.tar.gz`.
- SHA256: `dcdec2491881a43902ad46807d6784a338b55c6979d05aafd83bc86683c30b11`.
- Stage: `/var/tmp/mgs-finance-sms-manager-note-1555449010519679079`.

## Evidência

Diretório: `apps/finance-system/private/sms-manager-note-1555449010519679079/`.

Arquivos principais: `prepared.json`, `stage.json`, `published.json`, `public-browser.json`.
