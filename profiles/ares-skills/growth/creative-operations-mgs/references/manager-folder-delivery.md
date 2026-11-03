# Entrega final em pasta de gestor

## Autoridade e limites

Consultar a autoridade vigente em `/root/mgs-agent/data/ares/creative-ops/manager-delivery-policy.json`; manter IDs de aprovação e histórico nessa fonte, não duplicá-los no procedimento. Pedidos explícitos equivalentes de usuários Ares Creative Ops autorizados não precisam de novo OK do CEO quando cobertos pela política ativa. Isso inclui recuperar a mesma rota delimitada; não inclui credenciais, ACL/permissões, nova estrutura, exclusão, campanhas, budget, billing, migração histórica ou relaxar guards globais.

## Execução

### Padrão de destino supersedente

O desenho aprovado e a ativação verificável ficam em `context/creative-manager-storage-standard.md` e `data/ares/creative-ops/manager-storage-standard.json`. A aprovação específica de Rodolfo `1566497527719661640` cobre a atualização destes procedimentos. Com o binding ativo, novos pedidos de gestor usam `MGS-ARQUIVO/CRIATIVOS/<OP>/<IMG|VID>/<NOME> - Exclusivos`. Resolver o ID exato com `python3 /root/mgs-agent/scripts/ares_manager_storage_standard.py resolve --operation <OP> --format <IMG|VID> --manager <gestor>` e conferir via SA; jamais criar pasta pela interpretação do nome, nem entregar em Usados antes de utilização comprovada.

Kelly enviando material geral permanece no fluxo de distribuição READY quando esse for o pedido; um upload destinado a gestor permanece exclusivo. Remetente, por si só, não define elegibilidade. Preservar originais, reserva e linhagem. A estrutura não autoriza campanhas sem pedido válido da origem.

Kelly informando país/vertical/língua e pedindo aplicar regras/organizar, sem gestor destinatário nem exclusividade, é distribuição `common`, não entrega de gestor: tratado em `<OP>/IMG/01_READY` ou `<OP>/VID/01_READY`. Não chamar este runner de entrega exclusiva nesse caso, não exigir destinatário desnecessário e não inferir `KELLY - Exclusivos`. O `manager_name` interno registra a origem; não muda o destino escolhido. Reservas, duplicatas e uso anteriores permanecem protegidos.

Após readback Meta das peças efetivamente utilizadas, o finalizador registrado move somente seus mesmos stock IDs de Exclusivos para Usados e registra recibo CAS/uso. Falha e peças não selecionadas permanecem exclusivas; replay conclui apenas a camada faltante. Pedidos legados já em andamento mantêm a rota antiga para recuperação, sem migrá-los implicitamente ou exigir novos uploads. Não declarar a reorganização histórica concluída pela criação destas pastas.

SHEIN usa o finalizador integrado. Nas demais rotas de Campaign Ops, após registrar o uso real da linhagem no inventário, executar `python3 /root/mgs-agent/scripts/ares_manager_storage_standard.py confirm-use --asset-id <asset_id> --request-id <request_id>` em leitura e depois com `--apply`. O helper lê o anúncio Meta existente, confere conta/campanha/adset/creative e mídia, exige a mesma reserva e move o mesmo stock ID; não cria campanhas, não libera reserva nem troca tokens. Uso sem ID exato ou conflito de request permanece bloqueado. Este fechamento integra a entrega do Ares; não devolvê-lo como tarefa manual ao gestor.

1. Retomar o plano congelado, IDs e hashes; conferir usuário/request, pasta exata existente/registrada e reserva. Antes de pedir ao gestor que mova fontes ou iniciar writes, validar os dois extremos do transporte e a compatibilidade da conclusão/retirada com o destino final. Testar o handler correspondente à ação real: o guard de transferência entre drives ou de mudança de status não substitui o preflight da rota dedicada de entrega ao gestor. Quando a origem for corrigida pelo usuário, tratar os existentes; não transformar a passagem técnica em mudança de destino.
2. Validar clean em `<OP>/<IMG|VID>/01_READY` no staging e RAW em `99_LEGACY`; registrar inventário e hashes. Usar somente SA canônica.
3. Enfileirar exclusivamente as linhagens do pedido pelo produtor canônico, com lock e jobs persistidos. Usar o owner/stock transport existente, nos mesmos limites, até ACK nativo, aliases e `stockTransferredToArchive=true` nos dois membros do par.
4. Simular e depois executar a entrega dedicada para cada `asset_id`, com a mesma identidade do pedido:

