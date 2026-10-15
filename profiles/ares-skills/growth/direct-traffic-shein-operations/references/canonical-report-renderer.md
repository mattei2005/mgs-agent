# Renderer e gate canônicos de relatório SHEIN

## Objetivo

Evitar divergência entre threads e uso de modelos históricos em pedidos genéricos. A política visual continua exclusivamente em `data/ares/meta-ads/operations/SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout`. O índice `data/ares/discord/shein-intraday-report-bindings.json` vincula as 36 threads a contas exatas; não amplia autoridade. Ler ambos em cada pedido, não usar um snapshot de configuração como estado vigente.

## Produto com largura limitada e sem legenda extensa

Por pedido de Rodolfo na thread `1560303769680355525`, após problema visual na `1558147211026501643`, Produto tem máximo de **25 caracteres incluindo espaços**. Quando houver corte, os três caracteres `...` também entram nesses 25. O helper `product_label` lê `product_column` do contrato, normaliza apenas a exibição para uma linha, neutraliza pipes internos e respeita também largura visual Unicode máxima de 25. Não renomear campanhas/assets, sobrescrever o valor completo do modelo, alterar a ordenação/família ou consolidar produtos só porque seus rótulos truncados coincidem. Só a célula visível é cortada; dados e linhagem permanecem íntegros. Verificar os limites em todas as células depois de renderizar.

Rodolfo dispensou a legenda explicativa. `legend.enabled=false`: não acrescentar blocos de cores R/E, aliases de Lance, definições longas de Média, Produto ou COPY. Conservar apenas rodapé conciso de proveniência/fórmulas essenciais, corte parcial e limitações relevantes; as regras de cálculo/cores continuam no contrato. Não publicar um relatório novo durante um pedido de corrigir/limpar e aguardar nova solicitação. A suíte cobre exatamente 25, excesso com reticências, espaços/controles Unicode, preservação do modelo e de famílias, prefixos truncados iguais e ausência da legenda extensa.

## Diagnóstico de quebra visual no Discord

Compare as larguras de cada coluna em relatórios reais antes de propor alterar separadores, cabeçalhos ou dividir a tabela. O renderer usa a maior célula de Produto para preencher a coluna inteira: um único nome longo pode alargar todas as linhas, inclusive as dos produtos curtos. Se os perfis das outras colunas forem iguais e só Produto variar, identifique Produto como a causa da diferença entre contas; a largura total é o efeito. Não confundir o limite de 2000 caracteres por mensagem com a largura visual de uma linha. Para isolar a correção, simular a redução apenas de Produto mantendo todas as outras larguras e o separador aprovado. Qualquer novo limite menor que o vigente precisa de aprovação; não trocar a regra global durante um diagnóstico. Um perfil que cabe em outro relatório serve de referência de teste, não de garantia universal para janela/zoom diferentes. Procedimento exercitado comparando perfis completos de relatórios reais e confirmando que somente Produto explicava a diferença de largura.

## Modelo normalizado

O script `/root/.hermes/profiles/ares/scripts/shein-report-layout.py` recebe JSON sanitizado com:

- `account`: `id` (com ou sem act_), `name`, `currency`, `timezone_name` lidos na Meta.
- `date`: data civil ISO do relatório.
- `history_dates`: exatamente a data do relatório e as seis datas anteriores, crescentes.
- `source_timestamps.insights`: horário financeiro ISO com offset; preservar também os horários de SB, delay e configuração no modelo/audit.
- `delay.totalMinutes`: leitura atual do publisher no SB; ausente/inválido vira n/d.
- `rows`: uma linha por campaign ID real com `id`, `name` bruto, `number` literal, `product` resumido, `quiz` e `bid` comprovados ou n/d/misto explícitos, `spend` Meta, `net_revenue` e `estimated_revenue` SB, `roi`, `estimated_roi`, `health`, `roas`, `first_delivery` ISO ou null e `history`.
- Cada item de `history`: `date`, `spend` Meta diário, `net_revenue` SB diário, `roi` e `partial`. O dia atual utiliza o mesmo snapshot financeiro da tabela principal; sem receita/gasto positivo, roi=null. Campos numéricos podem ser strings decimais; não substituir indisponível por zero.

