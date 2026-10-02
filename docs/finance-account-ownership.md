# Finance — titulares, gestores e contas de anúncio

Dono: Rodolfo Mattei. Fonte: mensagem `1547048317853114438`; interpretação confirmada por `1547052028663169105`, thread `1545426987756298340`. Estado técnico canônico: cadastro `master-ad-accounts` e workspace do mês no PostgreSQL do Dash. Documento registra a decisão, não substitui readback live.

## Códigos de gestor
- G001 → Ícaro (namespace de cálculo histórico `george`; login público `icaro`).
- G002 → MGS (`SEM_COMISSAO`, sem criar funcionário/login/comissão).
- G003 → Isliago (`isliago`).
- G004 → Joe (`joe`).
- G005 → Kelly (`kelly`).
- G006 → Nicolas (`nicolas`).

## Sites MGS/G002 confirmados — 1547707970731638945

Rodolfo confirmou na revisão visual do Relatório Diário que **Cephyric, Escalatepower e Mavroa são todos MGS/G002**. No motor financeiro, manter `SEM_COMISSAO`: é a chave interna de G002/MGS sem funcionário/login/comissão, não pendência de atribuição. Na UI, exibir somente `MGS`, nunca `SEM_COMISSAO` como se fosse gestor distinto. Escopo atual da receita importada: Cephyric/FR, Escalatepower/US e Mavroa/US (`us-shein-es` já confirmado). A confirmação resolve gestor/titularidade financeira; não confirma status mensal ATIVO/INATIVO, cadastro de domínio, conta de anúncio ou mudança no rateio das despesas. Esses três sites permanecem com status de site a conferir até decisão separada.

## Boostingecon — 1548317688051277918

Boostingecon pode receber receita orgânica residual mesmo quando não está em operação. Desde setembro/2026, classificar `pl_digital-trust_boostingecon_us` como Boostingecon / US / `us-cc-en`, sempre MGS `g002-d`, exclusivamente estratégia de bot. O site fica `Não participa` do rateio das Despesas Gerais; receita e gastos continuam nos resultados. O token de placement é preservado literalmente na linhagem e não implica um TLD inventado.

## Vínculos confirmados e implantados em setembro de 2026
- `536294549227786` / Meta / `Vizioid-US-SHEIN-EN-01-G002` → Vizioid / US / MGS.
- `1583000095650153` / Meta / `Yolokfx-US-SHEIN-EN-02-G006` → Yolokfx / US / Nicolas.
- `2429758060563333` / Meta / `Yolokfx-US-SHEIN-EN-03-G005` → Yolokfx / US / Kelly.
- `781612907182683` / Meta / `Yolokfx-US-SHEIN-EN-04-G004` → Yolokfx / US / Joe.
- `787796726891306` / Meta / `Yolokfx-US-SHEIN-EN-05-G001` → Yolokfx / US / Ícaro.
- `1600310064116258` / Meta / `Yolokfx-US-SHEIN-EN-06-G003` → Yolokfx / US / Isliago.
- `5172498094` / Google Ads / `Mattei 1` → GameZoneAd / bloco US existente. Rodolfo não atribuiu um gestor específico a essa conta; não inventar um.
- `3188620887977617` / Meta / `Infinitynexx-MX-CC-ES-01` → Infinitynexx / MX / Joe / bloco principal (`AFV46:AFV52` no namespace interno da coleta1–7set).
- `1052719314075904` / Meta / `Infinitynexx-MX-CC-ES-01-G001` → Infinitynexx / MX / Ícaro / bloco complementar (`AFZ146:AFZ152` no mesmo namespace).

Vizioid já existia: reaproveitado, ativado em setembro e atribuído à MGS, sem duplicar o site ou a conta. Yolokfx continua um site compartilhado; a conta preexistente `7840111366055613` / `Yolokfx-US-SHEIN-EN-01-G002` continua MGS. Infinitynexx é de Joe; a conta de Ícaro não transfere a titularidade. Preservados os dois blocos financeiros existentes; não duplicar o site.

