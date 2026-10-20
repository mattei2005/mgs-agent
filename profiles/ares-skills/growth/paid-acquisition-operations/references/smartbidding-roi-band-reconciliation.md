# Smart Bidding — reconciliação de gasto e lucro

Escolher o ramo antes da coleta:

- **Aumento de gasto por site/gestor:** usar a seção `Decompor aumento de gasto`, com Domain e aquisição granular; não coletar Messenger/SMS nem produzir faixas de ROI sem necessidade.
- **Lucro misto por estratégia/faixa de ROI:** seguir as seções numeradas abaixo, incluindo as quatro fontes comparáveis. O contrato dos três blocos de ROI está no SKILL.md.
- **Campanhas de tráfego direto em faixas personalizadas:** usar aquisição granular SB e Insights Meta por campanha e por conta, conforme `Conciliação com contas de anúncio e faixas personalizadas`. Validar a estratégia pelo cadastro antes de dispensar Messenger/SMS/Domain; não apresentar o subtotal das campanhas como lucro total do site.

Todos os ramos compartilham o procedimento de período, autenticação e escopo da seção 1.

## Listas pela coluna Estimate Health — Meta primeiro, SB em lote

### 1. Congelar o universo de campanhas ativas

Resolver pelo catálogo positivo as contas de cada operação solicitada, sem fixar na skill quantidades de contas ou campanhas. Aplicar o gate account-scoped antes da consulta e comparar os conjuntos `contas_previstas` e `contas_consultadas`. Uma conta sem linhas SB não está automaticamente sem campanhas ativas.

Usar `ares-meta-common.py` com a versão Graph vigente, a credencial do binding e `graph_batch_get` para agrupar as leituras independentes de identidade da conta e do edge `act_<account_id>/campaigns`. Pedir `id,name,account_id,status,configured_status,effective_status` e filtrar `status IN [ACTIVE]`. Desempacotar `status, responses, headers`, validar o HTTP externo e cada `response.code`, consumir `response.body` já normalizado e seguir todos os cursores pendentes. Para somente efetivamente ativas, confirmar também `effective_status=ACTIVE`; conservar divergências de status separadamente. Persistir os resultados concluídos antes das asserções locais e recuperar apenas as partes ausentes.

A seleção nasce dos IDs ativos encontrados nas contas, nunca das candidatas abaixo do corte na SB. Conferir unicidade de `account_id + campaign_id` e a identidade retornada antes da junção financeira.

### 2. Consultar o recorte SB sem navegação por campanha

Resolver os publishers reais somente das operações solicitadas pelo catálogo corporativo autorizado e validar os hosts. Usar o helper `ares-smartbidding-common.py`:

```python
status, rows, metadata = sb.api_request(
    'POST', '/report/performance_per_campaigns',
    payload={
        'initialDate': initial_date_with_offset,
        'finalDate': final_date_with_offset,
        'publishers': authorized_publisher_ids,
        'currency': report_currency,
    },
)
```

O endpoint recebe uma lista de publishers; usar uma consulta para o recorte quando couber ou lotes bounded conforme tamanho/timeout. Não transformar isso em uma consulta por campanha ou uma varredura de todos os sites. Este POST lê relatório, não altera campanhas. Validar HTTP 200/201, tipo da resposta, cobertura e datas retornadas. Antes de salvar, restringir conjuntamente `PUBLISHER`, alias `DOMAIN` comprovado, `CUSTOMER_ID` autorizado e `DATE`; verificar duplicidade da chave granular quando disponível.

Fazer left join a partir dos IDs Meta. Distinguir ausência de linha, campo ausente/inválido e zero numérico retornado; nunca converter resposta vazia em uma linha financeira zero. Agregar todos os adgroups e dias da mesma campanha antes de calcular o percentual, sem média de percentuais diários.

### 3. Reproduzir a coluna vigente com proveniência correta

Descobrir os bundles pelo HTML atual da dash, seguir os imports do relatório Adgroup e localizar a definição `ESTIMATED_HEALTH`, seus argumentos e o agrupamento usado pela tabela. Não fixar hashes de bundles. A implementação observada recebe `CDP_IMPRESSIONS` como numerador e `GAM_CODE_SERVED_COUNT` como denominador:

```text
ratio = 100 × soma(CDP_IMPRESSIONS) / soma(GAM_CODE_SERVED_COUNT)
Health = max(0, ratio > 100 ? 200 − ratio : ratio)
```

