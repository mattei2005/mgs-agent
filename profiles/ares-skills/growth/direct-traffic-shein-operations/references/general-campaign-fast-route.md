# SHEIN — pipeline comum dos seis gestores

## Regra ativa

### Horário e herança de referência padrão

Na duplicação SHEIN sem parâmetros extras, manter a configuração e mídia/copy reais da fonte; budget ausente em pure_clone ativa `budget_from_reference=true`. Horário ausente ativa o marcador estável `start_next_midnight=true`, resolvido uma única vez em 00:00 do próximo dia civil da conta. Não regenerar a data no pedido original nem usar timezone do VPS. NOW/data/budget/PAUSED expressos prevalecem; nenhum default autoriza novo budget adicional ou mídia nova. Conta deve estar explícita ou resolvida em contexto canônico; ambiguidade pergunta somente a conta.

### Status final padrão aprovado por Rodolfo

Em novos pedidos SHEIN, omissão de status final materializa `ACTIVE` pela política canônica `SHEIN-US-DIRECT.json#/request_defaults`. O operador não precisa repetir `Execução: ativar após validação` ou `Status final: ativa`: isso já faz parte do pedido padrão autorizado. O runner continua criando PAUSED e fecha QA semântico, mídia e pós-processamento de **todas** as campanhas solicitadas antes de ativar; não é validação por amostragem. Data futura fornecida é preservada: ACTIVE habilita para o horário aprovado, não entrega antes dele. Pedido expresso para deixar PAUSED/revisão prevalece. Esta decisão vale para novas criações SHEIN, não autoriza reativar C114 ou outras campanhas já pausadas, nem muda defaults CAR/BOT/billing/autoridade financeira.

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

Resolver todos os IDs de origem pela metadata real do gateway. Não confiar no nome exibido do usuário/canal. Em threads de gestores, `source_channel_id` é o pai canônico. Source message ID é a mensagem, nunca o ID da thread: o snowflake mede mensagem → readback. Se metadata não estiver disponível, declarar medição parcial, sem inventar timestamp. Data/hora/budget/quantidade são somente os do pedido atual, não defaults do exemplo. Status final omitido usa o ACTIVE canônico aprovado; PAUSED expresso permanece exceção e nunca ativa.

Modos suportados pelo compiler/core:

- `pure_clone`: preservar estrutura, mídia, copy, lineage, Ad setup e localização do tracking da fonte. Create ad usa `source_definition_two_phase`, com definição completa e posts novos; não converter silenciosamente em Use existing post. Preservação expressa de posts só é aceita quando compatível com o destino/tracking exigido, nunca como prioridade automática sobre a duplicação correta.
- `clone_prestaged`: copiar shell e anúncios por lineage, com assets novos pre-stageados na conta exata; 1–5 ads por campanha.
- `from_zero_prestaged`: shell do zero nos edges diretos; três ads por campanha; source campaign/adset IDs proibidos no executor; somente lineage de ad quando exigida pela conta. Uma referência interna de copy/estratégia pode ser lida sem transformar o modo em clone.

Quantidade 1–100: um manifest, números sequenciais e bundles 2+2+…+1 pelo core. Budget é por campanha. Para toda quantidade, inclusive 1, `shein_batch_activation` mantém a criação e QA semântico/mídia renderizada/pós-processamento do pedido inteiro PAUSED; somente depois da barreira chama a fase central de ativação se o pedido já autorizou ACTIVE. O status original fica no target manifest selado e o request não é reescrito. PAUSED não ativa. Esta política supersede a versão anterior limitada a lotes 2+. Falha durante a ativação retoma somente IDs/status pendentes sem recriar campanhas nem reativar nós já corretos. Não montar manifests ad hoc ou pesquisar scripts durante o pedido; materializar apenas intenção e usar o runner.

## Mídia nova

