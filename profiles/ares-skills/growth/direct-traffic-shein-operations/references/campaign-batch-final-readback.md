# SHEIN — recibo e readback final de lotes multifonte

Use após cada linha terminal e novamente ao fechar um lote cuja recuperação tenha demorado. Este é um procedimento de leitura e consolidação; não cria objetos, não ativa campanhas e não substitui o QA central.

## 1. Consolidar cada linha antes de avançar

Leia o state, o checkpoint e as árvores finais da mesma identidade determinística. Normalize coleções Graph pela lista `data`, conservando o envelope original para helpers que o exigem. Confira conta, quantidade de campanhas e anúncios, budget, estratégia/cap, horário, status e lineage contra a fonte daquela linha. Fontes diferentes podem ter cardinalidades e lances diferentes.

Exija campanhas únicas entre linhas. Em duplicação igual, compare a cardinalidade e o conjunto de `source_ad_id` com `state.source.ads`; não aplique essa igualdade aos clones com grupos explícitos de mídia nova. Para cada campanha, compare os conjuntos não vazios de ad IDs e creative IDs com `state.media_qa[campaign_id]` e exija `verified=true`. Uma prova válida para outros IDs não cobre a árvore atual. Em retomadas, compare campaign/adset/ad IDs das árvores finais com os bundles do checkpoint para provar ausência de recriação.

Atualize o agregador antes de passar à próxima fonte: números/IDs novos, anúncios reais, budget, estratégia/cap, início, cobertura QA e comparação de IDs por fonte. Some o budget dos campaign IDs novos únicos; não derive o delta do request pela diferença entre snapshots globais da conta, que podem conter alterações concorrentes. Copie também `state.qa_warnings` de cada linha: `qa_proof.warnings` pode não existir e um fallback vazio perderia ressalvas reais.

## 2. Resolver a definição sem despejar payloads

Inspecione o tipo de `state.target_manifest` antes de tratá-lo como caminho: o runner single-clone pode guardar ali o manifest embutido, com `campaigns`. Indexe as definições por nome canônico exato e confronte cada árvore com sua própria definição. Não imprima o manifest inteiro para descobrir o schema: creative payloads podem conter thumbnails com URLs temporárias assinadas e centenas de campos de features.

Projete na saída somente conta, número/IDs, fase, budget, lance, horário e resultados das comparações. Preserve a definição completa no registro canônico existente e use-a em memória durante a verificação.

## 3. Relê-las ao final de recuperação demorada

Releia também os grupos concluídos primeiro, sem reexecutar o writer nem reativar grupos terminais pausados posteriormente. Use `graph_batch_get(token, requests)` com até 50 itens `{name, path, params: {fields, limit}}`; desempacote `(http, rows, headers)`, exija HTTP200 externo e `row.code == 200` para cada resposta antes de decodificar `row.body`. Peça os campos materiais dos creatives. Confira paginação de todos os edges: um `limit` alto não prova completude.

Quando a resposta expandir campanha, anúncios e conjuntos no mesmo objeto, monte a árvore esperada pelo helper:

```python
live = json.loads(row['body']) if isinstance(row['body'], str) else row['body']
tree = {
    'campaign': {k: v for k, v in live.items() if k not in ('ads', 'adsets')},
    'ads': live['ads'],
    'adsets': live['adsets'],
}
assert not tree['ads'].get('paging', {}).get('next')
assert not tree['adsets'].get('paging', {}).get('next')
assert shein_qa.proof_covers(state['media_qa'][live['id']], tree)
```

Preserve `tree['ads']` como envelope `{data: [...]}`: `proof_covers` acessa `live['ads']['data']`. Normalize para lista somente nos comparadores que a exigem. Reutilize a prova renderizada apenas após QA semântico completo e cobertura dos mesmos ad/creative IDs não vazios.

Compare cada árvore com seu target manifest: conta, nome, budget, estratégia/cap, início timezone-aware, status e cardinalidade. Confira o tracking na localização definida pelo payload aprovado, Page/Instagram, CTA e enrollment de Multi-advertiser ads. Cobertura dos mesmos IDs na prova renderizada não substitui essas comparações materiais. Se for afirmar que budget e lance das fontes ficaram preservados, releia esses campos nas fontes; divergência atual exige reconciliação, não atribuição automática de causa.

## 4. Persistir e comunicar a conclusão

Grave um recibo agregado sanitizado com os resultados verificáveis e os campos necessários, sem copiar respostas Graph completas, `object_story_spec`, `media_sourcing_spec` ou thumbnails. Exija cobertura integral da soma das quantidades pedidas, ausência de IDs sobrepostos, budget somado por campanha única e quantidade real de anúncios. Derive dele o checkpoint final e a resposta, evitando totais ou resumos paralelos.

Conclua somente quando todas as linhas estiverem verificadas. Se houver pendência, informe precisamente a cobertura concluída sem anunciar sucesso global. Responda na thread de origem, com um bullet por fonte e seus números novos, seguido de budget por campanha e total do lote, início/fuso, lances efetivos, status e total real de anúncios. Não confunda orçamento do lote com orçamento ativo total da conta.

Conserve na resposta as ressalvas de `state.qa_warnings` por fonte. Declare posts novos ou normalizações somente conforme as provas da linha afetada, sem generalizá-las ao lote. Data futura e ACTIVE significam habilitada/programada, não entrega comprovada.
