# SHEIN — recuperação de preflight e ativação

Use quando uma conta permitida falhar no guard técnico, um objeto criado não tiver proveniência reconhecida ou o QA terminar mas a ativação não fechar. Para recuperação de mídia/cópias e snapshot compacto, siga as seções correspondentes de `general-campaign-fast-route.md`.

## 1. Classificar a camada antes de corrigir

1. Recupere o request original e os IDs de runner/checkpoint; faça o checker positivo da conta e o dry-run pela rota central. Cadastro permitido não prova acesso live, e rejeição local anterior ao HTTP não é negativa da Meta.
2. Identifique a chamada exata pela receita `Classificar rejeição local antes de diagnosticar a Meta` da referência geral. Restrinja instrumentação ao dry-run; não suprima exceções do guard nem instrumente um execute live.
3. Separe manutenção autorizada da transação de campanha: preserve backup e IDs existentes, corrija somente a incompatibilidade demonstrada, rode regressões negativas e volte ao mesmo request após o dry-run aprovado. Nunca transforme falha local em pedido de outra credencial ou liberação global de nós.

## 2. Guard e proveniência de dependências técnicas

1. Trate `/me?fields=id,name,client_business_id` como GET técnico restrito, com readback do Business operacional e identidade exigida pelo runner. Não conceda por consequência `/me/adaccounts`, descoberta de portfólios ou writes de identidade.
2. Diferencie objetos Marketing API de Pages/vídeos/pixels referidos em respostas já account-scoped. Registre essas dependências com tipo e contas comprovadas, somente para leituras necessárias. Exija Business exato na leitura de tarefas; não promova Page ou usuários retornados por `assigned_users` a objetos mutáveis. Uma Page compartilhada não concede acesso às outras contas que a usam.
3. Para rejeição em `observe_meta_response` após GET account-scoped de `adspixels`, confronte o nó conflitante com o edge observado e a proveniência anterior: um pixel compartilhado pode ter sido cadastrado erroneamente como objeto exclusivo de outra conta permitida. Quando ambas as evidências forem positivas e o problema estiver somente nessa classificação local, faça manutenção de dados separada sob o lock da proveniência, com backup/recibo, convertendo exclusivamente esse nó em `scoped_graph_dependency`, `kind=pixel` e a união das contas comprovadas. Isso restringe o nó a GET `id,name`; nunca altere a allowlist, o pixel Meta, o guard ou proveniência de campanhas/conjuntos/anúncios. Verifique diff de uma única linha, GET permitido, POST/conta desconhecida/descoberta negados e REPORT-INFRA; depois retome dry-run e o mesmo request. A correção local não comprova criação: exigir QA/readback integral e igualdade dos IDs após retomada.

4. Verifique o transporte central além do cliente Graph comum: `GraphBatchTransport` deve aplicar o guard antes do HTTP, vincular cada nó à lane correta e observar respostas bem-sucedidas antes da próxima etapa. Registre `copied_campaign_id`, `copied_adset_id` e `copied_ad_id` dos receipts, inclusive em batches parcialmente rejeitados. Falha de observação após HTTP deve conservar `successful_children`, pois os objetos já podem existir.
5. Se os objetos forem anteriores à integração de proveniência, faça GET paginado de campanhas da conta autorizada e GET dos filhos; confira os IDs contra o request antes de continuar. Não semeie proveniência apenas com IDs do checkpoint e não copie novamente para resolver uma leitura.
6. Teste a camada comum e o Engine juntos, incluindo: identidade restrita; Business divergente; conta desconhecida; Page write; descoberta; lane divergente; dependência compartilhada; receipt de cópia; e IDs preservados após falha de observação. Execute com o Python de testes verificado:

```text
<PYTHON_DE_TESTES> -m pytest -q tests/test_ares_campaign_engine_v3.py tests/test_mgs_ares_asset_scope.py tests/test_ares_confidentiality_routes.py tests/test_ares_scope_campaign_dependencies.py
```

Execute no repositório e use `PYTHONPATH=/root/mgs-agent/scripts` quando necessário. Testes offline e dry-run não comprovam criação ou serving: retome o request autorizado e exija QA/readback reais. Recusa de outra chamada exige novo diagnóstico pontual, não acesso genérico.

## 3. Ativação parcial sem replay

1. Após erro de transporte ou de status, releia `state.phase`, `media_qa`, `qa_proof` e `media_postprocess_complete`. Para `ACTIVATION_PENDING` com QA completo, abra também `engine-v3/state/activation/<request_id>-<account_id>.json`: o checkpoint de criação pode continuar `COMPLETE` sem conter o erro da ativação. Não diagnostique o renderer pelo erro genérico de topo.
2. Faça GET dos campaign/adset/ad IDs existentes e compare `configured_status` (ou `status` quando ausente), conta, parents e creative IDs com a prova. Um batch pode deixar alguns filhos ACTIVE sob campanha PAUSED; um erro de readback pode ocorrer depois de todos ficarem ACTIVE. Nenhum desses estados autoriza recriação.
3. Com autoridade vigente, QA cobrindo os mesmos IDs e sem gate de quota/review, retome somente a rota central:

```text
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input <mesmo-request.json> --confirm-execute
```

Deixe a ativação reler e escrever somente os status faltantes; quando todos já estiverem ACTIVE, reconcilie o fechamento sem novos writes. Não envie updates diretos, não volte à cópia e não apague provas para reiniciar o pedido.
4. Compare status por ID, provas válidas e estágio após cada tentativa. Progresso comprovado permite continuação controlada; falta de avanço exige diagnóstico antes de outro retry. Respeite `retry_after_seconds`; trate `E2E_TARGET_EXCEEDED` como review, não como transiente. Só avance à próxima fonte após árvores finais e igualdade de IDs verificadas.
5. Para diagnosticar `BatchTransportError`, projete somente `stage`, tipo, HTTP, códigos/subcodes Meta e nomes dos children. Capture também outras exceções para não expor trace bruto. O padrão confiável é readback antes da retomada, não repetir a mesma chamada até passar.
