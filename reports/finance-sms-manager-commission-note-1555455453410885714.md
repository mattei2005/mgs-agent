# Nota SMS Funnel com comissão antes/depois — setembro 2026

Autoridade: Rodolfo `1555455453410885714`; thread `1554520572950618173`.

## Correção

A nota no card `Resultado líquido` foi ampliada para explicar a sequência financeira completa:

1. A recarga de R$95.000,00 fazia parte das Despesas Gerais.
2. A recarga foi preservada fora do resultado.
3. O consumo real passou a ser atribuído diretamente por gestor no Creditoparaveiculo.
4. A tela mostra `Comissão antes`, `Impacto do ajuste` e `Comissão depois`.
5. O consumo direto do gestor continua visível e é explicitado como já incluído no resultado líquido.

Os valores de antes/depois não são hardcoded. A API consulta o audit financeiro `SMS_DIRECT_COST_RECONCILED`, usa o delta de comissão registrado na aplicação e aplica esse delta à remuneração viva da competência. A identidade da fonte permanece rastreável pela autoridade da reclassificação.

## Readback público

Snapshot no momento da validação, sujeito ao câmbio provisório:

- Joe: antes R$3.507,20; impacto −R$474,56; depois R$3.032,64; consumo R$15.972,96.
- Nicolas: antes R$27.212,94; impacto +R$1.256,29; depois R$28.469,23; consumo R$2.759,60.
- Isliago: antes R$15.088,60; impacto −R$1.542,64; depois R$13.545,96; consumo R$30.749,04.
- Kelly: antes R$5.988,33; impacto −R$2.012,61; depois R$3.975,72; consumo R$41.009,60.
- Ícaro: antes R$3.000,00; impacto R$0,00; depois R$3.000,00; consumo R$12.449,04.

Cada ponte passou a igualdade em centavos `antes + impacto = depois`.

## Layout

- Desktop: valores do resultado à esquerda; explicação à direita.
- A explicação usa três blocos compactos: antes, impacto e depois.
- Impacto negativo aparece em vermelho; positivo em verde.
- Mobile: nota abaixo do resultado e os três blocos empilhados quando necessário.

## Segurança e validação

- Deploy somente leitura/API/UI; nenhum dado financeiro foi escrito.
- Cenários, ledger e histórico permaneceram byte-identical no cutover.
- 21 testes focados PASS.
- Stage isolado PASS.
- Produção: 5 gestores × desktop/mobile = 10 verificações PASS.
- Zero overflow, zero erros JavaScript e zero falhas same-origin.
- Serviço, socket e PostgreSQL ativos.
- Gateway Hermes não foi reiniciado.

## Backup e evidência

- Backup: `/home/zeus/mgs-finance-backups/sms-manager-commission-note-1555455453410885714/code-before.tar.gz`.
- SHA256: `b48bfb09189ef7275c8d6a2a6acd71bfa91a08115990c124a85cb3285133b047`.
- Stage: `/var/tmp/mgs-finance-sms-manager-commission-note-1555455453410885714`.
- Evidência: `apps/finance-system/private/sms-manager-commission-note-1555455453410885714/`.
