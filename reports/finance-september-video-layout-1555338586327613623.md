# Setembro — ajustes do vídeo, parâmetros centrais e câmbio live

## Autoridade e interpretação confirmada

Thread1545426987756298340. Autoridades de Rodolfo:
-1555338586327613623: vídeo109,55s, com pedido de consolidados à direita como em agosto, deslocamento da colunaRede deC paraD no resumo inferior e melhor organização dos gastos por conta. O próprio áudio localiza as contas no fim; não era autorização para duplicar/reimportar gastos.
-1555350526672113764: retirar os quadros inferiores repetidos de inválidos/revshare/imposto, já existentes no topo.
-1555351286113902643: os câmbios automáticos deveriam permanecerlive, não fixos.

Os frames nativos em47–56s confirmaramC199=Rede e o resumoB199:K248; o trecho80s mostra as duas contas Eggbev já existentes. Leituras equivocadas do contact sheet sobre ano/mês não foram usadas para escrever: a aba/gid foi resolvida ao vivo como Setembro2026.

Este relatório supersede o encerramento funcional/visual anterior apenas nos pontos corrigidos aqui. A fotografia fixa de câmbio usada na entrega anterior não era o estado correto para as cotações que a dash mantém automáticas. Os dados nominais continuam sendo o espelho autorizado da fonte; não foi autorizada nem criada sincronização automática de receitas/gastos.

## Resultado aplicado

### Consolidados no extremo direito

- Recriados11blocos de países na sequência da referência de agosto, incluindo oFR exigido por setembro: US,GB,DE,ES,TR,MX,CA,AR,BR,ZA,FR.
- Recriado o consolidado geral após os países.
- Região total: **Setembro2026!ASY:AWQ**. Consolidado geral: **AWI1:AWQ36**.
- Cada bloco contém30dias de setembro e seu total mensal. Agosto foi referência de desenho, não motivo para criar um dia31 inexistente.
-2.666resultados derivados verificados contra as células de origem. Fontes explícitas excluem os próprios resumos, evitando dupla contagem.
- Inválidos aparecem como informação já contida noNET; o lucro não os desconta novamente. ROI mensal usa agregados, e ROI sem mídia permanece vazio.

### Rede emD e contas legíveis

- Movido somenteC199:K248 paraD199:L248. Site permaneceu emB;C voltou a ser um separador, sem alterar as demais tabelas ou as referências cambiais do topo.
- Autoajuste das alturas do resumo mantém nomes e redes completos, sem cortarSB Rede1/Rede2 na coluna estreita.
- As39contas existentes tiveram nomes e IDs preservados e seus pares moeda original/conversãoUSD agrupados sob um único cabeçalho de conta.
- Cada site recebeu uma faixa clara deGASTOS POR CONTA DE ANÚNCIO; onde não havia gasto registrado, a ausência ficou explícita, sem inventar conta ou lançamento.

### Parâmetros somente no topo

- Retirados75quadros locais das linhas39:40, com225células numéricas de parâmetros e seus rótulos redundantes.
-6.750fórmulas da principal passaram a usar as referências globais, corretamente selecionadas por rede. Os percentuais globais não foram alterados.
- As taxas de todos os blocos com receita foram comparadas antes da troca e eram iguais às globais. Defaults locais em blocos sem receita foram substituídos pela referência da rede já aprovada; os resultados monetários permaneceram iguais antes de religar o câmbio.
-6.660fórmulas dos cinco gestores também foram ligadas à mesma origem. Cada gestor usa um único vínculo técnicoIMPORTRANGE deC1:O1 da principal emA610:M610, somente leitura e com a linha oculta; não foram criados novos quadros editáveis abaixo dos sites.
- O cabeçalho percentual deM2 no topo passou a exibir o percentual corretamente em vez de um decimal arredondado para zero.

### USD/BRL eUSD/CAD automáticos novamente

