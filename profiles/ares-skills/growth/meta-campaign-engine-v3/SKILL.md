---
name: meta-campaign-engine-v3
description: "Executa campanhas Meta em lotes determinísticos v3."
version: 3.0.15
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
5. `pure_clone` reutiliza os creatives/mídias existentes da campanha fonte e não depende do v3 media registry. `clone_prestaged` exige três mídias `ready` por campanha antes do manifest; o próprio pedido autorizado pode fazer pre-stage/upload/readback e registrar os IDs antes de materializar. O planner divide qualquer pedido de 1–100 campanhas em bundles 2+2+…+1 por conta.
6. Um outer Graph batch de readback por bundle; zero GET intermediário.
7. Cap local inicial: soft 100, hard 120; headers vivos da Meta são persistidos por lane.
8. Canário técnico explícito nasce `PAUSED`; pedido normal de produção usa `ACTIVE` com `start_time` futuro após manifest selado e validação dos guards.
9. `prevalidated=true`, `config.enabled=true`, `write_enabled=true` e `--confirm-execute` são gates independentes.
10. V2 permanece rollback congelado; nenhum legado é apagado durante a migração inicial.
11. Em CPV `clone_prestaged`, todo `asset_ref` exige `canonical_filename` válido da taxonomia `CAR_BR_BR_VID_*_{PV|NV|PH|NH}_NNN.mp4`. O anúncio nasce como `AD NN - {canonical_stem}` e o creative como `CPV CNN ADNN {canonical_stem}`. `asset_id` permanece apenas como identidade técnica no manifest/audit; se o nome canônico faltar ou for inválido, bloquear antes de selar o manifest.
12. Em Creditoparaveiculo, o pós-processamento só conclui após auto-armar cada campanha nova no guardrail de primeiro gasto. O enrollment valida IDs, data operacional, status `ACTIVE`, gasto zero e retorna `meta_writes=0`; falha deixa o request `POSTPROCESS_PENDING`. O watcher aceita primeiro spend observado de 00:30 a 02:00 SP inclusive sem pause; fora dessa janela, pausa uma vez e agenda reativação 00:30 do dia seguinte.
13. Todo alerta operacional de erro deve identificar operação e campanhas afetadas e informar, em linguagem humana e sem paths/credenciais: etapa, causa baseada no erro real, consequência, solução proposta e autorização necessária. Mensagem genérica de “bloqueado” sem diagnóstico não é conclusão suficiente.
14. Depois de qualquer exceção `V3 BLOQUEADO`, Ares pode continuar diagnóstico e readback somente leitura, mas nenhum write corretivo na Meta ocorre até Rodolfo ou Nicolas autorizar explicitamente a solução proposta. `PARTIAL_DEFERRED_QUOTA` saudável continua sendo retomada determinística, não erro.
15. Toda conclusão de criação programada informa em USD o budget ativo da conta, o saldo restante dentro do cap operacional e a fonte: preflight Meta vivo mais budgets do request confirmados por readback.
16. Criação programada é uma fase condicional do loop, não uma obrigação diária: analisar D1/D2/D3, aplicar pausas/escalas aprovadas e só abrir nova coorte quando a leitura justificar. `creation_hold.enabled=true` bloqueia criação/clone de novos slots e não expira sozinho; Rodolfo ou Nicolas libera explicitamente.
17. Em `clone_prestaged`, cada anúncio exige `source_ad_id` não zero e nasce por `POST /{source_ad_id}/copies` com `creative_parameters`; criação direta por `act_{account}/ads` é proibida. Campaign copy, adset copy, normalização de shell, ad copies e normalização de nomes são batches sequenciais; filhos PAUSED permanecem PAUSED até readback e ativação autorizada.

## How to run