## Esclarecimento para outubro — Infinitynexx, Vizioid e Mattei 1

Fontes: Rodolfo na thread `1545426987756298340`, mensagens `1555556080736800779`, `1555557606343573565`, `1555557986905235507` e delimitação explícita `1555558065619730537`.

- **Somente no caso do Infinitynexx**, atribuir a George/Ícaro (G001) apenas quando o nome da conta de anúncio terminar em `-g001` (comparação sem distinguir maiúsculas/minúsculas; preservar o nome original). Não inferir gestor pela existência ou posição de um bloco financeiro. `3188620887977617` / `Infinitynexx-MX-CC-ES-01` permanece Joe; `1052719314075904` / `Infinitynexx-MX-CC-ES-01-G001` permanece George/Ícaro. Não estender essa condição particular a outros sites nem sobrescrever outros sufixos/atribuições explícitas por inferência.
- Vizioid `536294549227786` / `Vizioid-US-SHEIN-EN-01-G002`: operação `us-shein-en`, US, MGS/G002 confirmada.
- Mattei 1 `5172498094`: manter em outubro a mesma regra de setembro, GameZoneAd / destino US existente; sem inventar novo gestor.
- Este esclarecimento refina os vínculos aprovados acima e supersede qualquer interpretação de que o bloco financeiro, sozinho, atribui Infinitynexx a George/Ícaro. Não muda titularidade do site, histórico financeiro, status mensal ou rateio.
- **Clarificação resolvida por `1555559500260573236`:** Rodolfo confirmou que `t001` em `1555558299192135721` foi erro de digitação; o correto é `g001`. Somente para Infinitynexx: conta sem sufixo de gestor é Joe; conta com sufixo terminal `-g001` é Ícaro/George, a mesma pessoa. `t001` não é alias válido. Esta confirmação supersede a ressalva temporária de sufixo pendente, preservando o histórico das mensagens e os IDs já conhecidos.
- **Recuperação executada — `1555562222023999501`:** vínculos específicos de outubro de Mattei1, Infinitynexx/Joe e Vizioid/MGS aplicados; três lançamentos pendentes reconciliados com a fonte; replay de gastos sem mudança e sem exceções. Receita GAM01/10 aplicada em64grupos, revisão90/audit2866, último dia completo01/10. Dashboard/Relatório Diário autenticados passaram em desktop e móvel. Evidência: `reports/finance-oct01-recovery-1555562222023999501.md`. Esta conclusão supersede o estado documental anterior de correção pendente; não altera meses anteriores, status/rateio ou vínculos de outros meses.

## Continuidade mensal aprovada — 1555577386995552397

Rodolfo esclareceu que novas operações e mudanças podem surgir durante o mês. A preparação do próximo mês deve usar a configuração atualizada no **último dia do mês**, não uma cópia antecipada e congelada da configuração de hoje.