Conferir a implementação viva antes de reutilizar a fórmula. Com denominador positivo, comparar com o corte solicitado antes do arredondamento. A coluna do frontend retorna zero quando o denominador é zero; se for necessário reproduzir esse zero, rotular `0% — sem base`, sem confundi-lo com zero calculado sobre denominador positivo. Campanha sem linha SB continua sem correspondência, não recebe o zero de uma função que nem chegou a ser aplicada a ela. Componentes ausentes/inválidos ficam indisponíveis e exigem ressalva, não coerção silenciosa.

Rotular a origem como **API SB com fórmula da coluna da dash**; isso não prova que a célula foi lida visualmente. Se o operador exigir conferência visual, copiar o valor renderizado no mesmo período e granularidade para os IDs exatos; usar browser/PC1 como verificação ou fallback, sem reconstruir sessão ou permissões do frontend para aparentar acesso. Preservar a coleta Meta e SB já válida e não repeti-la apenas por falha de navegação.

### 4. Validar e entregar

- Exigir igualdade entre contas previstas e consultadas, paginação integral, IDs ativos únicos e nenhuma conta/campanha fora do escopo.
- Reconciliar todas as campanhas ativas em partições disjuntas: percentual válido abaixo do corte, percentual válido fora do corte, linha sem base e campanha sem correspondência. Essas quantidades devem somar a seleção Meta.
- Testar razão numerador/denominador de 0, 0,9, 1, 1,1, 2 e acima de 2, além de denominador zero, linha ausente, corte exato e valores imediatamente adjacentes. Reproduzir a fórmula não substitui testes de cobertura.
- Para faixa fechada expressa como `90,1 a 94,9`, usar `Decimal('90.1') <= health <= Decimal('94.9')` sobre o percentual completo e arredondar somente a apresentação. Testar os dois limites exatos e valores imediatamente externos; um valor exibido como `94,90%` pode pertencer ou não à faixa conforme sua precisão original.
- Em uma faixa seguinte da mesma análise, ler o consolidado estruturado já validado, conservar os IDs ativos e horários originais, filtrar programaticamente, deduplicar e reconciliar a quantidade entregue. Não reconstituir números a partir do texto arredondado nem usar o conjunto de uma faixa anterior como universo das demais.
- Informar período civil, horário do status Meta, fonte/metodologia do percentual e lacunas relevantes. Em complemento apenas visual ou troca somente de faixa, conservar seleção e snapshot; em atualização, recuperar novas fontes e comparar os IDs. Explicitar que o recorte é acumulado do período; um pedido de ocorrências em qualquer dia exige cálculo diário e outra seleção.
- Responder perguntas sobre velocidade com a conclusão primeiro: o relatório pode ser consultado em lote; leituras individuais são exceções para lacunas específicas. Não prometer duração nem afirmar paridade visual sem evidência.

### 5. Reconfirmar cobertura e explicar campanhas sem linha SB

1. Quando houver pedido de reconferência, preservar o snapshot anterior antes da nova coleta. Reconsultar o mesmo universo de contas Meta e o mesmo lote SB, sem mudar período, publishers, moeda ou critério de status. Comparar os conjuntos de IDs selecionados, percentuais completos e contadores Health por chave granular; totais iguais podem esconder entradas e saídas compensadas.
2. Para ativos sem correspondência SB, reaplicar os gates das contas e agrupar em Graph Batch leituras GET de `<campaign_id>` com `id,account_id,created_time,start_time,status,effective_status` e de `<campaign_id>/insights` com `campaign_id,impressions,spend`, o mesmo `time_range` e `use_unified_attribution_setting=true`. Reutilizar configuração completa já coletada quando disponível. Validar HTTP externo, cada resposta interna, identidade, paginação e horários; persistir cada lote concluído sem URLs autenticadas antes de agregar.
3. Classificar ausência de entrega somente após Insights válidos integralmente vazios ou contadores explícitos de gasto e impressões zero. Erro ou leitura parcial permanece pendência. Havendo entrega positiva sem linha SB, manter lacuna de cobertura/atribuição explícita e não certificar que todas as campanhas com entrega foram classificadas por Health.
4. Usar `created_time` convertido ao timezone live da conta para identificar criação posterior ao fim do período; `start_time` é apenas agendamento. Não inferir primeira entrega ou ausência de entrega pela data do nome, pelo horário de criação ou pelo schedule. Criação posterior pode explicar parte das ausências, mas não fornece percentual Health.
5. Responder à confirmação com o recorte exato e a ponte completa: total de ativas, com Health dentro e fora da faixa, sem base e sem linha SB; entre as ausências, separar entrega zero comprovada de entrega positiva ou indisponível. Declarar estabilidade de IDs e percentuais somente quando comparada; não repetir uma ressalva antiga como pendência inexplicada depois de resolvê-la.

