# Finance — titulares, gestores e contas de anúncio

Dono: Rodolfo Mattei. Fonte: mensagem `1547048317853114438`; interpretação confirmada por `1547052028663169105`, thread `1545426987756298340`. Estado técnico canônico: cadastro `master-ad-accounts` e workspace do mês no PostgreSQL do Dash. Documento registra a decisão, não substitui readback live.

## Códigos de gestor
- G001 → Ícaro (namespace de cálculo histórico `george`; login público `icaro`).
- G002 → MGS (`SEM_COMISSAO`, sem criar funcionário/login/comissão).
- G003 → Isliago (`isliago`).
- G004 → Joe (`joe`).
- G005 → Kelly (`kelly`).
- G006 → Nicolas (`nicolas`).

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