Validação e plan são read-only:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py validate --manifest <manifest>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py plan --manifest <manifest>
python3 /root/mgs-agent/scripts/ares-creditoparaveiculo-v3-daily.py --offline-smoke
python3 /root/mgs-agent/scripts/ares-creditoparaveiculo-v3-daily.py --dry-run --operational-date YYYY-MM-DD
```

O runner diário CPV tem gate de início às 17:00 São Paulo e permite retomar o mesmo request fora da janela quando o state estiver `PARTIAL_DEFERRED_QUOTA` ou em outro estágio resumível. `--dry-run` faz somente plano live/read-only; `--offline-smoke` usa transporte fake e zero rede. O wrapper v3 só pode substituir o job legado depois da revisão independente do Zeus; até então, o cron de criação permanece pausado e o v2 continua rollback isolado.

A execução real está ativa sob `development_access`. Cada pedido autorizado de campanha fornece o `--confirm-execute` operacional, mas não altera os gates estruturais. O guard inicial é **por lane**: em uma conta, o primeiro bundle daquela conta é guardado/fail-closed; em várias contas, o primeiro bundle de cada `app_key + ad_account_id` pode iniciar em paralelo pelo `ThreadPoolExecutor`. Não existe canário global único antes das outras lanes; os bundles seguintes de cada lane obedecem à própria quota.

## Verification

- manifest válido e digestado;
- dry-run mostra duas campanhas por bundle;
- `intermediate_get_calls=0`;
- lanes separadas por conta;
- média/p95 por estágio no audit;
- nenhuma credencial no manifest/audit;
- GET final confirma IDs, estrutura, budget, status e `start_time`;
- audit diário preserva ordem estável e registra `duration_ms` + contadores sanitizados para `meta_preflight`, `drive_preflight`, `reconciliation`, `asset_selection`, `prestage`, `manifest_prevalidation`, `engine`, `postprocess` e total;
- Token é resolvido cache-first pelo helper canônico; runner/cron nunca usa `force_refresh=True` por padrão;
- antes do execute, nomes exatos do manifest não colidem com campanhas live não deletadas fora do mapeamento idempotente do mesmo request;
- títulos de pre-stage incluem `asset_id + checksum curto`, e o registry confirma `account + asset + checksum + IDs` por readback;
- falhas após possível side effect ficam `READBACK_DEFERRED`/`POSTPROCESS_PENDING`, nunca `FAILED` fora do gate;
- `BatchTransportError` persiste etapa e causa Meta sanitizada (`code/subcode/user_title`) para o alerta; paths, headers sensíveis, token e trace não entram na mensagem ao operador;
- simulação de erro confirma que o state recebe `manual_reconciliation_required=true` e `operator_authorization.required=true`, impedindo retomada/write corretivo automático;
- conclusão programada inclui `account_budget_after_creation` e a mensagem Discord informa budget ativo, restante e cap em USD;
- REPORT-INFRA para qualquer mudança estrutural.

## Pitfalls

- Alterar 60→120 sem reduzir GET/validate/upload não cria escala.
- Graph batch reduz round-trips, não quota lógica.
- `IN_PROCESS` é post-processing, não falha terminal.
- Mídia crua não entra na transação: primeiro pre-stage, depois manifest.
- Advanced Access por permission, Marketing API Full Access e asset assignment são gates diferentes.
- Em `clone_prestaged`, ao substituir `asset_feed_spec.videos`, preservar em cada novo vídeo os `adlabels` do vídeo-fonte vertical/square quando `asset_customization_rules` os referencia. Remover os labels causa `code=100/subcode=2446173` mesmo com mídia pronta. O mapeamento usa dimensão/orientação real, não apenas ordem presumida.
- `rename_options` da cópia nativa de adset pode concatenar o nome-fonte com o sufixo desejado. O pós-processamento deve normalizar o adset para o nome canônico exato e validar por readback.
- Se o bundle falhar depois de criar campaign/adset shells, bloquear replay cego. Reconciliar IDs existentes, procurar filhos/orphans por escopo recente ou nomes exatos, corrigir o payload, passar `validate_only` e retomar somente a camada faltante com state/audit/readback explícitos.
- Na criação `clone_prestaged`, a ordem do pool é obrigatória: atualizar a reconciliação Drive×Meta, eliminar do conjunto candidato todo asset não aprovado, conflitante, reservado ou com identidade divergente e somente então selecionar `3 × campanhas` do Shared Drive. Conflito em um candidato faz o seletor pular para o próximo elegível; nunca bloquear o lote inteiro enquanto houver quantidade reconciliada suficiente. Bloquear apenas quando o saldo único reconciliado for menor que o necessário.
- Nunca reutilizar o state de um request já concluído como ciclo do dia seguinte. `completed_operational_date_sp` anterior fecha a execução antiga; o novo ciclo começa com request e conciliação novos.
- Nunca confundir o horário de 17:00 com autorização automática para criar. O schedule apenas pode iniciar quando o lifecycle gate estiver liberado; em hold, Diário, Intraday, D1-D3, pausa, escala e first-delivery continuam ativos sem novos campaigns.
- `configured_status=ACTIVE`, `effective_status=ACTIVE`, três anúncios/creatives `ACTIVE` e `issues_info=null` não provam entrada real no leilão. Se uma cópia nativa feita no Ads Manager a partir da própria campanha API começar a imprimir/gastar enquanto o objeto-fonte permanece sem impressões, classificar como divergência de serving/release da rota, congelar novas `clone_prestaged` e comparar por Graph Batch campanha, adset, ads, creatives e Insights. Separar os dois eixos que a cópia pode alterar: `start_time` imediato versus futuro e regeneração de ad/creative/story IDs. Não culpar budget, público, revisão ou mercado sem diff vivo; qualquer canário corretivo por `deep_copy=true`, ativação imediata ou reconstrução de creative exige autorização operacional e readback de impressão/gasto, não apenas status.
- Para Video Ads, nunca pre-stagear mídia nova em `/{PAGE_ID}/videos` nem tratar `video_status=ready` da Página como associação à conta. O guia oficial exige que o `video_id` esteja associado ao ad account e aponta `act_{AD_ACCOUNT_ID}/advideos`. Upload usa o advertiser User Access Token; antes de selar o manifest, o ID retornado precisa aparecer no edge `advideos` da conta, com processamento pronto, e o registry registra `upload_edge=ad_account_advideos` + `association_verified=true`. Ausência dessa associação bloqueia creative/campaign write. Esse é um gate técnico necessário, mas não prova serving: no incidente CPV, a C20 corrigida com 6/6 vídeos associados, campanha/adset/ads/creatives ACTIVE e UTMs válidas permaneceu com zero impressão/gasto por pelo menos 45 minutos. Portanto, nunca declarar a associação como causa raiz suficiente; após esse gate, investigar reutilização de `creative_id`/post social-proof versus creative novo e divergência de serving entre API e Ads Manager. Não excluir os Page videos antigos sem reconciliação de dependências e autorização.
- A opção do Ads Manager para mostrar reações, comentários e compartilhamentos existentes corresponde ao objetivo operacional de preservar post/social proof. Para clonar campanha vencedora sem trocar mídia, preferir `pure_clone` ou criar os novos anúncios referenciando exatamente os `creative_id`/post IDs aprovados; validar por readback se a Meta reutilizou ou rematerializou IDs. `clone_prestaged` com criativos inéditos do Drive necessariamente cria creatives/posts novos e não preserva social proof; seu gate é mídia em `advideos` da conta, identidade Drive↔Meta, UTM e serving real.
- Em `clone_prestaged`, nunca descartar `source_ad_id` do template. O campo é aceito pela API na criação do anúncio e o endpoint oficial `/{ad_id}/copies` permite `adset_id` + `creative_parameters`, criando uma cópia com lineage enquanto sobrescreve o creative por novos vídeos/UTM. No incidente CPV, todos os anúncios API sem delivery tinham `source_ad_id=0`; C08/C10 e duplicações manuais que entregavam tinham lineage não zero. A rota preferida para mídia nova passa a ser ad-level copy com `creative_parameters` e readback `source_ad_id`, não `act_{account}/ads` direto.
- `execution_options=[validate_only]` não é documentado nem seguro em endpoints `/copies`. Um teste CPV recebeu `copied_ad_id` e criou três anúncios PAUSED apesar de `validate_only`; tratar qualquer copied ID como side effect real, persistir imediatamente e nunca repetir. Teste de payload para copy usa objeto técnico PAUSED autorizado ou validação documental/offline, não `validate_only`.
