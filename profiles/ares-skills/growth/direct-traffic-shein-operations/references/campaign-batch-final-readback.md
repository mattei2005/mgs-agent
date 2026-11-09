# SHEIN — recibo e readback final de lotes multifonte

Use após cada linha terminal e novamente ao fechar um lote cuja recuperação tenha demorado. Este é um procedimento de leitura e consolidação; não cria objetos, não ativa campanhas e não substitui o QA central.

## 1. Consolidar cada linha antes de avançar

Leia o state, o checkpoint e as árvores finais da mesma identidade determinística. Normalize coleções Graph pela lista `data`, conservando o envelope original para helpers que o exigem. Confira conta, quantidade de campanhas e anúncios, budget, estratégia/cap, horário, status e lineage contra a fonte daquela linha. Fontes diferentes podem ter cardinalidades e lances diferentes.

Exija campanhas únicas entre linhas. Em duplicação igual, compare a cardinalidade e o conjunto de `source_ad_id` com `state.source.ads`; não aplique essa igualdade aos clones com grupos explícitos de mídia nova. Para cada campanha, compare os conjuntos não vazios de ad IDs e creative IDs com `state.media_qa[campaign_id]` e exija `verified=true`. Uma prova válida para outros IDs não cobre a árvore atual. Em retomadas, compare campaign/adset/ad IDs das árvores finais com os bundles do checkpoint para provar ausência de recriação.

Atualize o agregador antes de passar à próxima fonte: números/IDs novos, anúncios reais, budget, estratégia/cap, início, cobertura QA e comparação de IDs por fonte. Some o budget dos campaign IDs novos únicos; não derive o delta do request pela diferença entre snapshots globais da conta, que podem conter alterações concorrentes. Copie também `state.qa_warnings` de cada linha: `qa_proof.warnings` pode não existir e um fallback vazio perderia ressalvas reais.

## 2. Resolver a definição sem despejar payloads

Inspecione o tipo de `state.target_manifest` antes de tratá-lo como caminho: o runner single-clone pode guardar ali o manifest embutido, com `campaigns`. Indexe as definições por nome canônico exato e confronte cada árvore com sua própria definição. Não imprima o manifest inteiro para descobrir o schema: creative payloads podem conter thumbnails com URLs temporárias assinadas e centenas de campos de features.

Projete na saída somente conta, número/IDs, fase, budget, lance, horário e resultados das comparações. Preserve a definição completa no registro canônico existente e use-a em memória durante a verificação.

Em conferência read-only após ação manual, registre os resultados por critério, sem encerrar a coleta no primeiro drift: uma diferença de orçamento não impede conferir status, rejeições, copy, tracking, lance, horário e identidade dos demais objetos. Execute `verify_readback` por campanha com sua definição original e retenha a falha sem afrouxar o comparador; mantenha separados `semantic_verified_against_original`, cobertura de IDs renderizados e verificações específicas aprovadas. Não altere o budget esperado em uma cópia do manifest para fabricar um PASS. Derive o total atual das leituras e apresente-o separado do total originalmente solicitado; não atribua a autoria da mudança sem evidência.

## 3. Relê-las ao final de recuperação demorada

Releia também os grupos concluídos primeiro, sem reexecutar o writer nem reativar grupos terminais pausados posteriormente. Use `graph_batch_get(token, requests)` com até 50 itens `{name, path, params: {fields, limit}}`; desempacote `(http, rows, headers)`, exija HTTP200 externo e `row.code == 200` para cada resposta antes de decodificar `row.body`. Peça os campos materiais dos creatives. Confira paginação de todos os edges: um `limit` alto não prova completude.

