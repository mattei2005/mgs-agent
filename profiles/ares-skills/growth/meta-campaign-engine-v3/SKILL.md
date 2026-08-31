---
name: meta-campaign-engine-v3
description: "Executa campanhas Meta em lotes determinísticos v3."
version: 3.4.1
author: Rodolfo Mattei, Ares, Zeus
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, ares, meta-ads, campaign-engine, batch, high-scale]
    related_skills: [direct-traffic-cbo-operations, paid-acquisition-operations]
---

# Meta Campaign Engine v3 — MGS/Ares

Motor central e versionado de Campaign Ops. O agente interpreta o pedido e materializa um manifest; o executor cria/clona campanhas sem `Searching`, edição de código ou descoberta de rota dentro do hot path.

## When to use

Use para:

- criar ou clonar campanhas Meta;
- executar lotes em uma ou várias contas;
- usar mídia pre-stageada na library da Meta;
- medir throughput, quota e readback por lane;
- migrar uma operação do executor v2.

Não use para editar credencial, billing, app permissions, pixel crítico, ChatPion, quiz, SMS Funnel ou WordPress.

## Fontes canônicas

```text
Config v3       /root/mgs-agent/data/ares/meta-ads/engine-v3/config.json
Operações       /root/mgs-agent/data/ares/meta-ads/operations/*-v3.json
Media registry  /root/mgs-agent/data/ares/meta-ads/engine-v3/media-registry.json
Executor         /root/mgs-agent/scripts/ares-campaign-engine-v3.py
Runner diário CPV /root/mgs-agent/scripts/ares-creditoparaveiculo-v3-daily.py
Módulos          /root/mgs-agent/scripts/ares_campaign_v3/
Audits           /root/mgs-agent/data/ares/meta-ads/engine-v3/audit/
State/lanes      /root/mgs-agent/data/ares/meta-ads/engine-v3/state/
```

## Progressive disclosure

1. Arquitetura, lanes, batch e segurança → `references/architecture-and-runtime.md`.
2. Contrato do manifest e comandos → `references/manifest-and-commands.md`.
3. Migração e rollback v2→v3 → `references/migration-v2-to-v3.md`.
4. Pesquisa da Meta → `references/official-meta-sources.md`.

Carregue somente a referência do branch atual.

## Invariantes