## 1. Fixar período, escopo e fonte do total

1. Recuperar o relatório/checkpoint anterior quando o pedido disser mesma análise; preservar moeda, empresas, tratamento de revenue share e metodologia. Reenvio usa os valores validados; novo período exige dados novos.
2. Resolver datas relativas pelo relógio real no fuso aplicável e fixar uma data civil. Construir `initialDate` e `finalDate` para o dia completo conforme a semântica SB. Conferir o conjunto de `DATE` retornado: timestamps começando às 00:00Z podem incluir a data anterior. Corrigir a janela com offset explícito antes de agregar; não inferir desse payload o fuso de cada conta de mídia.
3. Confirmar se a referência humana vem de `Domain`, aquisição ou outro card. O frontend calcula `profitTotal` usando receita por domínio e `profitAcquisition` usando a tabela de aquisição; não são o mesmo total.
4. Abrir a interface viva de `/root/mgs-agent/scripts/ares-smartbidding-common.py`. Autenticar internamente e usar `api_request(method, path, payload=...)`; tokens e headers não entram nos relatórios.
5. Resolver o catálogo por `api_request('GET', '/company')`: no helper Ares essa rota é uma projeção **local**, validada por `data/ares/sb-publisher-scope.json` × cadastro de hosts, sem HTTP global. Não substituir por chamada direta ao catálogo remoto nem buscar empresas fora do cadastro. Publishers novos/ausentes exigem reconciliação corporativa pela fonte autorizada; não adivinhar IDs. Antes de cada relatório, enviar explicitamente os publishers aprovados: o helper valida todos os seletores antes de credencial/HTTP. Incluir publishers inativos somente conforme o recorte pedido.
6. Tratar `DOMAIN` e `PUBLISHER` como identificadores que podem ser slugs ou IDs compostos. Resolver pelo publisher vivo e pela fonte canônica antes de uma ação de domínio; não enviar slug ao gate como se fosse FQDN nem adivinhar sufixo. No relatório global do produto, essas chaves servem para junção.

## 2. Coletar as quatro fontes comparáveis para ROI

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

## Conciliação com contas de anúncio e faixas personalizadas

- Quando o pedido exigir que o investimento bata com as contas, consultar Insights Meta por campanha e, independentemente, por conta, com a mesma data civil no timezone live e moeda. Exigir igualdade da soma das campanhas com o total de cada conta; preservar NET_REVENUE SB e recalcular lucro e faixa usando o gasto Meta. Mostrar a diferença contra INVESTIMENT SB, sem atribuir causa não comprovada nem forçar igualdade.
- Congelar o snapshot verificado. Um dia fechado ainda pode receber ajustes entre leituras Meta; comparar IDs e valores por campanha e recuperar, para cada conta divergente, o par campanha + total de conta com os mesmos parâmetros. Preservar cada resposta concluída antes das asserções locais e substituir somente a conta reconciliada, pois misturar um novo detalhamento com um total antigo produz fechamento aparente. Não declarar readbacks globais estáveis quando houve alteração.
- Verificar separadamente estabilidade das faixas pedidas e estabilidade do restante do universo. Após ajuste histórico, recalcular todas as campanhas e comparar quantidade, investimento, receita e lucro por faixa; só afirmar que o pedido não foi afetado quando esses campos permanecerem iguais. Na reanálise do mesmo dia, contar mudanças de faixa por `account_id + campaign_id`, não pela diferença líquida das contagens, pois entradas e saídas podem se compensar.
- Se o par campanha × conta continuar divergente após diagnóstico e readbacks delimitados, preservar ambos os totais e a diferença como pendência de conciliação; não ratear o residual, atribuí-lo automaticamente a arredondamento ou certificar igualdade integral. Distinguir resultado calculado por campanha de fechamento conciliado e registrar no checkpoint a conta afetada, evidência e próxima verificação. Uma ressalva não transforma a conciliação incompleta em teste aprovado.
- Aplicar os limites pedidos, não os defaults da análise anterior. Em `0% a 15%` versus `negativas`, usar `0≤ROI≤15` e `ROI<0`, comparar antes do arredondamento e testar zero, 15 e valores imediatamente adjacentes. Somar conjuntos antes de classificar; receita sem gasto e SMS sem vínculo comprovado ficam fora das faixas das campanhas.