Antes das asserções semânticas, conserve a projeção sanitizada das leituras bem-sucedidas e a cobertura por `name`; identifique cada falha por etapa, objeto, campo e esperado/observado seguros. Em falha de transporte ou child, projete somente HTTP, código/subcode e identidade da consulta, sem body Graph bruto, headers sensíveis, cursores ou URLs assinadas. Uma `AssertionError` sem contexto não permite distinguir leitura incompleta, diferença de tipo e drift material, e força recolher dados já disponíveis. Reutilize as respostas válidas para diagnosticar o verificador; faça novo GET somente quando faltar cobertura ou frescor, nunca novo write para testar uma comparação.

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

Reutilize o comparador central `ares_campaign_v3.shein_single_clone.verify_readback` em vez de manter um segundo validador parcial de mídia/copy/recursos. Ele compara somente `payload['campaigns'][0]`: para cada árvore, selecione sua definição pelo nome canônico exato e passe uma cópia do target manifest contendo apenas essa campanha. Não passe o manifest multifonte inteiro repetidamente, pois as campanhas posteriores seriam comparadas com a primeira. Preserve o manifest selado e os contextos de review exigidos pela rota; se o helper apontar divergência, diagnostique-a sem remover o gate nem substituir a comparação por contagem de IDs.

```python
from copy import deepcopy
from ares_campaign_v3.shein_single_clone import verify_readback
from ares_campaign_v3.shein_qa import proof_covers

by_name = {definition['name']: definition
           for definition in state['target_manifest']['campaigns']}
payload = deepcopy(state['target_manifest'])
payload['campaigns'] = [by_name[tree['campaign']['name']]]
fresh_warnings = verify_readback(payload, state['source'], tree)
assert proof_covers(state['media_qa'][tree['campaign']['id']], tree)
```

Acumule `fresh_warnings` por fonte junto de `state.qa_warnings`; uma verificação nova sem ressalvas não apaga avisos anteriores. Execute separadamente os checks de quantidade total, unicidade e igualdade com checkpoint, pois o comparador semântico de uma árvore não prova a integridade do lote.

Faça essa releitura num batch account-scoped com uma entrada por campanha nova e uma por fonte distinta; identifique cada entrada por `name` único. Exija correspondência exata entre nomes pedidos e retornados, além dos códigos HTTP, antes de associar respostas às linhas. Nas fontes, leia `daily_budget`, `bid_strategy` e `adsets{bid_amount}`; nos alvos, leia também identidade, status, início, filhos e campos materiais dos creatives. Compare o cap com a fonte da própria linha, nunca com o primeiro grupo. Normalize `daily_budget` e `bid_amount` presentes para `int` nas unidades menores já comprovadas antes de comparar ou somar: a Meta pode devolver budget como string e cap como inteiro na mesma árvore. Rejeite ausência, booleanos ou valores não integrais em vez de convertê-los silenciosamente para zero; preserve o payload original. Diferença apenas de tipo no verificador não é drift de campanha e não autoriza write nem replay. Compare instantes com `datetime.fromisoformat`, não strings de offset: `-0500` e `-05:00` podem representar o mesmo horário.

Em lotes NOW, valide o horário de cada campanha antes de gravar o recibo: bundles posteriores podem receber da Meta um início diferente do timestamp técnico selado. Não imponha igualdade literal para esse caso nem aceite uma tolerância genérica em segundos. Se os instantes divergirem, use o validador puro `ares_campaign_v3.shein_copy_schedule.normalized_schedule_proof` com state, checkpoint e identidade exatos; ele exige o início observado no readback original e dentro da janela auditada de `adset_copy` daquele bundle. Exija ainda que todos os conjuntos tenham o mesmo instante da campanha. Essa validação reaproveita a prova existente, sem rede, write de schedule ou nova execução do writer:

```python
from datetime import datetime
from ares_campaign_v3.shein_copy_schedule import normalized_schedule_proof

expected = definition['start_time']
observed = tree['campaign']['start_time']
if datetime.fromisoformat(expected) != datetime.fromisoformat(observed):
    proof = normalized_schedule_proof(
        state, checkpoint,
        request_id=state['request']['request_id'],
        account_id=tree['campaign']['account_id'],
        campaign_id=tree['campaign']['id'],
        idempotency_key=definition['idempotency_key'],
        expected=expected, observed=observed,
    )
    assert proof and proof['verified']
    # Registrar a normalização comprovada no recibo; preservar o manifest.
assert all(datetime.fromisoformat(adset['start_time']) ==
           datetime.fromisoformat(observed) for adset in adsets)
```