A seleção visual/semântica, liberação, sanitização, reserva e pre-stage continuam no fluxo canônico de Creative Ops antes do manifest. `asset_refs` são IDs/checksums internos resolvidos desse fluxo, não dados exigidos ao gestor. O handoff só aceita assets da língua correta, sanitizados, em READY, sem uso conhecido, reservados pelo request exato, associados à conta, processados e com título de lineage/checksum verificável. Credencial Google somente a Service Account canônica e Shared Drive MGS-AGENTS. Não consumir upload humano reservado em silêncio. Preservar original e registry de pre-stage.

Depois de readback Meta completo, o mesmo pipeline valida vídeo final por lineage, move somente o tratado de READY para TESTING com readback e registra ads/creative/post/history no inventário sob lock. Falha mantém IDs e POSTPROCESS_PENDING; repetir apenas a camada ausente com o mesmo request, sem recriar campanhas nem excluir mídia. Conte upload e tratamento no tempo total, não prometer o tempo de uma duplicação sem mídia nova.

## Prova, limites e recovery

- Fonte na mesma conta, evento fixo Add to Wishlist, Page/pixel/task vivos, URL de destino autorizada, moeda e timezone vivos.
- Tokens históricos válidos como `c01`/`c0101` são capturados literalmente; números/tracking canônicos novos não reescrevem a fonte. Nome antigo US-EN não prova idioma de mídia; novo nome usa idioma do catálogo, preservando posts/copy no pure clone. Qualidade/compatibilidade de mídia continua exigindo evidência no intake criativo.
- Budget/intenção de início explícitos; status final omitido é resolvido pelo default ACTIVE aprovado, não por suposição do agente. PAUSED expresso prevalece. SCHEDULED ACTIVE exige horário humano futuro válido. IMMEDIATE usa `start_now=true` e a fase central depois do QA; somente essa intenção permite o início técnico já passado. Guardrails, quotas e bloqueios reais permanecem.
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

Este gate está implementado na rota comum por `creative_media.py`, `shein_qa.py` e `preview_renderer.py`, release 3.6.2. Validar runtime do renderer antes do primeiro write; usar o Python dedicado registrado em `shein_media_qa.python_path`, Chromium isolado sem credenciais/perfis AdsPower e previews temporárias da Meta somente em memória. Referências flexíveis são compiladas com pacote completo, identidade Instagram e URLs novas; Meta IDs rematerializados são conciliados por labels/título/duração/ready, e a prévia precisa carregar a mídia esperada. Renderer indisponível ou vídeo sem frame/duração mantém PAUSED. Registros de mídia e proofs não guardam URLs assinadas de preview. A release 3.6.3 acrescenta os intents NOW/budget da fonte, transientes contidos e relógio/alvo E2E; a 3.6.4 preserva Ad setup e a localização original do tracking por definição completa, sem prioridade automática para prova social. Não dispensa esse gate de mídia.

Reutilizar snapshot PREPARED apenas dentro do TTL local de 120s; snapshot expirado é recolhido e a unicidade é sempre relida antes do write. Consumir o readback consolidado do core apenas quando fresco (15s), e os trees completos retornados pela ativação, sem GET redundante imediato. Cache de pastas Drive vive somente no request; cada arquivo/checksum/reserva continua sendo conferido. O registry conta+asset+checksum continua sendo a fonte para reutilizar upload confirmado, nunca o filename.

A implementação offline não comprova tempo live nem serving. No próximo pedido, medir até mídia/QA/postprocess/readback completos. Writes incertos sem ID confirmado permanecem resumíveis e não autorizam replay; usar `progress.py` e recuperação readback-first no mesmo request.

## Início imediato, budget herdado e alvo E2E