O renderer valida identidade da thread/conta, presença dos campos, cálculo de ROI, sete datas, igualdade da última coluna com o principal e origem COPY explícita. Deriva R/E, Saldo, média com cobertura, família e paginação pelo contrato atual. Não inventar Quiz/Início/Lance para passar o schema: null/n/d comprovado é preferível a inferência. A fonte de coleta precisa seguir o playbook live Meta × SB; passar no gate visual não prova que a coleta foi atualizada.

## Execução padrão nas threads Intraday

1. Coletar e persistir fontes live, sem publicar parciais financeiros sem QA.
2. Materializar o modelo normalizado com proveniência e o binding correto.
3. Executar `python3 /root/.hermes/profiles/ares/scripts/shein-report-layout.py render --thread-id <thread_id> --input <model.json> --output <report.md>`.
4. Executar imediatamente antes da resposta `python3 /root/.hermes/profiles/ares/scripts/shein-report-layout.py validate --thread-id <thread_id> --input <model.json> --report <report.md> --receipt <receipt.json>`.
5. Usar o report.md gerado integralmente na entrega nativa, sem remontar cabeçalhos ou alterar tabelas. O arquivo `.parts.json` contém blocos completos abaixo de 2000 caracteres. Validar a continuação nativa quando o relatório ultrapassar o limite de uma entrega; não tratar geração local como prova de entrega. Sem anexo não pedido e sem POST paralelo de mensagens por esse helper.
6. Qualquer alteração no contrato ou texto torna o recibo anterior insuficiente; repetir somente render/validate com o mesmo snapshot, salvo pedido de atualização financeira.

O gate compara o texto exato com o render atual. Ele rejeita remoção de pipes/Quiz, falta do histórico, divergência de ROI, contas trocadas e modelos incompletos. Conta vazia mantém os cabeçalhos do principal e do histórico e declara ausência de linhas; não criar linhas financeiras fictícias. No resumo vazio, não converter a soma vazia de receitas em zero: Receita, Saldo e ROIs ficam n/d quando não há base SB; gasto Meta pode ser zero com a ausência de entrega validada. O teste de conta vazia deve verificar esses valores, além dos dois cabeçalhos. Fora das 36 threads, a coleta e autorização próprias continuam necessárias; o renderer também atende modelos autorizados em Diretoria, sem fingir binding a uma thread diferente.

## Correção e limpeza de threads

Ao auditar relatórios em vários canais, paginar todo o histórico, preservar evidência local protegida e classificar os reports reais antes de qualquer exclusão. Corrigir a camada de formatação/procedimento, testar localmente e não publicar report novo se o pedido disser aguardar. Para apagar mensagens, usar somente os IDs de threads autorizados e verificar o pai; preservar canais, threads, membros e permissões. Após cada mutação, reler os alvos. Mensagens apagadas remotamente podem continuar no contexto interno; nos próximos pedidos o contrato atual e o gate prevalecem sobre exemplos antigos.

## Origem COPY com padding diferente

Compare a identidade numérica para resolver o pai explícito dentro da mesma conta/produto/seleção (por exemplo, `COPY C6` resolve `006` quando único), preservando os tokens literais `006` e `COPY C6` na apresentação e no modelo. Não retire zeros dos nomes nem altere o tracking para contornar o gate. Se mais de um ID tiver o mesmo número após a comparação numérica, mantenha a ambiguidade explícita, sem escolher um pai. O teste `test_padded_copy_parent_keeps_literals` cobre vínculo único, preservação integral do modelo e ambiguidade numérica; a suíte canônica foi exercitada com esse caso e com relatório live.

## Testes

`python3 -m unittest discover -s /root/.hermes/profiles/ares/tests -p test_shein_report_layout.py -v`.

A suíte usa uma pequena fixture real Meta × SB, além de testes sintéticos explicitamente unitários de limites, ciclos e dados faltantes. Cobre cores em 10/40, média sem imputação, conta vazia, vínculo thread/conta, famílias em múltiplas gerações, ciclos, alinhamento Unicode, preservação de dados e rejeição de texto modificado. Uma renderização local completa também deve ser exercitada antes de promover alteração do renderer. O helper não tem transporte de publicação e não acessa a rede.