- Durante o mês, manter o cadastro e a descoberta diária normais; não adiar o reconhecimento de uma operação nova até o fechamento.
- No último dia, conferir contas, sites, países/operações e gestores vigentes, incluindo operações iniciadas no meio do mês. Somente depois transportar os vínculos confirmados para o mês imediatamente seguinte.
- Preservar alterações explícitas já cadastradas para o mês seguinte. Conflitos de negócio reais são isolados para esclarecimento; não escolher por inferência. Não propagar automaticamente para todos os meses futuros.
- Transportar configuração/cadastro validado, não receitas, gastos, pagamentos, saldos operacionais ou números realizados do mês anterior. Não reescrever histórico nem copiar cotações liquidadas como cotação nova.
- Antes de importar o primeiro dia, validar novamente destinos, moedas e abertura mensal; detectar alterações posteriores à conferência do último dia. Consulta API concluída não prova gastos completamente atribuídos.
- Aceitação obrigatória da implementação: simular outubro→novembro e dezembro→janeiro, operações adicionadas/alteradas no decorrer do mês, configuração específica no destino, preservação do mês anterior, receita/gasto/gestor e replay sem duplicação.
- **Implantação autorizada e concluída — `1555579357651537931`:** runner `scripts/finance-month-rollover.py` ativo, conferência/propagação no último dia às23:04:25 America/New_York, com noop nos demais dias; preflight obrigatório em `finance_media_spend_sync.py` antes da coleta/importação. Comparação e continuidade somente de sites e vínculos de contas, preservando alterações explícitas no destino; nenhuma cópia de movimentos financeiros. State separa continuidade de cadastro de mero recálculo da base SMS. Ainda não houve o disparo natural de31/10; calendário, execução, repetição e viradas foram ensaiados.
- **Setembro→outubro:** a recuperação inicial tinha corrigido apenas três contas; esta implementação completou mais oito vínculos mensais e três configurações de sites (titularidade Infinitynexx, Vizioid ativo/MGS e Yolokfx compartilhado com custos por gestor), com receita/mídia originais preservadas. Novembro não recebeu cópia antecipada dos vínculos de outubro.
- **Exclusão SMS explicitada na autorização:** jamais transportar a reconciliação de comissões maio–setembro, custos mensais históricos, ajustes de ledger ou a mensagem explicativa dos gestores para outubro+. Outubro e meses posteriores usam consumo diário verificado do SMS Funnel; crédito comprado é pré-pago, não despesa operacional. A referência antiga deR$30mil foi excluída do resultado pelo motor desde outubro, antes do rateio e cálculo dos gestores; histórico e créditos reais preservados. Registros de pagamento/saldo anterior seguem o ledger normal, sem lançar de novo a diferença histórica.
- Validação/rollback: `reports/finance-monthroll-1555579357651537931.md`;443testes, restore isolado, stage real de viradas,15competências,8vistas autenticadas e5gestores; sem duplicação. Esta conclusão supersede o estado anterior de política ainda não implementada.

## Limites de cálculo e UI
- Contas de anúncio: identidade, site e gestor, sem painel de gastos.
- Relatório Diário: gastos por conta/gestor/dia em moeda original, incluídos uma única vez na Mídia do site.
- Custos nativos de Yolokfx são atribuídos aos cinco gestores. A ponte é opt-in nesse site; contas já vinculadas ao grafo de origem não são debitadas novamente. Não inferir repartição de receitas a partir dos gastos.
- Prévia dos cinco gestores mostra os gastos diários de suas contas Yolokfx em bloco próprio, sem copiar fonte Sheets ou abrir novos acessos.
- Vínculos explícitos usam ID, site, país e segmento. Preferência pelo último destino não pode sobrepor uma atribuição explícita de Rodolfo.
- Meses anteriores e futuros não foram regravados. Setembro mantém rotina07:16Eastern+25s; futuro rollover requer preservar vínculos segundo contrato mensal, sem retropropagar dados.

## Evidência e supersessão
`apps/finance-system/private/account-managers-1547052028663169105/`: backup dual por hash e restore isolado, `stage.json`, `production.json`, `published.json`, `browser.json`, plano exato e testes.
- Nove registros existentes ajustados, zero duplicatas;14 campos financeiros antes pendentes preenchidos, sete Mattei1 e sete Infinitynexx/Joe.
- Readback de63 registros conta/dia nas nove contas; repetição com zero mudanças.
-88testes Node e3Python passaram;8visões em4sites (desktop/mobile),5prévias de gestor, zero erros JS.
- Agosto, histórico fechado, demais períodos, usuários e lançamentos de pagamento preservados. Vizioid ativo participa das cotas de rateio de setembro conforme mecanismo preexistente; não houve alteração da regra de rateio.

As pendências antigas “Mattei1 sem destino” e “Infinitynexx-MX-CC-ES-01 ambígua” estão **explicitamente supersedidas** pela decisão acima e pelo readback de produção. Capturas anteriores permanecem históricas. As27contas Google canceladas/encerradas continuam uma observação de disponibilidade independente destes vínculos; não equivalem a gasto zero.