- Para `iniciar agora`, materializar `start_now=true` e não inventar um `start_time` futuro no agente. Para `mesmo budget da referência`, materializar `budget_from_reference=true` sem buscar o valor numa consulta manual separada. O runner resolve ambos na coleta account-scoped da fonte e persiste o pedido original separado de `resolved_request`. Flags com data/budget explícitos conflitantes são rejeitados. O gestor continua falando naturalmente, sem formulário técnico.
- `resolve_intent` gera o horário técnico em segundos inteiros e sela `start_intent=IMMEDIATE` nos manifests SHEIN. O buffer técnico curto não redefine a intenção comercial. Depois de passar QA, a fase central status-only aceita que esse início técnico já tenha passado, sem editar o início imutável, copiar novamente ou pedir ativação manual. Essa rota supersede a limitação futura-only anterior, exclusivamente em SHEIN. Datas humanas agendadas continuam literais e um horário agendado vencido continua bloqueado.
- Aceitar os transientes conhecidos `IN_PROCESS`/`PENDING_REVIEW` somente quando o status configurado da campanha continua PAUSED; isso não prova mídia pronta nem libera ativação. Comparações materiais, renderer e proof por IDs continuam obrigatórios. Não repetir criações ou updates já confirmados por um effective transitório.
- Para uma campanha SHEIN, Rodolfo definiu alvo máximo E2E de 144s (2min24), incluindo preparação, criação, QA/mídia e readback. Configuração: `shein_execution_sla`. Preservar o relógio original entre retomadas; quando há timestamp real da mensagem/receipt, usá-lo, caso contrário declarar a medição a partir do runner. Nunca anunciar sucesso no SLA usando somente o tempo do motor.
- O gate impede iniciar uma nova ativação depois do alvo; mantém o pedido e os IDs para revisão, sem recriação ou retirada de QA. Um write já em voo continua exigindo readback, e latência/limitação da Meta não pode ser garantida pelo agente. Marcar `e2e_target_met` com a medição real; testes offline não comprovam o alvo live.
- Repetir um request já concluído faz somente leitura dos IDs e devolve resultado histórico/estado atual, sem reativar objetos que alguém pausou depois. O próximo pedido de criação recebe identidade nova; nunca reutilizar a autorização anterior.

## Duplicação fiel de Ad setup e localização do tracking

- Antes de compilar, classificar cada criativo pela definição real: `object_story_spec` sem `object_story_id` representa Create ad; `object_story_id` representa Use existing post. O `effective_object_story_id` existe nos dois casos e não autoriza converter Create ad em post existente.
- Em duplicação de uma referência Create ad, usar `source_definition_two_phase`: copiar a linhagem do anúncio, materializar a definição completa de mídia/copy/CTA/Page/Instagram e anexar ao novo anúncio. Não escolher preservação de prova social automaticamente nem substituir a forma de edição por outro setup. Posts novos são declarados; se o usuário exigir preservar o mesmo post e atualizar seu link imutável, bloquear a incompatibilidade antes do write.
- Preservar onde a fonte guarda o tracking. Website URL com UTMs e `url_tags` vazio gera Website URL completo com os novos tokens e `url_tags=""`. Fonte com parâmetros em Tracking mantém essa localização. Não mover UTMs por conveniência do executor, nem validar apenas a combinação de parâmetros sobreposta em memória.
- Validar o link da CTA/Website URL/asset feed diretamente: campanha e grupo novos em todos os destinos pertinentes; nenhuma referência c71 permanece numa nova c114. Comparar copy, mídia, CTA e setup; renderizar a prévia sem clicar no anúncio. Source URL de Ad sources não é Website URL de Destination e não é prova do destino.
- GET pode devolver `video_data.image_url` e `image_hash` juntos: enviar apenas um, preservando o hash válido. Preservar features individuais da fonte; remover somente `standard_enhancements` descontinuado e declarar normalizações que a API não conservar. Validate-only é permitido no edge direto de adcreatives, nunca em copies.
- Em código de inspeção, manter IDs técnicos em variáveis dedicadas e validar formato numérico antes de chamar a Graph; não reutilizar nomes de loop/patch como destinos de API. Envolver falhas de transporte com saída sanitizada de tipo/código, nunca `str(exception)` ou traceback bruto: URLs de GET podem conter credenciais. Se houver exposição acidental, registrar somente metadados e escalar a Zeus; revogar/substituir credencial continua exigindo confirmação crítica de Rodolfo.
- Reposição numérica é exceção por pedido expresso, não preenchimento de buracos: `target_number` exige um `replaces_campaign_id` exato na mesma conta, readback DELETED desse ID e nova consulta de unicidade imediatamente antes do primeiro write. Novo request/novos IDs; não reciclar o state da campanha excluída. Exclusão de campanha não autoriza excluir mídia/posts/arquivos do Drive.

