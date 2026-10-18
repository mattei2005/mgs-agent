# Smart Bidding — contribuição do lucro por faixa de ROI

Use para análise read-only consolidada por empresas da SB, sem assumir que o lucro total do card é integralmente atribuível às campanhas.

1. Resolver identidade e autoridade; pedidos globais do produto SB não exigem inventar um domínio-alvo. Abrir o helper vivo `scripts/ares-smartbidding-common.py` e validar sua interface antes do uso. Autenticar internamente; nunca imprimir credenciais/headers.
2. Tratar `/company` como resposta sensível: filtrar em memória para as empresas autorizadas e projetar apenas companyId/name e publisherId/name/active. Não gravar ou imprimir resposta bruta. Incluir publishers inativos quando o pedido disser todos.
3. Obter as rotas reais do frontend atual (`reportProvider`, Acquisition/Adgroup). `/report/performance_per_campaigns` retorna linhas granulares de adgroup, não necessariamente uma linha por campanha. A assinatura e hashes dos bundles mudam; não fixar nomes de assets históricos.
4. Fixar o dia civil completo conforme semântica do relatório SB. Payloads 00:00Z podem incluir a data anterior: conferir o conjunto de DATE retornado, corrigir janela com offset explícito e exigir somente a data pedida. Não transformar a faixa UTC em prova do fuso de todos os fornecedores.
5. Coletar campanhas por POST de relatório e totais por GET `/report/performance_per_domain`, com os mesmos publishers, período e moeda; o GET usa `publishers[]` conforme serialização do frontend. Esses POSTs são consultas, não mutações de campanha.
6. Espelhar `Discount revenue share`: quando ativo usar NET_REVENUE e lucro=NET_REVENUE−INVESTIMENT. Não descontar a participação novamente. Confirmar no frontend vivo, não em memória.
7. Validar unicidade da chave granular e completude. Agregar investimento e receita por SOURCE + CUSTOMER_ID + CAMPAIGN_ID antes de calcular ROI. Não calcular faixas por adgroup nem fazer média simples de ROI.
8. Classificar com precisão decimal e limites não sobrepostos: ROI<0; 0≤ROI<10; 10≤ROI<20; 20≤ROI<30; ROI≥30. Testar exatamente 0/10/20/30 e valores imediatamente antes/depois. Campanhas com investimento zero não têm ROI econômico definido; separar sua receita, mesmo que a UI mostre ROI=0.
9. Reconciliar três camadas: lucro das faixas; receita em linhas sem identidade ou em campanhas sem gasto; receita consolidada do domínio ausente da tabela de aquisição. A UI calcula `profitTotal` por domínio e `profitAcquisition` pela tabela: não são a mesma métrica. Não ratear o residual por gasto, receita ou ROI sem metodologia explicitamente autorizada.
10. Informar contribuição assinada de cada faixa sobre o lucro consolidado real; prejuízo contribui negativamente e parcelas positivas podem superar 100%. Se houver residual, mostrá-lo como não classificável nos relatórios consultados, sem rotulá-lo automaticamente como broadcast/SMS/orgânico ou lucro das campanhas atuais.
11. Comparar os totais vivos com a referência informada pelo usuário, exibindo qualquer delta sem inventar causa. Repetir leitura de campanha para validar estabilidade; exigir que soma das faixas + itens sem ROI + residual = lucro consolidado.
12. Entregar conclusão primeiro, cinco faixas e reconciliação; não chamar a decomposição de integral quando parte do lucro não tiver vínculo comprovado. Salvar resultado/checkpoint para retomada sem anexar arquivos não pedidos.

Validação mínima: unicidade granular; contagem de campanhas antes/depois; soma de investimento exata; reconciliação decimal do lucro; testes de limites; readback live estável. Nenhum write SB/Meta/Google é necessário.
