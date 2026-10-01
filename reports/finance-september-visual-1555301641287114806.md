# Setembro — restauração do padrão visual de agosto

## Autoridade e supersessão

Rodolfo1555301641287114806, thread1545426987756298340, rejeitou a aparência de setembro e determinou comparação com agosto, preservando cores, formatações e organização. A apresentação genérica entregue sob1555274844109803522 **não tinha aceitação visual**, apesar da paridade financeira. Este relatório supersede apenas a conclusão visual daquele relatório; a origem financeira da revisão922 e a proibição de modificar a dash permanecem.

A iniciativa foi reaberta na própria tarefa. Não houve delegação/background nem promessa de correção futura: a correção foi aplicada e validada nos seis arquivos.

## Alterações efetivas

- Agosto foi lido ao vivo nos seis workbooks, com formatos efetivos/digitados, paletas, regras condicionais, zebra, bordas, mesclagens e dimensões. Nenhuma identidade Google alternativa foi usada.
- Na principal, o primeiro site voltou à colunaD, como no modelo de agosto. O consolidado extra, que ocupava o início e deslocava os sites, foi movido para a área inferior, a partir da linha258. A área de despesas/recebimentos foi preservada. O Google atualizou as referências nativas dos recortes movidos; as âncoras externasF1/H1/O145 dos gestores não mudaram.
- Os49painéis de sites retomaram o padrão grafite do proprietário, calendário azul, receitas azuis, inválidos/impostos pretos, gastos vermelhos, lucro verde, ROI cinza, zebra branca/cinza, divisores estreitos e totais fortes. Os blocos novos receberam a mesma linguagem visual.
- Países foram reorganizados dentro dos respectivos blocos pela ordem de agosto, preservando todas as operações de setembro. Isso devolveuUS à frente onde era o padrão do proprietário, sem atribuir países novos nem remover dados.
- Nas cinco planilhas de gestores, foram restaurados resumos azuis, projeções douradas, caixas de câmbio, cores por métrica, alternância das linhas e totais completos. As fontes, larguras, alturas e alinhamentos deixaram de usar o layout genérico.
- Campos adicionais de câmbio/rateio passaram a formar grupos legíveis. Remuneração ficou ligada visualmente ao seu rótulo. Os dois quadros com site excedente agora dizem explicitamente `SITES ADICIONAIS · INCLUÍDOS NO TOTAL`.
- Cabeçalhos técnicos ficaram discretos como na referência, e os rótulos voltaram aos nomes de negócio. O contraste do ROI positivo em amarelo e dos totais negativos em azul-escuro foi corrigido sem mudar regras financeiras.

## Verificação real, não somente contagem de estruturas

- Comparação de76.522células numéricas/formulares após as movimentações e após a apresentação final: zero diferença financeira, zero erro de fórmula. As coordenadas movidas foram verificadas por mapa explícito origem→destino; os demais campos foram relidos no mesmo endereço.
-2.296cabeçalhos de métricas conferidos contra a paleta efetiva de agosto: zero cor alheia à referência.
-Os seis arquivos de agosto tiveram seus hashes integrais de valores/fórmulas relidos e idênticos aos anteriores. Os formatos da referência capturada também permaneceram iguais. Caixa de setembro foi relido: resultados financeiros preservados.
-Todas as áreas temporárias de reorganização foram verificadas vazias ao final. IDs e gids originais preservados. Nenhum pagamento ou ajuste financeiro criado; nenhuma escrita, configuração ou código alterado na dash.
-Exportações PDF reais de gids/ranges financeiros delimitados, autenticadas pela Service Account canônica, foram renderizadas e inspecionadas visualmente. Houve comparação da principal e das cinco visões de gestores com agosto, além de revisão de um bloco novo (WavesBee Finanzas). Não foi usada uma simulação HTML como se fosse a planilha real.
-O QA final de Joe e George confirmou cabeçalhos íntegros, caixas de câmbio completas, associação dos quadros, ROI legível e negativos dos totais com contraste, sem corte ou sobreposição. O bloco novo confirmou a mesma paleta/zebra/totais da referência. As células de ROI sem mídia seguem vazias por regra financeira, não por falta de preenchimento.

## Falhas transitórias corrigidas e prevenção

1. O módulo Python de PDF não estava disponível. O PDF real já havia sido obtido com a Service Account; a rasterização migrou imediatamente para o Ghostscript instalado, sem instalação nem mudança de identidade.
2. O primeiro verificador do canário não tratava uma célula formatada mas vazia omitida pela API. Foi corrigido para comparar ausência com ausência, sem alterar dado.
3. O Sheets `PASTE_FORMAT` transportou banding e mesclagens. Um `addBanding` redundante foi rejeitado atomicamente; as requisições redundantes foram removidas. No quadro de redes, a mesclagemM:N ocultou cinco fórmulasN175:N179. As cinco foram restauradas exatamente do snapshot, as mesclagens indevidas desfeitas e todos os resultados dependentes/Caixa revalidados. Não houve alteração residual. Antes de avançar aos gestores, as cópias foram convertidas em escritas exclusivamente de `userEnteredFormat`, eliminando essa classe de perda de conteúdo.
4. Mesclagens cruzando o limite congelado e duas dimensões extras em grids menores foram rejeitadas atomicamente. As faixas foram ajustadas aos limites reais, sem descongelar dados nem ampliar escopo. Recibos de lotes já concluídos impediram replay cego.

As recuperações foram verificadas antes do encerramento. Não foi declarado que nenhuma fórmula chegou a ser tocada: houve movimentação nativa de referências e restauração das cinco fórmulas afetadas. O resultado financeiro final, e não apenas o valor de uma requisição, é o que foi comprovado preservado.

## Evidência e continuidade

Diretório privado: `apps/finance-system/private/september-visual-1555301641287114806/`.

- `capture-manifest.json`, `*-august.json`, `*-before.json`, `*-meta.json`: fontes visuais vivas e backups.
- `main-organization-proof.json`, `main-recovered-financial-proof.json`, `*-country-order-proof.json`: organização, recuperação e paridade por coordenadas.
- `*-verified-final.json`, `final-validation.json`, `august-full-protection-proof.json`, `contrast-readback-proof.json`: readbacks finais.
- PDFs/PNGs `*-august-reference`, `*-september-restyled`, `joe-september-final`, `george-september-final`, `new-site-wavesbee-finanzas-final`: evidência visual real. Não anexados ao Discord sem solicitação.
- Planos iniciais, versões corrigidas e recibos de lotes preservados como histórico; não são runners genéricos para replay em outro mês.

Aprendizado salvo e relido nas skills `monthly-finance-sheet-fill` (incluindo a referência de exportação) e `google-drive-agent-automation`: preservar o visual do dono, validar a renderização real antes de concluir e não tratar `PASTE_FORMAT` como pintura inofensiva em geometrias diferentes.

Checkpoint: ZEUS-FINANCE-SEPTEMBER-EXPORT-1555267485928788099. Correção visual aplicada e verificada; conferência geral financeira da semana do dia20 continua separada e não foi antecipada.
