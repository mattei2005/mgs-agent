# SHEIN — pipeline comum dos seis gestores

## Regra ativa

Pedidos equivalentes de Rodolfo e dos gestores autorizados seguem o mesmo intake, compiler account-scoped, Engine v3, guards, recovery e readback. Não existe fluxo rápido exclusivo do CEO. Política canônica: `data/ares/meta-ads/policies/SHEIN-US-DIRECT-request-parity.json`. Gestores somente nas próprias contas e no próprio canal pai; Rodolfo conserva escopo global. Nunca mudar credencial, billing, app permissions, pixel/CAPI estrutural ou automação recorrente por consequência dessa regra.

## Intake natural e descoberta de Páginas

- Os seis canais `shein-g001`…`shein-g006` são canais dos gestores SHEIN. O operador informa a conta pelo nome completo como Rodolfo fez; o nome já identifica site/país/vertical/idioma/gestor. Resolver o ID por lookup exato, sem exigir que o operador repita o site ou complete um formulário. Domínio/URL de destino ainda deve ser reconciliado com a fonte canônica e passar pelo gate, nunca inventado acrescentando `.com` ao rótulo.
- Manter dois catálogos compactos e independentes somente quando reduzirem descoberta: contas (nome → ID → gestor/canal) e Páginas (nome → ID + evidência de acesso). Não carregar inventários completos no prompt nem consultar a BM inteira a cada pedido; filtrar apenas os registros necessários. Não transformar observações de uso em regras de propriedade ou associação exclusiva.
- Não presumir relação exclusiva Page ↔ site, conta ou gestor: uma mesma Page pode ser usada em contas de sites diferentes quando o pedido/contrato e as permissões reais permitirem. Em duplicação/clone, a campanha exata solicitada determina a Page a preservar. Uma campanha amostrada não fixa default eterno. Em criação do zero, resolver a Page escolhida/aprovada para o pedido e validar o acesso; ausência de campanha não prova ausência de Page ou indisponibilidade da conta.
- Os cadastros de contas e Páginas vêm da BM e da API da Meta. AdsPower não participa de intake, criação, clone, duplicação, validação ou ativação de campanhas SHEIN, nem é pré-requisito para manter esses catálogos. Não introduzir navegador de perfis, cookies ou token alternativo nesse pipeline. Guardar somente nomes/IDs e evidências necessárias, com lookup filtrado e sem carregar listas completas no prompt.
- Ausência da Page no token corporativo ou erro em leitura é evidência de limitação daquela consulta, não prova isolada de falha de criação/clone. Distinguir Page observada na interface, acesso de leitura, tarefa de anúncio e serving. Não anunciar bloqueio geral ou pedir mudança de delegação antes de diagnóstico suficiente.

## Fontes e resolução rápida

- Nome exato/ID → gestor/canal: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json`.
- Parâmetros e prontidão de cada conta: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json`.
- Registro dos modos e guardrails: `data/ares/meta-ads/engine-v3/config.json`.
- Catálogo independente de Páginas BM: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-pages.json`; `page-lookup --page <nome-exato-ou-ID>` filtra apenas o registro necessário. Cobertura da API é declarada no snapshot; IDs conhecidos sem nome/acesso não são inventados nem apresentados como inventário administrativo completo.
- Autoridade: `authorized-users.json`, `permissions-matrix.md` e `SHEIN-US-DIRECT.json#/manager_channels`.

O catálogo não prova que uma Page está delegada nem que uma conta vazia já possui parâmetros de criação aprovados. Não confundir `LIVE_SOURCE_READY` (modelo Meta/Page/pixel acessível) com mídia nova disponível ou serving validado. `PAGE_ACCESS_PENDING` e `NEEDS_ACCOUNT_REFERENCE` são pré-requisitos materiais aplicáveis igualmente a Rodolfo e ao gestor, não versões diferentes de procedimento.

## Comando normal único

```text
python3 /root/mgs-agent/scripts/ares-shein-campaigns.py campaign --input <request.json> --confirm-execute
```

O comando faz preflight vivo, seleção da fonte na conta exata, compiler, prevalidation/plan, conciliação de numeração antes do write, delegação ao Engine central e readback. Sem confirmação ou com `--dry-run`, não entra no writer. `single-clone` é alias de compatibilidade, não rota privilegiada; `prepare-live/materialize` G005 de três modos fica apenas legado/rollback, não intake rotineiro.

