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

## Proposta MGS para pedidos SHEIN com mais de uma campanha

Recomendar, ainda sem considerar implantado: manter criação em bundles de duas pelo core, mas deixar todas as campanhas PAUSED durante criação, QA por item e pós-processamento. Somente após o lote inteiro completo e QA global passar, executar a fase de ativação autorizada e readback, persistindo IDs e progresso. Pedido final PAUSED não entra nessa fase. Pedido final ACTIVE pode autorizar ambas as etapas no mesmo request; não impor um novo OK artificial. Qualquer erro antes da barreira mantém o lote pausado; erro durante a ativação exige leitura e retomada apenas de estados pendentes, sem afirmar atomicidade. Preservar horário/budget aprovados, reservar quota também para a ativação e tratar atraso de schedule sem mudança silenciosa. Não mudar código/config/estratégia por essa recomendação: implantação precisa de autorização explícita de Rodolfo e testes de falha parcial.

## Fronteira com MGS

Os testes C113/C114 foram pedidos explicitamente PAUSED e não demonstram a fase de ativação. O Engine MGS usa bundles de duas e status solicitado; a existência de criação PAUSED de shells e readback não prova que haja barreira global de QA antes de toda ativação. Qualquer adoção desse lifecycle requer autorização estrutural, desenho resumível por IDs, reserva separada para ativação e readback, teste de falha parcial e prova real; não mudar status/default/schedule por consequência de uma pergunta comparativa.