```text
python3 /root/mgs-agent/scripts/ares_manager_delivery.py --asset-id <asset_id> --destination <folder_id_exato> --requester-id <usuario_autorizado> --thread-id <thread_do_pedido_ou_continuacao> --message-id <mensagem_explicita> [--apply]
```

Sem `--apply`, só verifica/plano. Para novos pedidos, o destino deve ser a pasta Exclusivos registrada da operação, formato e gestor do inventário. A exigência antiga de filha direta de CRIATIVOS fica supersedida somente por esses bindings; pastas legadas são aceitas apenas no caminho de compatibilidade do executor. Não aceitar pastas arbitrárias, origem RAW, asset usado ou elegível. Não executar PATCH paralelo por fora deste runner nem mudar o handler genérico de status.

5. A rota usa os locks fila→inventário, verifica ACK/par/checksums/capabilities, persiste intent CAS e move **o mesmo stock shortcut** clean. O provider preserva ID/bytes/ACK e o ID lógico/RAW não muda; resolver localização pelo binding, não presumir que sua árvore física continue diretamente na raiz ou em READY. Em resultado ambíguo, o mesmo intent é reconciliado pelo parent/hash antes de outro PATCH; não criar cópia nova.
6. Exigir recibo `mgs.manager.delivery.receipt.v1` em `30tb-archive/manager-delivery/delivery-<logical_id>.json`, parent final nativo, bytes e inventário. O inventário registra `manager_media_folder_id`, `manager_delivery_receipt`, `asset_stock_file_id`, `asset_provider_id` e `asset_path` real.
7. Auditar o lote completo já entregue e congelar essa evidência antes da conclusão canônica. Com `requested_manager_final_parent` no plano, executar:

```text
python3 /root/mgs-agent/scripts/ares_manual_intake_completion.py --execution-dir <diretorio_canonico_do_lote> --requester-id <autor_do_pedido> --apply
```

Exigir recibo de conclusão, batch `complete` e cobertura de todas as fontes no índice canônico. O verificador reconcilia staging READY, recibos de gestor e arquivo real, sem substituir o destino final por READY. Em continuação de lote já concluído, preservar plano e auditoria e confirmar `already_complete`; não regravar a evidência com novos timestamps, pois seu hash integra a prova de conclusão.
8. A retirada é etapa separada do controlador existente. A validação aceita o parent de gestor **somente** para clean com recibo exato, policy ativa e inventário compatível. RAW, provider e arquivo mantêm seus paths/ACKs. Não executar DELETE nem alterar limites/autorização da retirada.
9. Reconciliar também o manifesto de retomada original, o estado por fase e o checkpoint: marcar o pedido encerrado, preservar o bloqueio anterior como histórico supersedido e remover instruções de próxima ação já cumpridas. Separar `dry_run_remote_writes=0` da indicação de execução real; não deixar um marcador de simulação parecer ausência de writes após a entrega. Comunicar contagens, link da pasta efetiva e mapa completo original→final. Só após auditoria e conclusão canônica remover mídia transitória local; preservar manifestos e recibos.

## Acervo legado e namespace físico

Consultar `context/creative-archive-legacy-consolidation.md` e o binding `30tb-archive/legacy-consolidation/`. As árvores antigas, pilotos e estruturas técnicas foram preservados sob `CRIATIVOS/_ARQUIVO_FISICO`, sem nova entrada de upload. Novos pedidos continuam usando os destinos registrados; nomes de pastas legadas não provam uso nem liberam reservas. Exceções ambíguas ficam preservadas e fora do pool até conciliação. Ler mídia pelo resolvedor canônico, que mantém IDs/ACKs e separa metadata nativa do registro lógico. Não criar árvores paralelas, reescrever provas antigas, retornar material a READY nem mover/apagar fontes no intake para silenciar alertas.

## Testes e segurança

Executar testes offline `test_ares_manager_delivery.py`, regressões de archive/retirement/manual completion e verificação real do pedido. As fixtures Shared-Drive históricas devem isolar explicitamente `locations.active()` do cutover vivo; não afrouxar a produção para fazer fixtures antigas passarem. Rodar módulos de teste com aliases/imports sintéticos em interpretadores separados para não misturar identidades de `ArchiveError`; somar somente as contagens efetivamente executadas. `pytest` não é pressuposto: os testes unittest podem rodar com a biblioteca padrão.