JSON interno de intenção (não formulário obrigatório ao gestor):

```json
{
  "request_id": "shein-MESSAGE_ID",
  "account": "NOME EXATO OU ID DO CATALOGO",
  "mode": "pure_clone",
  "source_number": 110,
  "quantity": 1,
  "budget_usd": "30",
  "start_time": "2026-10-08T00:00:00-04:00",
  "status": "PAUSED",
  "authorized_by": "DISCORD_SENDER_ID",
  "source_channel_id": "CANONICAL_PARENT_CHANNEL_ID",
  "source_thread_id": "ACTUAL_THREAD_OR_CHANNEL_ID",
  "source_message_id": "ACTUAL_GATEWAY_MESSAGE_ID"
}
```

Resolver todos os IDs de origem pela metadata real do gateway. Não confiar no nome exibido do usuário/canal. Em threads de gestores, `source_channel_id` é o pai canônico. Source message ID é a mensagem, nunca o ID da thread: o snowflake mede mensagem → readback. Se metadata não estiver disponível, declarar medição parcial, sem inventar timestamp. Data/hora/budget/quantidade/status são somente os do pedido atual, não defaults do exemplo.

Modos suportados pelo compiler/core:

- `pure_clone`: preservar mídia/copy/lineage; tracking e números novos. Referência tradicional usa `existing_post_two_phase` e preserva o post. Referência com `asset_feed_spec` usa `full_media_two_phase`, preserva o pacote e as regras, mas materializa posts novos; declarar `posts_preserved=false`. Se o pedido exigir expressamente os mesmos posts/prova social, materializar `preserve_posts=true` e bloquear a incompatibilidade antes do write, sem substituir silenciosamente. Page token direto somente para contadores de posts realmente preservados.
- `clone_prestaged`: copiar shell e anúncios por lineage, com assets novos pre-stageados na conta exata; 1–5 ads por campanha.
- `from_zero_prestaged`: shell do zero nos edges diretos; três ads por campanha; source campaign/adset IDs proibidos no executor; somente lineage de ad quando exigida pela conta. Uma referência interna de copy/estratégia pode ser lida sem transformar o modo em clone.

Quantidade 1–100: um manifest, números sequenciais e bundles 2+2+…+1 pelo core. Budget é por campanha. Para toda quantidade, inclusive 1, `shein_batch_activation` mantém a criação e QA semântico/mídia renderizada/pós-processamento do pedido inteiro PAUSED; somente depois da barreira chama a fase central de ativação se o pedido já autorizou ACTIVE. O status original fica no target manifest selado e o request não é reescrito. PAUSED não ativa. Esta política supersede a versão anterior limitada a lotes 2+. Falha durante a ativação retoma somente IDs/status pendentes sem recriar campanhas nem reativar nós já corretos. Não montar manifests ad hoc ou pesquisar scripts durante o pedido; materializar apenas intenção e usar o runner.

## Mídia nova

A seleção visual/semântica, liberação, sanitização, reserva e pre-stage continuam no fluxo canônico de Creative Ops antes do manifest. `asset_refs` são IDs/checksums internos resolvidos desse fluxo, não dados exigidos ao gestor. O handoff só aceita assets da língua correta, sanitizados, em READY, sem uso conhecido, reservados pelo request exato, associados à conta, processados e com título de lineage/checksum verificável. Credencial Google somente a Service Account canônica e Shared Drive MGS-AGENTS. Não consumir upload humano reservado em silêncio. Preservar original e registry de pre-stage.

Depois de readback Meta completo, o mesmo pipeline valida vídeo final por lineage, move somente o tratado de READY para TESTING com readback e registra ads/creative/post/history no inventário sob lock. Falha mantém IDs e POSTPROCESS_PENDING; repetir apenas a camada ausente com o mesmo request, sem recriar campanhas nem excluir mídia. Conte upload e tratamento no tempo total, não prometer o tempo de uma duplicação sem mídia nova.

## Prova, limites e recovery

