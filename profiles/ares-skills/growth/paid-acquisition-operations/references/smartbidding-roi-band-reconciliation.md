# Smart Bidding — reconciliação de lucro por estratégia e faixa de ROI

Use quando o operador quiser explicar o lucro consolidado da SB por faixas de ROI, especialmente em escopo que mistura aquisição direta e BOT com retenção. O contrato de apresentação dos três blocos está no SKILL.md; este arquivo contém a receita técnica.

## 1. Fixar período, escopo e fonte do total

1. Recuperar o relatório/checkpoint anterior quando o pedido disser mesma análise; preservar moeda, empresas, tratamento de revenue share e metodologia. Reenvio usa os valores validados; novo período exige dados novos.
2. Resolver datas relativas pelo relógio real no fuso aplicável e fixar uma data civil. Construir `initialDate` e `finalDate` para o dia completo conforme a semântica SB. Conferir o conjunto de `DATE` retornado: timestamps começando às 00:00Z podem incluir a data anterior. Corrigir a janela com offset explícito antes de agregar; não inferir desse payload o fuso de cada conta de mídia.
3. Confirmar se a referência humana vem de `Domain`, aquisição ou outro card. O frontend calcula `profitTotal` usando receita por domínio e `profitAcquisition` usando a tabela de aquisição; não são o mesmo total.
4. Abrir a interface viva de `/root/mgs-agent/scripts/ares-smartbidding-common.py`. Autenticar internamente e usar `api_request(method, path, payload=...)`; tokens e headers não entram nos relatórios.
5. Consultar `GET /company`, filtrar em memória somente as empresas autorizadas e projetar `companyId/name` e `publisherId/name/active`. Incluir publishers inativos se o pedido disser todos. A resposta completa contém dados sensíveis: não imprimir nem gravar o bruto ou um prefixo truncado.
6. Tratar `DOMAIN` e `PUBLISHER` como identificadores que podem ser slugs ou IDs compostos. Resolver pelo publisher vivo e pela fonte canônica antes de uma ação de domínio; não enviar slug ao gate como se fosse FQDN nem adivinhar sufixo. No relatório global do produto, essas chaves servem para junção.

## 2. Coletar as quatro fontes comparáveis

Confirmar as rotas no `reportProvider` e nos componentes atuais do frontend; descobrir bundles a partir do HTML vigente, sem fixar hashes históricos. Usar o mesmo escopo, período e moeda nas quatro consultas:

| Fonte lógica | Consulta |
| --- | --- |
| Aquisição granular | `POST /report/performance_per_campaigns` |
| BOT por página | `POST /report/messenger` |
| Retenção SMS | `POST /report/performance_per_sms` |
| Referência consolidada | `GET /report/performance_per_domain` |

O payload dos POSTs contém `initialDate`, `finalDate`, `publishers` e `currency`. O GET usa esses parâmetros, serializando publishers como `publishers[]`. São consultas de relatório, não mutações de campanha. Salvar evidência e agregar programaticamente; a rota de campaigns pode retornar várias linhas de adgroup por campanha.

Para revenue share ativo, usar `NET_REVENUE` na aquisição, SMS e Domain. No Messenger, verificar a fórmula do frontend e comparar `REVENUE` com Domain/`NET_REVENUE` em publishers sem mistura: o relatório pode entregar receita já líquida diretamente. Não aplicar novamente o desconto da rede.

## 3. Resolver a estratégia antes de calcular ROI

1. Validar unicidade da chave granular de aquisição e das chaves Page/UTM do Messenger.
2. Vincular BOT pelo join `company + publisher + UTM_ADGROUP=pg_<id>` da aquisição com `company + publisher + UTM_CAMPAIGN` do Messenger. Exigir identidade sem conflito e igualdade do investimento por página, não apenas igualdade no total.
3. Confirmar o tráfego direto pelas contas/UTMs e contratos aplicáveis. Não chamar automaticamente todo resto de direto nem supor que `SOURCE=facebook` identifica BOT: ambas as estratégias usam Facebook. Padrões de UTM são evidência a validar, não uma allowlist global imutável. Manter identidade ambígua separada.
4. Agregar o tráfego direto por `SOURCE + CUSTOMER_ID + CAMPAIGN_ID` antes de calcular ROI. Não classificar adgroups individualmente nem tirar média simples de percentuais.
5. No BOT, usar a página como unidade econômica quando múltiplas campanhas a alimentarem. Cada gasto e receita entra uma única vez; não copiar o broadcast inteiro para cada campanha.