## 6. Verificar e entregar

- Testar os limites das faixas efetivamente solicitadas, valores imediatamente adjacentes e investimento zero; usar 0/10/20/30 somente quando forem os cortes do relatório.
- Validar contagens distintas de linhas, campanhas e páginas; não transportar denominadores de um período para outro.
- Repetir as consultas exigidas pelo ramo escolhido e comparar chaves, valores monetários e contagens: as quatro fontes no relatório misto; aquisição SB e os dois níveis de Insights Meta no relatório restrito de campanhas diretas. Se mudarem, reconciliar a versão utilizada antes de fechar.
- Verificar a base líquida por múltiplos publishers comparáveis e frontend vivo. Pequenas diferenças centesimais podem decorrer de granularidade/arredondamento: declarar a tolerância e distinguir igualdade exata de aproximação; não exigir uma contagem incidental de matches exatos herdada de outro dia nem eliminar residual para passar no teste.
- Manter precisão integral nos cálculos e arredondar apenas na apresentação. Se as parcelas exibidas somarem 100,01% ou 99,99%, explicar o arredondamento; não editar uma parcela para forçar 100%.
- No relatório misto, publicar na ordem estável: tráfego direto sem SMS; BOT com drip/broadcast; consolidado. No relatório restrito, publicar primeiro as faixas solicitadas e sua soma; depois contexto e conciliação. Repetir fonte, data e denominador junto aos títulos para que cada bloco faça sentido isoladamente.
- Preservar relatório e checkpoint por período; uma nova data não sobrescreve os resultados anteriores. Entregar inline, sem anexos não solicitados.

Critério de aceite de ROI misto: quatro fontes do mesmo dia/escopo, estratégia e identidade comprovadas, ausência de receita BOT zero-only tratada corretamente, joins por página exatos para gasto, faixas sem sobreposição, reconciliação decimal e readback documentados. Para campanhas diretas em faixas personalizadas: aquisição SB e Insights Meta por campanha/conta no mesmo período e moeda, cobertura do join por IDs, agregação prévia dos conjuntos, limites testados, conservação decimal e readbacks documentados. Igualdade campanha × conta só recebe aceite quando demonstrada; residual persistente exige status com ressalva, não PASS de conciliação. Limitações de atribuição e custos permanecem explícitas em ambos os ramos.

## Decompor aumento de gasto por site e gestor

1. **Fixar a comparação.** Ler a imagem real quando houver print, confirmando mês/ano, moeda e linhas diárias. Resolver o dia atual pelo relógio e escolher a janela-base anterior ao salto; se o pedido disser semana anterior, usar sete datas civis completas imediatamente anteriores ao início identificado. Separar o dia em andamento, pois compará-lo com dias completos reduz artificialmente a média posterior.
2. **Coletar somente as duas fontes necessárias.** Seguir a seção 1 para autenticação e publishers. Descobrir o `reportProvider` no HTML/frontend vigente e confirmar `GET /report/performance_per_domain` e `POST /report/performance_per_campaigns`. Usar `initialDate`, `finalDate`, publishers e `currency` idênticos; no GET, serializar a lista como `publishers[]`. Validar as datas de `DATE` retornadas antes de calcular.
3. **Congelar e reconciliar o investimento.** Salvar lotes separados, sem credenciais, e ler `INVESTIMENT` com `Decimal(str(valor))`. Validar unicidade de `PK_JBF_PERFORMANCE_PER_DOMAIN` e `PK_JBF_PERFORMANCE_PER_ADGROUP` quando presentes; não eliminar linhas distintas só porque pertencem à mesma campanha, pois a aquisição retorna granularidade de adgroup. Somar os dias independentemente nas duas fontes e expor resíduos centesimais em vez de forçar igualdade. Usar Domain para o consolidado/sites e aquisição para contas/campanhas.
4. **Resolver gestor por identidade estável.** Agrupar aquisição por empresa, publisher/site, `SOURCE` e `CUSTOMER_ID`; tratar `ACCOUNT_NAME` como rótulo, não chave única. Cruzar o ID com o cadastro da operação e o código de gestor com a fonte canônica da equipe. Usar sufixo G001–G006 do nome apenas como pista de junção; confirmar a atribuição no cadastro antes de publicar o nome humano. Preservar contas sem vínculo validado como `gestor não identificado`, sem excluir seu gasto do consolidado nem atribuí-las ao gestor de outra conta do mesmo site.
5. **Calcular a ponte antes → depois.** Para cada grupo, calcular `media_base = soma_base / dias_base`, `media_pos = soma_pos / dias_pos` e `delta_dia = media_pos − media_base`. Usar o mesmo denominador de dias civis para todos os grupos, incluindo zeros confirmados; ausência de cobertura não equivale a zero. Ordenar por `delta_dia` decrescente e descer de site para conta/gestor nos maiores contribuintes. Mostrar o dia de pico separadamente da média posterior. Base zero produz percentual N/D, não infinito nem 100% arbitrário.
6. **Validar a interpretação da contribuição.** Exigir que a soma dos deltas por site reproduza o delta consolidado da mesma fonte. Se um site adicionar mais que o aumento líquido total, explicar que quedas de outros sites compensaram parte do salto; participação acima de 100% pode ser correta. Não ordenar pelo percentual de crescimento, porque uma base pequena pode esconder os maiores aumentos em dólares.
7. **Conferir print e readback.** Comparar o total diário vivo com a imagem; não misturar o total do print com parcelas de outra extração nem atribuir diferença a atraso, filtro, câmbio ou canal sem prova. Repetir as duas consultas com os mesmos parâmetros e comparar chaves, contagens e `INVESTIMENT` por linha, pois totais estáveis podem esconder compensações entre contas. Se houver mudança, reconciliar a versão utilizada antes de fechar.
8. **Entregar a conclusão operacional.** Mostrar primeiro site e gestor/conta predominantes; depois janelas/moeda, média consolidada, maiores deltas por site e gestores do site principal. Distinguir vínculo da conta de autoria de budget write: só histórico de alterações/audit específico comprova quem executou a mudança. Relatório de gasto não autoriza alteração de campanha.