- Fonte na mesma conta, evento fixo Add to Wishlist, Page/pixel/task vivos, URL de destino autorizada, moeda e timezone vivos.
- Tokens históricos válidos como `c01`/`c0101` são capturados literalmente; números/tracking canônicos novos não reescrevem a fonte. Nome antigo US-EN não prova idioma de mídia; novo nome usa idioma do catálogo, preservando posts/copy no pure clone. Qualidade/compatibilidade de mídia continua exigindo evidência no intake criativo.
- Budget/status/intenção de início explícitos; sem ativação presumida. SCHEDULED ACTIVE exige horário humano futuro válido. IMMEDIATE usa `start_now=true` e a fase central depois do QA; somente essa intenção permite o início técnico já passado. Guardrails, quotas e bloqueios reais permanecem.
- Mesmo sender/account/channel gera os mesmos parâmetros que Rodolfo para o pedido equivalente; cross-manager/channel é recusado antes de credencial ou API write.
- State persistido antes do Engine, per-account lock/context, IDs/checkpoint do core, retomada readback-first. Nenhuma credencial ou Page token persistida/impressa.
- Flags age/gender normalizados pela Meta são ressalva, não cópia 100% idêntica; não repetir writes já comprovadamente ineficazes. Sem-base/contadores ausentes não viram zero.
- Somente resumo final curto; interromper com mensagem apenas por decisão necessária, bloqueio/falha real. `tool_progress: all` permanece.

## Criativo flexível — descoberta do destino

Quando `object_story_spec` expuser somente `page_id`, consultar também `asset_feed_spec`. A URL pode estar em `asset_feed_spec.link_urls[].website_url`, não em `video_data.call_to_action` ou `link_data.link`. Validar o conjunto de destinos efetivos e as regras de customization antes de compilar; não chamar ausência de URL nesse primeiro formato de domínio errado nem inventar uma CTA. Guardar a resposta original e a linhagem da normalização usada no compiler. Em pure clone, reaproveitar posts comprovados não autoriza afirmar igualdade de todas as configurações flexíveis/placement somente por post ID; comparar as camadas relevantes e declarar limitações. Falha transitória em um child de ad copy exige readback das campanhas/conjuntos/ads/creatives já persistidos e retomada do mesmo manifest exclusivamente para a camada faltante.

## Gate de mídia para referências flexíveis

- Classificar pelo payload completo: `asset_feed_spec` com múltiplos vídeos e `asset_customization_rules` por placement exige preservação do pacote e das regras. Não chamar todo `AUTOMATIC_FORMAT` de Dynamic Creative; conferir também `is_dynamic_creative` e a estrutura viva.
- Não tratar o `effective_object_story_id` de uma referência flexível como representação suficiente do criativo. Um post efetivo pode conter somente link/texto, enquanto os vídeos existem exclusivamente no `asset_feed_spec`. A rota `existing_post_two_phase` pode aceitar o write, gerar thumbnail e até receber impressões sem carregar a mídia. Post ID igual, thumbnail presente, preview endpoint HTTP 200 e status ACTIVE não fecham QA.
- Comparar fonte × alvo: pacote de mídia, labels/regras, copy/CTA, destino/tracking e identidade Instagram. Renderizar a prévia e confirmar vídeo carregado (`readyState`, duração e dimensões) ou imagem real, distinguindo-a do ícone da Page. Bloquear ativação se a referência tem mídia e a prévia alvo mostra somente texto/link.
- Se o anúncio errado já estiver entregando, pausar reversivelmente a campanha exata durante o reparo autorizado; preservar budget, schedule, campaign/adset/ad IDs e `source_ad_id`. Validar o payload no edge direto de adcreatives, nunca `/copies` com `validate_only`; persistir cada creative criado e fazer readback antes de anexar somente a camada faltante. Retomar o status original somente após QA dos dois anúncios. Não excluir creatives órfãos sem autorização.
- Ao rematerializar o pacote, consultar `instagram_user_id` do creative fonte e preservar a mesma identidade explicitamente; ausência no `object_story_spec` não prova que não há identidade Instagram. Não criar/atribuir outra conta. Um anúncio aceitar identidade implícita não prova que o outro aceitará.
- A Meta pode rematerializar IDs e reordenar vídeos. Reconciliar por labels preservados, título, duração, status ready e evidência visual; não exigir igualdade dos IDs nem aceitar apenas quantidade. No GET de vídeo usar `id,title,length,status,picture`; `width`/`height` não são fields válidos desse objeto. Obter dimensões via mídia/preview real.
- Restaurar o pacote completo pode gerar posts novos. Declarar essa mudança e nunca afirmar prova social preservada depois dela; preservar o post efetivo não autoriza sacrificar a mídia. Se houver requisito expresso de manter o post incompatível, escalar a decisão em vez de substituir silenciosamente. Insights anteriores ao reparo não provam entrega do criativo corrigido; separar prévia validada, revisão e serving pós-reparo.

