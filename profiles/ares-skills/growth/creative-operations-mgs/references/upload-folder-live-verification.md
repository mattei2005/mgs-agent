# Verificação live de arquivos da entrada e da entrega permanente

Use quando perguntarem se um lote foi tratado e entregue corretamente. Fonte vigente: `context/drive-flat-intake-cutover.md`, binding flat vivo e receita `flat-upload-intake.md`.

## Princípio

`UPLOAD MANUAL` é entrada temporária, não acervo. No modo flat, arquivos sem pedido/contexto registrado permanecem preservados e não podem ser atribuídos a gestor por suposição. Uma pasta técnica vazia não prova que todos os lotes foram tratados, nem arquivos na entrada provam falha de outro lote já entregue.

No tratar/mover canônico, preservar RAW e clean, sanitização, hashes, linhagem, reservas, owner/ACL, receipt/ACK e stock. READY/LEGACY no Shared Drive são staging interno; a entrega definitiva resolve os 30 TB e o destino common/exclusive/used realmente autorizado. Fontes históricas já relocadas continuam pelos mesmos IDs e provas de relocação; não exigir seu retorno ao Shared Drive.

## Procedimento somente leitura

1. Recuperar o pedido original, manifest/claim e IDs exatos. Inspecionar a pasta indicada e seus parents reais; inventário recursivo é diagnóstico do escopo identificado, não autorização para tratar arquivos vizinhos.
2. Resolver cada source ID pelo relatório e inventário, incluindo links de duplicata, sem usar filename como identidade. Separar recebidos, novos, duplicatas, concluídos e sem contexto.
3. Consultar os resolvedores `ares_archive_locations` e `ares_archive_storage`; manter registros lógicos distintos de metadata nativa do provider e do stock. IDs/paths legados não tornam o My Drive um Shared Drive.
4. Conferir namespace/naming da operação. CAR Brasil em português do Brasil usa CAR_BR_BR; PT só quando Portugal é explícito. Não criar subpastas intermediárias de placement/idioma para satisfazer um path antigo.
5. Validar destino atual: common em 01_READY, exclusivo na pasta registrada `<NOME> - Exclusivos`, ou uso confirmado em `<NOME> - Usados`; replay/duplicata não pode desfazer reserva, uso ou movimentação legítima posterior.
6. Conferir native owner/ACL/ancestrais, request/receipt/ACK e alvo de atalho/provider, conforme o backend ativo. Falta de driveId é legítima no arquivo dos 30 TB.
7. Na verificação forte, baixar cada provider do conjunto, comparar tamanho/SHA-256 com a prova de sanitização e executar o verificador de metadados. Para RAW retido, verificar seu ID/bytes e a prova exata de relocação, não inventar um recibo de exclusão.
8. Verificar saída do staging separadamente, por IDs e receipts da manutenção. No binding flat de preservação, fontes saem por movimento de mesmo ID, nunca por DELETE/trash.
9. Reportar contagens e links permanentes por classe, sem reprocessar/reentregar um lote concluído para corrigir apenas sua explicação.

## Critério de sucesso do lote congelado

- Toda source do lote reconciliada a uma única linhagem/destino ou duplicata explicitamente identificada.
- RAW/clean, provider/stock, nome, hashes, sanitização, reserva e acesso coerentes com o estado atual autorizado.
- Receipt/ACK e conclusão/entrega canônicos comprovados; nenhuma prova inventada.
- Falhas do lote = zero para declarar conclusão integral. Materiais não relacionados na entrada são contados separadamente, não exigidos como zero global.
- Primeiro novo pedido real é distinto de canário técnico e não é presumido a partir de monitor idle.

## Pitfalls e resposta

Não mover RAW antes de validar clean; não confundir SHA do bruto com clean_sha256; não confirmar por relatório antigo sem readback atual; não criar outra linhagem ou outro writer. Se a execução original estiver ativa, supervisionar somente leitura. Responder com resultados e destino reais, pendências específicas e links; nunca chamar todo destino de READY se a entrega foi Exclusivos ou Usados.