1. Hot path: pedido → manifest → um executor determinístico → readback final.
2. Zero busca ampla, skill discovery, patch, teste ou criação de cron durante execução.
3. Bundle padrão: duas campanhas da mesma conta.
4. Lanes independentes por `app_key + ad_account_id`; nunca misturar contas no mesmo bundle.
5. O v3 representa quatro formas distintas e nunca as trata como sinônimos: `from_zero_prestaged` = criar do zero; `clone_prestaged` = clonar estrutura/lineage e substituir por criativos novos do Drive; `pure_clone` = duplicar preservando estrutura, público, estratégia, mídia e copy; `clone_page_switch` = clonar estrutura/lineage e ads-fonte, preservar mídia/copy e rematerializar os parâmetros criativos aprovados para outra Page/UTM/JSON. Naming, tracking, budget e início seguem o contrato canônico da operação, nunca um default cruzado. Creditoparaveiculo mantém próximo sequencial, UTMs novas e sufixo `COPY C{fonte}`. Em Eggbev `1034081997659047`, clones usam `DUPnn`; criação do zero usa `[page_sequence] - [Page] - ENG - US - (pg_XXXXX) C0XX`, avançando C001, C002, C003... na ordem do lote e sem sufixo adicional. Ambos aceitam budget escolhido pelo gestor sob gate financeiro e exigem `ACTIVE` às 00:00 ET por padrão. Exceção única: o primeiro request `eggbev-pg-5024-20260830-nicolas-01` atualiza o início no execute para o horário corrente ET com buffer técnico mínimo; não propagar esse override. O planner divide 1–100 campanhas em bundles 2+2+…+1 por conta.
6. O readback consolidado usa um outer Graph batch por bundle. Em `development_access`, o bundle de duas campanhas persiste todos os IDs após a janela de writes e adia somente esse batch para a janela seguinte; zero GET intermediário e zero replay de write.
7. O ceiling local original permanece 100/120 apenas enquanto o tier está desconhecido. Header vivo `development_access` reduz efetivamente a lane a 60, com decaimento 300s; o bundle `clone_prestaged` reserva 30 por campanha (60 no par) e adia readback por `max(reset_time_duration, estimated_time_to_regain_access×60, 300)+5s`. Header vivo `standard_access` promove a lane a 9000 e remove somente o cooldown fixo de development; utilização/reset vivos continuam soberanos. Extrair o tier tanto de `X-Ad-Account-Usage` quanto de `X-Business-Use-Case-Usage`, inclusive quando o outer batch falha.
8. Canário técnico explícito nasce `PAUSED`; pedido normal de produção usa `ACTIVE` com `start_time` futuro após manifest selado e validação dos guards.
9. `prevalidated=true`, `config.enabled=true`, `write_enabled=true` e `--confirm-execute` são gates independentes.
10. V2 permanece rollback congelado; nenhum legado é apagado durante a migração inicial.
11. Em CPV `clone_prestaged`, todo `asset_ref` exige `canonical_filename` válido da taxonomia `CAR_BR_BR_VID_*_{PV|NV|PH|NH}_NNN.mp4`. O anúncio nasce como `AD NN - {canonical_stem}` e o creative como `CPV CNN ADNN {canonical_stem}`. `asset_id` permanece apenas como identidade técnica no manifest/audit; se o nome canônico faltar ou for inválido, bloquear antes de selar o manifest.
12. Em Creditoparaveiculo, o pós-processamento só conclui após auto-armar cada campanha nova no guardrail de primeiro gasto. O enrollment valida IDs, data operacional, status `ACTIVE`, gasto zero e retorna `meta_writes=0`; falha deixa o request `POSTPROCESS_PENDING`. O watcher aceita primeiro spend observado de 00:30 a 02:00 SP inclusive sem pause; fora dessa janela, pausa uma vez e agenda reativação 00:30 do dia seguinte.
13. Todo alerta operacional de erro deve identificar operação e campanhas afetadas e informar, em linguagem humana e sem paths/credenciais: etapa, causa baseada no erro real, consequência, correção em andamento e estado útil da recuperação. Mensagem genérica de “bloqueado” sem diagnóstico e ação não é conclusão suficiente.
14. Por regra permanente de Rodolfo em 24/08/2026, reafirmada em 27/08/2026, erro dentro de um request já autorizado inicia recuperação automática, não bloqueio passivo: fazer readback, reconciliar efeitos parciais, corrigir somente a camada ausente/inválida e retomar o mesmo request até concluir. Nunca repetir POST não idempotente às cegas nem ampliar budget, billing, credencial, estratégia ou escopo. Bloqueio externo mantém o request resumível e ativamente escalado. `PARTIAL_DEFERRED_QUOTA` saudável continua sendo retomada determinística, não erro. Quando todos os IDs do bundle já estiverem persistidos no estágio `children_created_readback_pending`, a recuperação executa exclusivamente `recovery_consolidated_readback`: não repete campaign/adset/ad copy nem normalização de nomes já correta.
15. Toda conclusão de criação programada informa em USD o budget ativo da conta, o envelope operacional efetivo, o saldo dentro desse envelope e a fonte: preflight Meta vivo mais budgets do request confirmados por readback. Em Creditoparaveiculo G006, USD500 é o piso e o envelope sobe somente ao total live mais os deltas exatos autorizados de criação, escala ROI e reativação; não há write de billing nem `account_spend_limit`.
16. Criação programada segue o loop de análise, mas o hold vigente pode ser liberado por Rodolfo ou Nicolas. Para Creditoparaveiculo G006, Rodolfo liberou o hold em 24/08/2026 e reativou o scheduler diário de 17:00 São Paulo; um hold futuro continua sem expiração automática e bloqueia criação/clone até nova liberação explícita.
17. Em `clone_prestaged`, cada anúncio exige `source_ad_id` não zero e nasce por `POST /{source_ad_id}/copies` com `creative_parameters`; criação direta por `act_{account}/ads` é proibida nessa rota. `clone_page_switch` usa a mesma lineage por ad copy, mas não recebe `media`: preserva a mídia/copy da fonte e rematerializa somente os parâmetros aprovados de Page/UTM/JSON. Em `from_zero_prestaged`, ocorre o inverso: IDs fonte são proibidos e campaign/adset/creative/ad nascem somente pelos edges diretos `act_{account}`. Campaign copy, adset copy, normalização de shell, ad copies e normalização de nomes continuam batches sequenciais exclusivos dos clones; criação do zero usa `campaign_create → adset_create → creative_create → ad_create → campaign_finalize → consolidated_readback`.
17a. Toda conta registrada declara explicitamente `supported_modes` e `ad_serving_route`; ausência de qualquer um falha fechado antes de selar/executar o manifest. `lineage_required_for_new_media` proíbe `from_zero_prestaged`. As contas Creditoparaveiculo 05 e 13 usam essa rota após a confirmação live de zero delivery nos anúncios diretos com `source_ad_id=0`; novos criativos entram exclusivamente por `clone_prestaged`/Ad Copies API. Apenas contas com evidência live e `direct_and_lineage_verified` podem manter criação direta.
18. Quando a fonte canônica da operação autorizar reteste, o seletor pode combinar `01_READY` com `03_TESTED` explicitamente elegível. Em CPV G006, o mix é 2 READY + 1 TESTED inconclusivo por subentrega por campanha, máximo de duas tentativas e fallback da terceira vaga para READY. Reteste nunca ignora reserva, uso ativo, lineage ou conciliação Meta×Drive; após readback do novo anúncio, o asset volta a `02_TESTING` e a tentativa é anexada idempotentemente a `test_history`.
19. Em CPV G006, a origem de `clone_prestaged` é selecionada no preflight do manifest pelo maior ROI Smart Bidding da data operacional dentro da mesma partição de veículo. `MOTO` nunca usa fonte `CARRO`, e `CARRO` nunca usa fonte `MOTO`. C08 não é template fixo: só pode vencer se tiver o maior ROI elegível na partição correta. Persistir IDs da campanha/adset/anúncios fonte, ROI, investimento, receita, data, moeda, fórmula e digest do snapshot antes de selar o manifest; ausência de fonte elegível falha fechado antes de reserva/write.
20. Em Eggbev from-zero, o runner operacional materializa e sela o manifest, mas nunca cria objetos Meta diretamente: `scripts/ares-eggbev-creation.py` delega toda execução ao Engine v3. O request aplica reconciliação scoped Drive×Meta, reserva somente após o pedido, pre-stage registry-first com títulos `asset_id + checksum curto`, três ou cinco ads por campanha, e **todas as três headlines aprovadas em cada anúncio** com `title_label` square/vertical próprio do novo creative. Cada novo creative Eggbev carrega obrigatoriamente `data/ares/meta-ads/templates/eggbev-us-cc-en-messenger-welcome.json` com identidade semântica `ecc2204e5f94203434a212737bb0110ed3d53780478a701c80809d0807f819ad`; drift bloqueia antes do write, e o pós-criação compara o JSON instalado na Meta diretamente contra esse arquivo. O pós-processamento `01_READY → 02_TESTING` ocorre apenas depois do readback Meta completo. Os nomes dos ads são derivados automaticamente como `AD NN - {canonical_stem}`; budget é input humano obrigatório em criação normal. Nicolas tem autoridade permanente de Rodolfo para definir, reduzir ou aumentar budgets Eggbev, inclusive a baseline de USD45, sem nova aprovação do Rodolfo; cada write exige valor exato, pré-leitura e readback Meta. Billing, `account_spend_limit`, credenciais e escala automática permanecem separados. Depois de toda criação Eggbev, o runner faz GET de cada creative: Page e `url_tags` são comparados com o manifest aprovado, enquanto o JSON parseado em `asset_feed_spec.additional_data.page_welcome_message` é comparado diretamente com o arquivo canônico fixo. Divergência deixa `POSTPROCESS_PENDING`, preserva IDs e proíbe replay da criação.
21. `adset_updates` é permitido somente nos modos de clone que normalizam o shell copiado. Campos controlados pelo executor (`id`, `campaign_id`, `name`, `status`, `start_time`) são proibidos nesse mapa. Em substituição revisada Eggbev, ele materializa o `promoted_object` com `custom_event_type=OTHER`, `custom_event_str=eggbev-pv-u` e o targeting manual aprovado. O readback consolidado sempre inclui `promoted_object`; divergência bloqueia a exclusão da campanha fonte.

