# Entrega final em pasta de gestor

## Autoridade e limites

Consultar a autoridade vigente em `/root/mgs-agent/data/ares/creative-ops/manager-delivery-policy.json`; manter IDs de aprovação e histórico nessa fonte, não duplicá-los no procedimento. Pedidos explícitos equivalentes de usuários Ares Creative Ops autorizados não precisam de novo OK do CEO quando cobertos pela política ativa. Isso inclui recuperar a mesma rota delimitada; não inclui credenciais, ACL/permissões, nova estrutura, exclusão, campanhas, budget, billing, migração histórica ou relaxar guards globais.

## Execução

1. Retomar o plano congelado, IDs e hashes; conferir usuário/request, pasta exata existente/registrada e reserva. Antes de pedir ao gestor que mova fontes ou iniciar writes, validar os dois extremos do transporte e a compatibilidade da conclusão/retirada com o destino final. Testar o handler correspondente à ação real: o guard de transferência entre drives ou de mudança de status não substitui o preflight da rota dedicada de entrega ao gestor. Quando a origem for corrigida pelo usuário, tratar os existentes; não transformar a passagem técnica em mudança de destino.
2. Validar clean em `<OP>/<IMG|VID>/01_READY` no staging e RAW em `99_LEGACY`; registrar inventário e hashes. Usar somente SA canônica.
3. Enfileirar exclusivamente as linhagens do pedido pelo produtor canônico, com lock e jobs persistidos. Usar o owner/stock transport existente, nos mesmos limites, até ACK nativo, aliases e `stockTransferredToArchive=true` nos dois membros do par.
4. Simular e depois executar a entrega dedicada para cada `asset_id`, com a mesma identidade do pedido:

```text
python3 /root/mgs-agent/scripts/ares_manager_delivery.py --asset-id <asset_id> --destination <folder_id_exato> --requester-id <usuario_autorizado> --thread-id <thread_do_pedido_ou_continuacao> --message-id <mensagem_explicita> [--apply]
```

Sem `--apply`, só verifica/plano. O destino deve ser exatamente a pasta corporativa do gestor do inventário, filha de CRIATIVOS permanente. Não aceitar pastas arbitrárias, origem RAW, asset usado ou elegível. Não executar PATCH paralelo por fora deste runner nem mudar o handler genérico de status.

5. A rota usa os locks fila→inventário, verifica ACK/par/checksums/capabilities, persiste intent CAS e move **o mesmo stock shortcut** clean. O provider binário permanece no arquivo READY imutável; o ID lógico e o RAW não mudam. Em resultado ambíguo, o mesmo intent é reconciliado pelo parent/hash antes de outro PATCH; não criar cópia nova.
6. Exigir recibo `mgs.manager.delivery.receipt.v1` em `30tb-archive/manager-delivery/delivery-<logical_id>.json`, parent final nativo, bytes e inventário. O inventário registra `manager_media_folder_id`, `manager_delivery_receipt`, `asset_stock_file_id`, `asset_provider_id` e `asset_path` real.
7. Auditar o lote completo já entregue e congelar essa evidência antes da conclusão canônica. Com `requested_manager_final_parent` no plano, executar:

```text
python3 /root/mgs-agent/scripts/ares_manual_intake_completion.py --execution-dir <diretorio_canonico_do_lote> --requester-id <autor_do_pedido> --apply
```

Exigir recibo de conclusão, batch `complete` e cobertura de todas as fontes no índice canônico. O verificador reconcilia staging READY, recibos de gestor e arquivo real, sem substituir o destino final por READY. Em continuação de lote já concluído, preservar plano e auditoria e confirmar `already_complete`; não regravar a evidência com novos timestamps, pois seu hash integra a prova de conclusão.
8. A retirada é etapa separada do controlador existente. A validação aceita o parent de gestor **somente** para clean com recibo exato, policy ativa e inventário compatível. RAW, provider e arquivo mantêm seus paths/ACKs. Não executar DELETE nem alterar limites/autorização da retirada.
9. Reconciliar também o manifesto de retomada original, o estado por fase e o checkpoint: marcar o pedido encerrado, preservar o bloqueio anterior como histórico supersedido e remover instruções de próxima ação já cumpridas. Separar `dry_run_remote_writes=0` da indicação de execução real; não deixar um marcador de simulação parecer ausência de writes após a entrega. Comunicar contagens, link da pasta efetiva e mapa completo original→final. Só após auditoria e conclusão canônica remover mídia transitória local; preservar manifestos e recibos.

## Testes e segurança

Executar testes offline `test_ares_manager_delivery.py`, regressões de archive/retirement/manual completion e verificação real do pedido. As fixtures Shared-Drive históricas devem isolar explicitamente `locations.active()` do cutover vivo; não afrouxar a produção para fazer fixtures antigas passarem. Rodar módulos de teste com aliases/imports sintéticos em interpretadores separados para não misturar identidades de `ArchiveError`; somar somente as contagens efetivamente executadas. `pytest` não é pressuposto: os testes unittest podem rodar com a biblioteca padrão.