Use `adsets` já normalizados e não vazios. Se a prova falhar, diagnostique o diff material; uma asserção local do verificador não invalida automaticamente a conclusão central nem autoriza replay, alteração de horário ou recriação. Inícios futuros explícitos continuam exigindo igualdade exata de instantes.

Antes de classificar o lote como futuro ou NOW, compare `state.request` com `state.resolved_request`: o dry-run pode anteceder a meia-noite e o execute ocorrer depois dela. Confira `resolved_request.start_now` e `schedule_adjustment`, preservando `requested_start_time` e o motivo da resolução; não reutilize o diagnóstico temporal do dry-run nem deduza agendamento pelo enum `COMPLETE_FUTURE_ACTIVE`. Quando a política vigente tiver resolvido o horário vencido do próprio dia para `IMMEDIATE_AFTER_QA`, valide os inícios observados pela receita NOW acima, por campanha e bundle, sem editar o input original ou pedir nova aprovação somente pelo atraso. Sem essa resolução comprovada, não aplique tolerância NOW a um início futuro explícito.

Para confirmar ausência de drift depois da ativação, compare cada creative vivo com a definição aprovada e a árvore terminal persistida usando uma projeção material: Page/Instagram, texto, título, descrição, CTA/link, `url_tags`, mídia/variantes, `contextual_multi_ads` e post quando aplicável. Não compare o payload bruto nem inclua thumbnail/source URL temporária na projeção: a renovação de assinatura não é mudança criativa. Exija ainda unicidade separada dos conjuntos de campaign, adset e ad IDs entre linhas; igualdade de quantidade de campanhas não detecta filho repetido ou omitido.

## 4. Persistir e comunicar a conclusão

### Conferências pós-ativação e do acervo

- Releia o estado dos anúncios após a ativação: o snapshot histórico ACTIVE não exclui rejeição posterior. `issues_info` com `2490468` comprova análise rejeitada, não a razão editorial específica. Preserve IDs, mídia/copy e parâmetros; não force ativação nem recrie conteúdo como sondagem. Registre a cobertura atual e peça somente a decisão nova de revisão ou conteúdo corrigido. Se o aviso final já foi entregue, corrija a mesma mensagem com journal e GET, sem segundo POST, e mantenha o pedido aberto até satisfazer o aceite integral.
- Para validar Usados, resolva o destino pelo binding vivo `ares_manager_storage_standard.destination`. `new_media_assets.testing_parent_id` pode guardar Exclusivos no snapshot do intake, não o parent final de `confirm-use`. Confira pelo mesmo stock ID o parent vigente, nome, hash, reserva e assignments, além da preservação de RAW/clean; não mova arquivos para satisfazer uma expectativa antiga do verificador.


Grave um recibo agregado sanitizado com os resultados verificáveis e os campos necessários, sem copiar respostas Graph completas, `object_story_spec`, `media_sourcing_spec` ou thumbnails. Exija cobertura integral da soma das quantidades pedidas, ausência de IDs sobrepostos, budget somado por campanha única e quantidade real de anúncios. Derive dele o checkpoint final e a resposta, evitando totais ou resumos paralelos.