## How to run

Validação e plan são read-only:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py validate --manifest <manifest>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py plan --manifest <manifest>
python3 /root/mgs-agent/scripts/ares-creditoparaveiculo-v3-daily.py --offline-smoke
python3 /root/mgs-agent/scripts/ares-creditoparaveiculo-v3-daily.py --dry-run --operational-date YYYY-MM-DD
python3 /root/mgs-agent/scripts/ares-eggbev-creation.py offline-smoke
python3 /root/mgs-agent/scripts/ares-eggbev-creation.py prepare --help
```

O runner diário CPV tem gate de início às 17:00 São Paulo e permite retomar o mesmo request fora da janela quando o state estiver `PARTIAL_DEFERRED_QUOTA` ou em outro estágio resumível. `--dry-run` faz somente plano live/read-only; `--offline-smoke` usa transporte fake e zero rede. O cron v3 diário está ativo desde a liberação de Rodolfo em 24/08/2026; v2 continua congelado como rollback isolado.

A execução real está ativa sob `development_access`. Cada pedido autorizado de campanha fornece o `--confirm-execute` operacional, mas não altera os gates estruturais. O guard inicial é **por lane**: em uma conta, o primeiro bundle daquela conta é guardado/fail-closed; em várias contas, o primeiro bundle de cada `app_key + ad_account_id` pode iniciar em paralelo pelo `ThreadPoolExecutor`. Não existe canário global único antes das outras lanes; os bundles seguintes de cada lane obedecem à própria quota.

## Verification

- manifest válido e digestado;
- dry-run mostra duas campanhas por bundle;
- `intermediate_get_calls=0`;
- lanes separadas por conta;
- média/p95 por estágio no audit;
- nenhuma credencial no manifest/audit;
- GET final confirma IDs, estrutura, budget, status e `start_time`;
- audit diário preserva ordem estável e registra `duration_ms` + contadores sanitizados para `meta_preflight`, `drive_preflight`, `reconciliation`, `asset_selection`, `source_selection`, `prestage`, `manifest_prevalidation`, `engine`, `postprocess` e total;
- Token é resolvido cache-first pelo helper canônico; runner/cron nunca usa `force_refresh=True` por padrão;
- antes do execute, nomes exatos do manifest não colidem com campanhas live não deletadas fora do mapeamento idempotente do mesmo request;
- títulos de pre-stage incluem `asset_id + checksum curto`, e o registry confirma `account + asset + checksum + IDs` por readback;
- falhas após possível side effect ficam `READBACK_DEFERRED`/`POSTPROCESS_PENDING`, nunca `FAILED` fora do gate;
- `BatchTransportError` persiste etapa e causa Meta sanitizada (`code/subcode/user_title`) para o alerta; paths, headers sensíveis, token e trace não entram na mensagem ao operador;
- simulação de erro confirma que o state recebe `manual_reconciliation_required=false`, `operator_authorization.required=false` e `automatic_recovery_required=true`; o recovery faz readback, preserva o mesmo request e cria somente a camada comprovadamente ausente;
- conclusão programada inclui `account_budget_after_creation`; a mensagem Discord informa budget ativo, envelope efetivo, saldo dentro do envelope e USD;
- REPORT-INFRA para qualquer mudança estrutural.

## Pitfalls

- Alterar 60→120 sem reduzir GET/validate/upload não cria escala.
- Graph batch reduz round-trips, não quota lógica.
- `IN_PROCESS` é post-processing, não falha terminal.
- Mídia crua não entra na transação: primeiro pre-stage, depois manifest.
- Advanced Access por permission, Marketing API Full Access e asset assignment são gates diferentes.
- Em `clone_prestaged`, ao substituir `asset_feed_spec.videos`, preservar em cada novo vídeo os `adlabels` do vídeo-fonte vertical/square quando `asset_customization_rules` os referencia. Remover os labels causa `code=100/subcode=2446173` mesmo com mídia pronta. O mapeamento usa dimensão/orientação real, não apenas ordem presumida.
- `rename_options` da cópia nativa de adset pode concatenar o nome-fonte com o sufixo desejado. O pós-processamento deve normalizar o adset para o nome canônico exato e validar por readback.
- Se o bundle falhar depois de criar campaign/adset shells, bloquear replay cego. Reconciliar IDs existentes, procurar filhos/orphans por escopo recente ou nomes exatos, corrigir o payload, passar `validate_only` e retomar somente a camada faltante com state/audit/readback explícitos. Em falha parcial `campaign_adset_update`, usar os `campaign_ids`/`adset_ids` persistidos no checkpoint, fazer GET de ambos, aplicar somente o shell divergente (por exemplo, `promoted_object.custom_event_str` ausente ou targeting rejeitado), confirmar por novo GET e só então retomar o mesmo request para criar anúncios ausentes; nunca repetir campaign/adset copy. No incidente Eggbev `pg_5024 DUP01`, o checkpoint preservou os shells, `explore` foi removido após `2490589`, o `promoted_object` foi corrigido para `eggbev-pv-u` e o recovery criou apenas os três ads faltantes.
- Na criação `clone_prestaged`, a ordem do pool é obrigatória: atualizar a reconciliação Drive×Meta, eliminar do conjunto candidato todo asset não aprovado, conflitante, reservado ou com identidade divergente e somente então selecionar `3 × campanhas` do Shared Drive. Conflito em um candidato faz o seletor pular para o próximo elegível; nunca bloquear o lote inteiro enquanto houver quantidade reconciliada suficiente. Bloquear apenas quando o saldo único reconciliado for menor que o necessário.
- Nunca reutilizar o state de um request já concluído como ciclo do dia seguinte. `completed_operational_date_sp` anterior fecha a execução antiga; o novo ciclo começa com request e conciliação novos.
- Quando um request resumível cruza a meia-noite de São Paulo, preservar `state.operational_date_sp` até `COMPLETE`; naming, `cycle_start_date`, first-delivery e override usam a data original do request, não a data civil da tentativa de recuperação. Se todas as campanhas já existem, o resumo de budget usa o total ativo do preflight vivo e `new_minor=0`, sem somar novamente uma campanha fantasma.
- Nunca confundir o horário de 17:00 com autorização automática para criar. O schedule apenas pode iniciar quando o lifecycle gate estiver liberado; em hold, Diário, Intraday, D1-D3, pausa, escala e first-delivery continuam ativos sem novos campaigns.
- `configured_status=ACTIVE`, `effective_status=ACTIVE`, três anúncios/creatives `ACTIVE` e `issues_info=null` não provam entrada real no leilão. Se uma cópia nativa feita no Ads Manager a partir da própria campanha API começar a imprimir/gastar enquanto o objeto-fonte permanece sem impressões, classificar como divergência de serving/release da rota, congelar novas `clone_prestaged` e comparar por Graph Batch campanha, adset, ads, creatives e Insights. Separar os dois eixos que a cópia pode alterar: `start_time` imediato versus futuro e regeneração de ad/creative/story IDs. Não culpar budget, público, revisão ou mercado sem diff vivo; qualquer canário corretivo por `deep_copy=true`, ativação imediata ou reconstrução de creative exige autorização operacional e readback de impressão/gasto, não apenas status.
- Para Video Ads, nunca pre-stagear mídia nova em `/{PAGE_ID}/videos` nem tratar `video_status=ready` da Página como associação à conta. O guia oficial exige que o `video_id` esteja associado ao ad account e aponta `act_{AD_ACCOUNT_ID}/advideos`. Upload usa o advertiser User Access Token; antes de selar o manifest, o ID retornado precisa aparecer no edge `advideos` da conta, com processamento pronto, e o registry registra `upload_edge=ad_account_advideos` + `association_verified=true`. Ausência dessa associação bloqueia creative/campaign write. Esse é um gate técnico necessário, mas não prova serving: no incidente CPV, a C20 corrigida com 6/6 vídeos associados, campanha/adset/ads/creatives ACTIVE e UTMs válidas permaneceu com zero impressão/gasto por pelo menos 45 minutos. Portanto, nunca declarar a associação como causa raiz suficiente; após esse gate, investigar reutilização de `creative_id`/post social-proof versus creative novo e divergência de serving entre API e Ads Manager. Não excluir os Page videos antigos sem reconciliação de dependências e autorização.
- A opção do Ads Manager para mostrar reações, comentários e compartilhamentos existentes corresponde ao objetivo operacional de preservar post/social proof. Para clonar campanha vencedora sem trocar mídia, preferir `pure_clone` ou criar os novos anúncios referenciando exatamente os `creative_id`/post IDs aprovados; validar por readback se a Meta reutilizou ou rematerializou IDs. `clone_prestaged` com criativos inéditos do Drive necessariamente cria creatives/posts novos e não preserva social proof; seu gate é mídia em `advideos` da conta, identidade Drive↔Meta, UTM e serving real.
- Em `clone_prestaged`, nunca descartar `source_ad_id` do template. O campo é aceito pela API na criação do anúncio e o endpoint oficial `/{ad_id}/copies` permite `adset_id` + `creative_parameters`, criando uma cópia com lineage enquanto sobrescreve o creative por novos vídeos/UTM. No incidente CPV, todos os anúncios API sem delivery tinham `source_ad_id=0`; C08/C10 e duplicações manuais que entregavam tinham lineage não zero. A substituta C20 criada integralmente pela rota corrigida iniciou delivery na 19ª leitura, com US$0,11/11 impressões, sem duplicação manual no Ads Manager; causa/solução confirmadas por canário live. A rota obrigatória para mídia nova é ad-level copy com `creative_parameters` e readback `source_ad_id`, nunca `act_{account}/ads` direto.
- O Ad Copies API pode rematerializar os vídeos enviados em `creative_parameters`: os video IDs do creative final podem diferir dos IDs de pre-stage e não aparecer no edge `advideos` ou `PAGE/videos`. Isso é esperado quando cada ID derivado passa GET direto com `video_status=ready`, todas as fases `complete`, e o título preserva `asset_id + checksum curto`. Não sobrescrever o media registry de pre-stage; inventário/audit guardam separadamente `meta_prestage_video_ids` e os IDs derivados efetivamente usados pelo creative. Falta de vínculo por título/checksum, vídeo não ready ou quantidade diferente de 6 bloqueia ativação.
- `execution_options=[validate_only]` não é documentado nem seguro em endpoints `/copies`. Um teste CPV recebeu `copied_ad_id` e criou três anúncios PAUSED apesar de `validate_only`; tratar qualquer copied ID como side effect real, persistir imediatamente e nunca repetir. Teste de payload para copy usa objeto técnico PAUSED autorizado ou validação documental/offline, não `validate_only`.
- Em Eggbev com `Instagram Account = Use Facebook Page`, a identidade técnica é o `page_backed_instagram_account` (PBIA) existente da própria página: obter por Page Access Token e incluir `object_story_spec.instagram_user_id` junto ao `page_id`; sem isso, o Graph v26 rejeita o anúncio com `code=1815707/subcode=2490442`. Nunca substituir por outra conta Instagram.
- Em Eggbev Graph v26, não enviar `instagram_positions=["explore"]`: o create retornou `code=100/subcode=2490589` (“IG Explore Placement Is Deprecated”). A campanha real `pg_5024 C001` foi criada com `explore_home` sem `explore`, e o readback do ad set em 2026-08-30 confirmou `ACTIVE` e exatamente essa lista; o objeto live criado supersede o validate-only histórico contraditório `2490392`. Audience Network e Advantage+ Placements continuam proibidos. Para três headlines em `asset_feed_spec` com customization por placement, cada título usa labels square e vertical próprios do novo creative, e as regras referenciam `title_label`; o direct `adcreative validate_only` aceitou esse payload com HTTP 200 e zero ID lateral. Nunca reutilizar IDs/labels internos de outro creative. A evidência de `validate_only` em edges diretos não se estende a `/copies`.
- Em `clone_page_switch` e em qualquer `clone_prestaged` com troca de Page, alterar `object_story_spec.page_id`/JSON no `creative_parameters` não altera o `promoted_object.page_id` do ad set copiado. O incidente Eggbev de 31/08/2026 confirmou dois bloqueios independentes: o AdG copiado rejeitou a troca do promoted object (`1885090`) e `/ad copies` entre Pages rejeitou PBIAs conflitantes (`2238280`). A recuperação scoped, autorizada pelo gestor, precisou criar target-AdG + creatives/ads diretos; o fresh AdG ainda exigiu remover `explore_home` após `2490392`. Até uma arquitetura determinística global representar essa rota e receber aprovação estrutural, remover `clone_page_switch` de `accounts[ACCOUNT_ID].supported_modes` na conta afetada para a prevalidation falhar antes do primeiro write; nunca publicar com Page do creative diferente da Page promovida no ad set.
- Quota de `write`, `recovery` e `readback` usa IDs de reserva distintos; uma reserva antiga de write nunca autoriza recovery imediato. Para `code=2` transitório, preservar children bem-sucedidos, aguardar capacidade efetiva, fazer readback por slot/lineage e repetir somente o anúncio comprovadamente ausente. A reserva fresca de recovery estima GETs de reconciliação + missing writes + normalização realmente necessária + readback final; se cobrir o total, concluir na mesma wave sem um segundo cooldown fixo. Se não cobrir, persistir IDs como `children_created_readback_pending` e deferir somente o readback.
- Em Eggbev `from_zero_prestaged`, um batch `creative_create` pode retornar sucesso parcial junto de `code=100/subcode=1487390`. Persistir imediatamente os IDs de `successful_children` e reconciliá-los por slot/nome antes de criar qualquer substituto. Se a versão corrente não conseguir mapear esses IDs e o recovery criar creatives finais novos, tratar os primeiros como orphans preservados para auditoria: não anexar a anúncios, não contar como segunda linhagem e nunca excluir sem autorização explícita.
- Uma retomada do mesmo bundle pode deixar no checkpoint/audit um registro vazio `IN_PROGRESS` e um registro final `COMPLETE` com o mesmo `index`. O pós-processamento deve considerar somente o final completo; correção de dados exige confirmar readback e todos os IDs, criar backup e remover exclusivamente o duplicado vazio (sem IDs e sem `stage`) nos dois JSONs. Nunca remover um registro parcial com qualquer ID. Registrar a mudança operacional em REPORT-INFRA antes de retomar `POSTPROCESS_PENDING`.
- Cooldown e pós-processamento nunca rodam como comando foreground monolítico com `sleep`. O writer cria lease persistida da conta já no início do preflight e a mantém em `DEFERRED_QUOTA`/`READBACK_DEFERRED`/`RECOVERY_PENDING` entre ticks. Intraday, Diário, Snapshot, first-delivery e guardrail reactivation chamam o mesmo reader gate e usam lock compartilhado; todos deferem silenciosamente enquanto a lease ou o `cpv-daily` estiver resumível. Lock livre entre ticks não autoriza cron concorrente. Ao concluir, liberar a lease e remover `failure`, `retry_after_epoch` e `operator_authorization` do state.
- Watchdogs de recovery precisam reconhecer os estados terminais reais do runner e do engine. Para Eggbev v3, aceitar pelo menos `phase in {COMPLETE, COMPLETED}` combinado com `engine_result.status in {COMPLETE, COMPLETE_FUTURE_ACTIVE}`. Antes de alertar “estado não retomável”, reler state/audit/checkpoint e, se terminal, fazer readback Meta e encerrar em sucesso; nunca transformar uma conclusão real em alerta falso por diferença de enum.
- Antes do auto-arm de first-delivery, validar que o watcher resolve exatamente o mesmo `account_id`, `OP_PATH` e token reference do manifest. Um watcher CPV hardcoded para outra conta deve rejeitar os IDs; nunca corrigir isso inserindo campanhas na allowlist da conta errada. Sem runtime determinístico account-scoped já aprovado, manter `POSTPROCESS_PENDING`, registrar último spend/impressões live e escalar a criação/alteração de script ou cron para o owner de arquitetura.