Critério de aceite de gasto: mesmas datas/escopo/moeda nas duas fontes, investimento sem duplicidade, deltas por site fechando no consolidado, atribuição de gestor validada ou explicitamente pendente, readback das parcelas e diferença contra o print preservada. Testes de consistência: grupos com gasto zero continuam no denominador; base zero não divide; um grupo pode superar 100% do aumento líquido quando outros caem; mudanças opostas entre contas devem ser detectadas mesmo com total estável.

## Dimensionar um objetivo de redução de gasto

1. **Separar objetivo de execução.** Resolver pelo contexto o escopo consolidado, moeda e periodicidade; perguntar somente se essa identidade continuar ambígua. Registrar no checkpoint o objetivo informado e o estado da decisão, deixando explícito quando cortes, redistribuição ou automação não foram autorizados. Não promover um objetivo gerencial a política de enforcement.
2. **Escolher a referência observada.** Reutilizar o snapshot verificado que acabou de ser apresentado para dimensionar o gap, identificando sua data de consulta; não fazer nova coleta só para calcular a diferença. Se o pedido for avaliar se ações posteriores dos gestores já surtiram efeito, coletar dados novos e separar dias completos de parciais. Um histórico anterior às ações não comprova o gasto atual.
3. **Calcular o esforço com Decimal.** Para gasto diário observado `G` e objetivo diário `T`, calcular `reducao_necessaria = max(G − T, 0)` e `reducao_pct = 100 × reducao_necessaria / G` quando `G > 0`. Calcular separadamente para a média recente e para o último dia completo, sem misturar os denominadores. Não usar o aumento contra a semana-base como sinônimo de redução até o objetivo: são diferenças contra referências distintas.
4. **Responder proporcionalmente ao pedido.** Quando o operador apenas comunicar o objetivo e disser que está avaliando alternativas, confirmar entendimento, quantificar o gap e indicar o critério de análise; não iniciar uma auditoria completa de rentabilidade nem aplicar cortes sem pedido. Tratar o gap como esforço necessário sobre o gasto observado, não economia já alcançada.
5. **Somente quando solicitado, construir cenários.** Investigar primeiro as maiores contribuições em dólares, mas selecionar candidatos por rentabilidade recorrente e maturidade, após considerar atraso GAM/SB e atribuição direta/BOT/retenção. Apresentar gasto histórico dos candidatos, ajuste proposto e incerteza sobre receita/margem afetadas. Não igualar soma de budgets removidos à economia diária garantida, porque orçamento e entrega efetiva são medidas diferentes.

Verificações: gasto abaixo ou igual ao objetivo gera redução necessária zero; gasto observado zero não permite percentual de redução; média e último dia usam referências próprias; nenhum cenário constitui write autorizado nem prova de lucro preservado.