Este gate está implementado na rota comum por `creative_media.py`, `shein_qa.py` e `preview_renderer.py`, release 3.6.2. Validar runtime do renderer antes do primeiro write; usar o Python dedicado registrado em `shein_media_qa.python_path`, Chromium isolado sem credenciais/perfis AdsPower e previews temporárias da Meta somente em memória. Referências flexíveis são compiladas com pacote completo, identidade Instagram e URLs novas; Meta IDs rematerializados são conciliados por labels/título/duração/ready, e a prévia precisa carregar a mídia esperada. Renderer indisponível ou vídeo sem frame/duração mantém PAUSED. Registros de mídia e proofs não guardam URLs assinadas de preview. A release 3.6.3 acrescenta os intents NOW/budget da fonte, transientes contidos e relógio/alvo E2E; não dispensa esse gate de mídia.

Reutilizar snapshot PREPARED apenas dentro do TTL local de 120s; snapshot expirado é recolhido e a unicidade é sempre relida antes do write. Consumir o readback consolidado do core apenas quando fresco (15s), e os trees completos retornados pela ativação, sem GET redundante imediato. Cache de pastas Drive vive somente no request; cada arquivo/checksum/reserva continua sendo conferido. O registry conta+asset+checksum continua sendo a fonte para reutilizar upload confirmado, nunca o filename.

A implementação offline não comprova tempo live nem serving. No próximo pedido, medir até mídia/QA/postprocess/readback completos. Writes incertos sem ID confirmado permanecem resumíveis e não autorizam replay; usar `progress.py` e recuperação readback-first no mesmo request.

## Início imediato, budget herdado e alvo E2E

- Para `iniciar agora`, materializar `start_now=true` e não inventar um `start_time` futuro no agente. Para `mesmo budget da referência`, materializar `budget_from_reference=true` sem buscar o valor numa consulta manual separada. O runner resolve ambos na coleta account-scoped da fonte e persiste o pedido original separado de `resolved_request`. Flags com data/budget explícitos conflitantes são rejeitados. O gestor continua falando naturalmente, sem formulário técnico.
- `resolve_intent` gera o horário técnico em segundos inteiros e sela `start_intent=IMMEDIATE` nos manifests SHEIN. O buffer técnico curto não redefine a intenção comercial. Depois de passar QA, a fase central status-only aceita que esse início técnico já tenha passado, sem editar o início imutável, copiar novamente ou pedir ativação manual. Essa rota supersede a limitação futura-only anterior, exclusivamente em SHEIN. Datas humanas agendadas continuam literais e um horário agendado vencido continua bloqueado.
- Aceitar os transientes conhecidos `IN_PROCESS`/`PENDING_REVIEW` somente quando o status configurado da campanha continua PAUSED; isso não prova mídia pronta nem libera ativação. Comparações materiais, renderer e proof por IDs continuam obrigatórios. Não repetir criações ou updates já confirmados por um effective transitório.
- Para uma campanha SHEIN, Rodolfo definiu alvo máximo E2E de 144s (2min24), incluindo preparação, criação, QA/mídia e readback. Configuração: `shein_execution_sla`. Preservar o relógio original entre retomadas; quando há timestamp real da mensagem/receipt, usá-lo, caso contrário declarar a medição a partir do runner. Nunca anunciar sucesso no SLA usando somente o tempo do motor.
- O gate impede iniciar uma nova ativação depois do alvo; mantém o pedido e os IDs para revisão, sem recriação ou retirada de QA. Um write já em voo continua exigindo readback, e latência/limitação da Meta não pode ser garantida pelo agente. Marcar `e2e_target_met` com a medição real; testes offline não comprovam o alvo live.
- Repetir um request já concluído faz somente leitura dos IDs e devolve resultado histórico/estado atual, sem reativar objetos que alguém pausou depois. O próximo pedido de criação recebe identidade nova; nunca reutilizar a autorização anterior.

## Calibração

Testes offline: `test_shein_general_runtime.py`, `test_shein_single_clone_route.py`, `test_ares_shein_campaigns_v3.py`. Usar fake transport somente explicitamente offline. Dry-run live não cria campanha nem valida serving. Ganho E2E real exige próximo pedido humano autorizado; aprovação desta arquitetura não autoriza canários Meta por si só.