**Pitfall crítico:** `NET_REVENUE` da aquisição pode vir zero-only nas linhas BOT apesar de o Messenger mostrar receita positiva. Não transformar ausência de cobertura dessa coluna em prejuízo de aquisição de −100%; usar o resultado operacional por página e rotular o ROI de campanha como indisponível quando não houver atribuição válida.

## 4. Calcular faixas e separar retenção sem gasto

Usar decimal desde a leitura dos valores monetários:

- `lucro = receita líquida − investimento`.
- `ROI = lucro × 100 / investimento`, somente com investimento positivo.
- Faixas sem sobreposição: `ROI<0`; `0≤ROI<10`; `10≤ROI<20`; `20≤ROI<30`; `ROI≥30`.
- `contribuição = lucro da faixa × 100 / lucro da estratégia`; no consolidado, o denominador é o lucro total Domain. Denominador zero gera N/D, não divisão inventada; lucro total negativo exige rótulo explícito para evitar leitura enganosa das contribuições.

Para BOT, `REVENUE` é o total da página; `DRIP_REVENUE` e `BD_REVENUE` são componentes. Não calcular total + drip + broadcast. Se os componentes não fecharem exatamente, preservar a diferença dentro do total como não detalhada.

Separar receita BOT de páginas sem gasto no dia: não há ROI finito, portanto não colocar em 0% nem em 30%+. O resultado diário inclui leads históricos e não representa ROI de coorte/LTV dos leads recém-captados. A mesma cautela vale para receita direta sem gasto e para retenção SMS: sem vínculo de coorte, não atribuir às campanhas atuais.

## 5. Fechar contra Domain antes de interpretar

Exigir duas identidades:

```text
investimento direto + investimento BOT = investimento consolidado
lucro direto + lucro BOT + resultado SMS na base SB + diferenças = lucro Domain
```

Dentro de cada estratégia, somar faixas, receitas sem ROI e linhas sem identidade até reconciliar seu subtotal. Localizar diferenças por publisher ajuda o diagnóstico, mas não prova vínculo a campanha/página; não ratear por gasto, receita ou ROI para fazer o fechamento parecer completo.

Separar custos operacionais que a SB não incluiu. Custo SMS zero no relatório não prova custo real zero; mostrar a mesma base de Domain primeiro e qualquer P&L ajustado em outro bloco. Comparar os totais vivos com a referência humana e informar o delta sem inventar causa.

Interpretar aquisição e retenção separadamente. ROI negativo de aquisição não é prova isolada de prejuízo do BOT; não recomendar corte como se toda receita de retenção fosse preservada automaticamente.

## 6. Verificar e entregar

- Testar exatamente os limites 0/10/20/30 e valores imediatamente adjacentes.
- Validar contagens distintas de linhas, campanhas e páginas; não transportar denominadores de um período para outro.
- Repetir as quatro consultas e comparar chaves, valores monetários e contagens. Se mudarem, reconciliar a versão utilizada antes de fechar.
- Verificar a base líquida por múltiplos publishers comparáveis e frontend vivo. Pequenas diferenças centesimais podem decorrer de granularidade/arredondamento: declarar a tolerância e distinguir igualdade exata de aproximação; não exigir uma contagem incidental de matches exatos herdada de outro dia nem eliminar residual para passar no teste.
- Manter precisão integral nos cálculos e arredondar apenas na apresentação. Se as parcelas exibidas somarem 100,01% ou 99,99%, explicar o arredondamento; não editar uma parcela para forçar 100%.
- Publicar na ordem estável: tráfego direto sem SMS; BOT com drip/broadcast; consolidado. Repetir fonte, data e denominador junto aos títulos para que cada bloco faça sentido isoladamente.
- Preservar relatório e checkpoint por período; uma nova data não sobrescreve os resultados anteriores. Entregar inline, sem anexos não solicitados.

Critério de aceite: quatro fontes do mesmo dia/escopo, estratégia e identidade comprovadas, ausência de receita BOT zero-only tratada corretamente, joins por página exatos para gasto, faixas sem sobreposição, reconciliação decimal e readback documentados; limitações de atribuição e custos permanecem explícitas.