## Nome obrigatório e Multi-advertiser ads

- Ao aplicar naming canônico, validar também `config.json#/accounts/<conta>/campaign_policy/name_regex`: `shein_naming.enabled=true` não sincroniza automaticamente o validador. Se o dry-run rejeitar o nome gerado pelo formatter aprovado porque a conta ainda exige US-EN/ES + event_add_to_wishlist, reconciliar somente o regex da conta exata com a política canônica vigente, preservar backup/inventário, provar que nenhum outro campo mudou e repetir o dry-run antes de qualquer write. Não renomear para o padrão antigo, remover o gate ou ampliar a correção para outras contas. Registrar a correção em REPORT-INFRA.

- Mesmo em duplicar/clonar igual, preservar a configuração não significa copiar o nome da fonte. Todo modo SHEIN gera `Nº CAMPANHA - DATA - QUIZ - PRODUTO - LANCE - (TRACKING) - add_to_wishlist` pelo formatter `shein_naming.py`. Número vem primeiro; data é o início configurado no timezone da conta; produto limpo de qualificadores históricos; MAXVOL/COCAP/BIDCAP vêm do bid_strategy real. Não inserir moeda, valor do cap, US-EN/ES, LP NORMAL ou COPY Cnnn no novo padrão.
- Identificar quiz pela regra corporativa verificada do plugin MGS Direct Quiz, não por substring arbitrária: admin do plugin declara lp1=V1/sh1, lp2=V2/sh2, lp3=V3/sh3. Aplicar somente rotas ancoradas `/quiz/us/sh([123])-gNNN/` e mapear para v1/v2/v3. A página atual da rota usada no lote comprovou `data-model=lp2`; registrar evidência e bloquear formatos desconhecidos. Nenhuma alteração de quiz/plugin/WordPress é autorizada pela leitura ou pelo nome.
- Ler `contextual_multi_ads` dos criativos da fonte e preservá-lo explicitamente no payload de materialização. Esse campo representa Multi-advertiser ads, separado de degrees_of_freedom_spec/Advantage+. Missing não significa OPT_OUT. Com política de preservação ativa, estado da fonte não confirmado bloqueia antes do write.
- QA compara o enrollment real fonte × alvo em todos os anúncios, e a fase central de ativação relê o campo contra a prova. OPT_OUT na fonte exige OPT_OUT no alvo; não herdar o default da Meta. Uma screenshot de um anúncio não limita a conciliação ao mesmo anúncio: validar todo o lote pedido.
- Se a Meta rejeitar update desse campo no creative com 1815573, reconciliar o efeito antes de qualquer retry. Rematerializar somente o creative completo autorizado com contextual_multi_ads explícito e anexar aos ad IDs existentes depois de readback, preservando mídia/copy/CTA/URLs/Page/Instagram/lineage, campaign/adset/ad IDs, budget, status e início. Registrar os novos creative/post IDs, repetir renderer QA e não excluir os anteriores sem autorização.
- Pedido explícito de renomear campanhas existentes permite somente name nos IDs exatos e readback de budget/start/status/bid/URLs inalterados. Atualizar recibos/correção sem apagar o manifest inicial selado nem reconstruir a campanha.

## Calibração

Testes offline: `test_shein_general_runtime.py`, `test_shein_single_clone_route.py`, `test_ares_shein_campaigns_v3.py`. Usar fake transport somente explicitamente offline. Dry-run live não cria campanha nem valida serving. Ganho E2E real exige próximo pedido humano autorizado; aprovação desta arquitetura não autoriza canários Meta por si só.