- **CAIXA SINTETICO!K2:** `=GOOGLEFINANCE("USDBRL")*99%`.
- **Setembro2026!F1:** continua vinculado à cotação de setembro emCaixaK2.
- **Setembro2026!H1:** `=GOOGLEFINANCE("USDCAD")`.
- Fórmulas correspondem às da fonte técnicaGoogle da dash. A avaliação numérica foi relida, e os valores mudaram entre leituras mantendo as fórmulas, comprovando que não são constantes mascaradas.
- As cinco planilhas dos gestores acompanham as mesmas cotações; remuneração, folha da principal eCaixa foram reconciliados após a propagação.
- **GBP/USD permaneceu fixo**, exatamente como o modo de setembro na própria dash, que foi consultado somente porSELECTREAD ONLY. Não foi promovido para automático por suposição nem confirmado como liquidação.
- As notas e rótulos deixaram de descrever uma fotografia cambial fixa e passaram a identificar câmbios automáticos/provisórios. A conferência geral da semana do dia20 permanece separada.

## Preservação e validação

- Antes de religarFX:38.864células financeiras existentes e os2.666novos resultados passaram, sem divergência ou erro.
- Depois de religarFX e concluir os vínculos dos gestores:5.978entradas numéricas originais verificadas, zero alteração nominal;2.666resumos reavaliados com a cotação atual, zero divergência; cinco remunerações/pisos e a cadeia de importação conferidos.
- Zero erro de fórmula, zero quadro inferior restante e zero referência às antigas células locais de taxa.
- Consolidado geral, fechamento principal eCaixa continuam coerentes entre si. Resultados convertidos podem variar com o câmbio, como solicitado; isso não é alteração das receitas/gastos originais.
- Os seis arquivos de agosto tiveram hashes integrais de valores/fórmulas conferidos e preservados.
- PDFs reais dos novos consolidados, da área de gastos Eggbev, do resumo inferior e do topo foram exportados com aService Account e revisados visualmente. Títulos, agrupamentos eRede emD ficaram legíveis. Um avaliador visual pediu31dias por confundir referência de agosto com competência-alvo; isso foi rejeitado pelo calendário e pelo readback dos30dias de setembro.
- **Zero escrita na dash**, zero pagamento executado, zero alteração de credencial, permissão, cron ou configuração produtiva.

## Recuperações de mídia

A URL inicial doCDNDiscord retornou403 apesar de assinatura válida. A mesma mídia foi obtida pelo domínio oficialmedia.discordapp.net e validada por tamanho113623142bytes, sem enviar o vídeo privado a arquivos públicos/proxies terceiros. A transcrição local encontrou incompatibilidadePyAV no argumento metadata_errors; foi recuperada comPCM16kHz/mono viawave+NumPy, sem trocar dependências compartilhadas. Um timeout da ferramenta de edição foi reconciliado por leitura do arquivo antes da gravação. Não restou falha operacional pendente.

## Evidência e aprendizado

Diretório privado: `apps/finance-system/private/september-video-layout-1555338586327613623/`.

- `media/`: vídeo original, transcrição completa e frames que fundamentaram a interpretação.
- `metadata-before.json`, `main-before.json`, `august-reference.json`, `target-styles-before.json`: baseline e backup.
- `plan.json`, `apply-receipt.json`, `layout-proof.json`: alterações do vídeo e remoção dos quadros locais.
- `fx-live-readback.json`, `dashboard-rate-modes-final-readonly.json`, `manager-rate-link-proof.json`, `final-proof-post-rate-links.json`: estado final, modos reais, referências e cálculos.
- `account-structure-and-notes-proof.json`, `august-protected.json`, `completion.json`: proteção deIDs/dados/histórico e fechamento.
- `right-overall-final`, `right-us-gb-final`, `ad-accounts-eggbev-final`, `recap-rede-d-final`, `top-rates-final`: renderizações reais, não anexadas sem solicitação.

Procedimentos corrigidos nas skills financeira e de mídia: não deixar FX automático congelado na entrega, preservar as áreas funcionais do modelo, centralizar taxas, ouvir o vídeo inteiro antes de inferir falta de dados e recuperar downloads/transcrição por rotas seguras.

Checkpoint: ZEUS-FINANCE-SEPTEMBER-EXPORT-1555267485928788099. Estado: pedidos do vídeo e das duas mensagens adicionais aplicados e validados.
