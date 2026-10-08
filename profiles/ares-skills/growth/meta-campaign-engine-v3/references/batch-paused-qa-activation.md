# Referência externa — criação PAUSED, QA e ativação de lote

Use ao analisar o fluxo Hércules/ExecMeta de Felipe ou propostas de ativação em duas fases. É comparação arquitetural, não política MGS automaticamente vigente e não autorização de alteração do Engine.

## Fonte verificada

Documento fornecido por Rodolfo: `fluxo-criacao-campanhas-shein-website.md`, versão Production ExecMeta, atualizado 23/09/2026 Toronto. Arquivo original recebido: `/root/.hermes/profiles/ares/cache/documents/doc_275bbc022074_fluxo-criacao-campanhas-shein-website.md`. Cópia durável da fonte fornecida: `/root/mgs-agent/data/ares/meta-ads/research/references/hercules-execmeta-flow-provided-20260923.md`.

Seções relevantes: 2 (1–12 campanhas; filhos até quatro; microbatch unitário), 3 (pipeline), 4.7 (uma árvore PAUSED com IDs persistidos e QA antes da próxima), 4.8 (barreira global de QA antes de ativação serial), 5.4 (capacidade separada para criação/QA e ativação/readback), 5.8–5.9 (reconciliação por leitura antes de retry) e 6 (falhas parciais e readback final GET-only).

## Conclusão fundamentada

O programa documentado cria e confere cada campanha PAUSED; somente depois de todas as árvores completas e da barreira global de QA inicia a ativação serial, com readback terminal. O padrão também cobre uma campanha, não apenas lotes maiores. A screenshot de Hercules de Rodolfo mostra uma campanha primeiro validada PAUSED e depois ACTIVE com início futuro; não mostra um lote de 40 ou rate limit.

Esse desenho contém o dano de falha na criação: objetos completos permanecem pausados enquanto o pedido retoma só o que falta. Não elimina quota nem torna a ativação atômica. Se rate limit atingir a ativação serial, parte pode estar ACTIVE e parte PAUSED; reler IDs e retomar somente estados pendentes, sem pausar/reativar objetos já corretos nem replay de POST incerto.

ACTIVE com start_time futuro significa habilitada para o horário agendado, não entrega imediata. A separação das etapas não exige necessariamente novo OK humano: a autorização de ativação pode estar no pedido aprovado, desde que o contrato permita e o QA esteja concluído. Pedido explicitamente PAUSED nunca ganha ativação implícita.

O documento declara máximo de 12 campanhas; o relato de 40 pode se referir a outra release e não está confirmado pelo arquivo. Não atribuir ao documento garantias de tempo ou ganho de quota. Não copiar os limites locais (120/15min, lease 80) como se fossem teto oficial da Meta ou policy MGS.

## Política MGS implantada — toda criação SHEIN

A autorização posterior de Rodolfo na mesma thread supersede a versão limitada a quantidade ≥2: `config.json#/shein_batch_activation` agora tem `minimum_quantity=1`, em conjunto com `shein_media_qa`. O request aprovado conserva status final/budget/start; o runner sela um manifest de criação PAUSED e um manifest de destino com o status solicitado. O core conserva bundles de duas, todos os itens passam por QA semântico, mídia renderizada e pós-processamento antes da barreira global, e somente então `CampaignEngine.activate_verified` executa a fase status-only por IDs persistidos quando o destino aprovado é ACTIVE. Pedido PAUSED termina pausado; quantidade 1 também exige essa barreira. Por decisão posterior de Rodolfo, novos pedidos SHEIN sem status final usam ACTIVE depois de QA de todas as campanhas via `request_defaults`; não é uma ativação de campanhas existentes e não elimina a construção PAUSED. Não há necessidade de repetir autorização de ativação em cada modelo humano. O core rejeita execute ACTIVE de criação SHEIN enquanto o gate de mídia estiver ativo e exige prova de mídia vinculada aos ad/creative IDs antes da ativação. Não há novo OK artificial se o request já autorizou ACTIVE. Reativação parcial retoma por GET e somente estados pendentes, sem POST de criação nem resets de nós já ACTIVE. Budget, nomes e start não são alterados na ativação; schedule expirado exige decisão, nunca ativação imediata silenciosa. Quota e writer lease da fase de ativação são independentes. A referência externa não define os limites MGS nem autoriza canários reais.


## Fronteira com MGS

A implementação do lifecycle foi autorizada separadamente e validada offline; uma pergunta comparativa ou aprovação de software nunca autoriza um novo canário Meta. As provas de transporte simulado, renderer com mídia local e source snapshots não são benchmark live nem prova de serving. O próximo teste real exige novo pedido humano autorizado; não alterar schedule, budget, conta ou campanhas existentes para produzir benchmark.