Se informar orçamento ativo total da conta, persista o valor realmente devolvido pelo readback, sua fonte e horário no recibo, separado do budget dos IDs novos. Não introduza esse total como literal manual no verificador ou apresente uma leitura anterior como parte do batch final. Para campanhas com budget diário no nível da campanha, inclua no batch final um GET account-scoped de `act_<account_id>/campaigns`, com `fields=id,status,daily_budget` e `filtering=[{"field":"status","operator":"IN","value":["ACTIVE"]}]`. Percorra todas as páginas, confirme IDs únicos e status configurado ACTIVE e some `int(daily_budget)` em unidades menores antes de formatar a moeda. Um `limit` elevado não dispensa a verificação de `paging.next`. Esse valor é orçamento diário configurado das campanhas ativas, não gasto nem garantia de entrega; estruturas ABO/lifetime exigem a metodologia própria, não tratar `daily_budget` ausente como orçamento zero. Mantenha o delta do pedido calculado exclusivamente pelos IDs novos.

Após `mgs-knowledge-control.py checkpoint-upsert`, selecione o checkpoint pelo ID exato, exija correspondência única e confira origem, objetivo, estado e próximo passo semanticamente. Compare `id`, `thread_id` e `source` literalmente; para conteúdo descritivo de `state`, normalize tanto o valor lido quanto os termos esperados com `.casefold()`. O controlador pode converter todo o estado para minúsculas, inclusive os rótulos de campanhas ali embutidos: normalizar apenas a palavra `complete`, mas procurar um rótulo `Cnnn` em maiúsculas, ainda produz falso negativo. Use esta ordem de comparação, com os esperados derivados do recibo verificado, não digitados como um segundo resumo:

```python
matches = [row for row in registry['checkpoints']
           if row['id'] == expected_checkpoint_id]
assert len(matches) == 1
checkpoint = matches[0]
assert checkpoint['thread_id'] == expected_thread_id
assert checkpoint['source'] == expected_receipt_path
normalized_state = checkpoint['state'].casefold()
assert all(term.casefold() in normalized_state
           for term in expected_state_terms)
```

Se uma asserção falhar depois de o upsert retornar sucesso, releia o registro exato e classifique divergência de conteúdo versus simples normalização antes de escrever novamente. Uma asserção local de apresentação não autoriza repetir o upsert, reexecutar o writer ou tratar uma conclusão Meta já verificada como falha operacional.

Conclua somente quando todas as linhas estiverem verificadas. Se houver pendência, informe precisamente a cobertura concluída sem anunciar sucesso global. Em pedido misto, apresente na ordem: pausas confirmadas por número; cópias existentes por fonte, com números novos, budget, horário configurado e status; fontes ainda não iniciadas. Não descreva horário persistido em campanha PAUSED como ativação agendada nem some cópias não criadas ao orçamento efetivamente materializado. Se precisar de review material, delimite a pergunta aos deltas comprovados e aos números/IDs afetados: aceite para cópias existentes não se transfere a fontes ainda não executadas. Evite a afirmação global “originais não alterados” quando o mesmo pedido incluiu pausas; identifique quais fontes de duplicação não receberam writes e quais campos tiveram preservação verificada.

Responda na thread de origem, com um bullet por fonte e seus números novos, seguido de budget por campanha e total do lote, início/fuso, lances efetivos, status e total real de anúncios. Não confunda orçamento do lote com orçamento ativo total da conta.

Separe os três relógios no recibo e na comunicação: horário humano solicitado, `start_time` efetivamente configurado em campanha/conjunto e instante em que a ativação foi confirmada por GET. `start_time` não é prova do horário real da ativação nem de primeira entrega. Se a meia-noite solicitada já passou, informe o ajuste uma única vez, com data por extenso e fuso; agrupe campanhas somente quando seus horários observados coincidirem. Diga “início configurado” para o campo Meta e “ACTIVE confirmado na leitura” para o status. Só informe horário efetivo de ativação quando houver prova temporal própria; sem ela, não transforme `completed_at` ou `readback_at` em timestamp do write. Não anuncie início pontual cumprido quando os horários configurados ou a confirmação ocorreram depois do solicitado.

Conserve na resposta as ressalvas de `state.qa_warnings` por fonte. Declare posts novos ou normalizações somente conforme as provas da linha afetada, sem generalizá-las ao lote. Data futura e ACTIVE significam habilitada/programada, não entrega comprovada.
