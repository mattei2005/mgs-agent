# Auditoria de alta escala — Ares Meta Campaign Engine

## Veredito executivo

Rodolfo está correto: o problema dominante não é apenas rate limit. A rota atual do Ares ainda é uma automação de canário/engenharia, não um executor industrial de campanhas. O `development_access` amplia o problema, mas os maiores atrasos observados vieram de trabalho feito dentro da conversa, duas falhas que exigiram cleanup, preparação/upload de mídia dentro da transação e execução totalmente sequencial.

A correção sobre “v20” também está registrada: `v20` era a maturidade/versão de otimização do executor externo, não a versão da Graph API. As novas capturas mostram que o amigo já chama o executor atual de **v23**. Não usar Graph v20 como hipótese de desempenho.

## Evidência direta do executor externo

As cinco capturas recebidas depois da auditoria confirmam os princípios do desenho vNext:

1. O executor é um **programa padronizado**, separado do agente; não é recriado por sessão ou por tópico.
2. Todos os tópicos usam o mesmo executor. Antes da padronização, cada sessão tentava criar um executor novo e o comportamento saía do padrão.
3. Há componentes separados para proteção de API e validação de fluxo.
4. O processo operacional informado é: pegar a campanha de referência → montar tudo → passar por auditoria → mandar para o executor → subir PAUSED → fazer GET final.
5. Quando há mídia nova, ela é enviada primeiro para a library do Facebook; a campanha só é montada quando todas as mídias já terminaram de subir.
6. A rota via Drive adiciona cerca de cinco minutos por causa do upload da mídia, segundo o operador externo.
7. O executor é melhorado fora da execução: executar → auditar duração/problema → sugerir melhoria → aplicar → próximo problema.
8. O operador relata já ter enviado 100 campanhas em uma operação; o primeiro bloqueio acima de 99 foi mapeado e depois tratado.
9. O executor atual citado nas capturas está em v23, resultado de mutações incrementais, e não tem relação com versão de Graph API.

Isso confirma que o maior diferencial não é um prompt mais forte: é **produto de software centralizado, versionado e reutilizado**, com mídia pre-stageada e melhoria pós-execução.

### Evidência adicional: “subir de 60 para 120”

A nova captura prova que o operador pediu ao agente para elevar algum limite de 60 para 120 e que o executor continuou funcionando. Ela **não prova** que o agente alterou a quota do servidor da Meta: o próprio operador diz que não sabe como foi feito.

A captura do Ares mostra `47/60` e `89/60` como **score projetado pelo guard local**. No código MGS, 60 também está hardcoded em `DEVELOPMENT_ACCESS_SCORE_MAX`. Portanto, mudar 60→120 no cliente apenas relaxa o bloqueio local; não aumenta a quota server-side documentada pela Meta.[8]

As explicações compatíveis com a evidência são:

- o executor externo alterou seu próprio safety cap/batch cap;
- o app real não estava no tier development, então 120 ainda cabia no servidor;
- o “120” era capacidade agregada entre lanes/contas, não score de uma conta;
- pure clone consumia poucos pontos e nunca encontrou o limite real.

Para o Ares vNext, não usar 60 nem 120 como constante operacional cega. Resolver capacidade por `app_id + ad_account_id`, usar os headers vivos e manter o cap local como proteção conservadora. Aumentar o número só pode ocorrer após um canário provar que o servidor aceitou a carga sem `17/2446079`.

## Cobertura da investigação

- Thread de autorização/execução `1540137110789562408`: 15/15 mensagens; 12 anexos de token/permissões inventariados, não necessários para medir throughput.
- Thread operacional `1539826050765299872`: 91/91 mensagens; 2 anexos; screenshot de erro relevante já inspecionada.
- Runtime Ares inventariado: 46 scripts de profile, 76 scripts `ares-*` no repositório, 152 arquivos em skills Growth, 3 testes no profile e 12 testes `test_ares*` no repositório.
- Subsistema CPV: 26 scripts/artefatos de runtime, 19 resíduos `__pycache__`, 10 arquivos no fechamento ativo e 16 legados/completados/one-shot.
- Código ativo de criação: 1.740 linhas, 69 funções; `execute()` sozinho tem 491 linhas, 40 `if`, 9 loops e 6 blocos `try`.

## Benchmark correto

O benchmark externo foi 40 clones, em três contas, em 15 minutos, com lanes paralelas.

```text
Métrica                                             Resultado
--------------------------------------------------  ----------------
Throughput global externo                           22,5 s/clone
Clones médios por conta                             13,33
Tempo equivalente por clone em cada lane de conta  67,5 s
Ares C12 — caminho bem-sucedido                     115,6 s
Ares C13 — caminho bem-sucedido                     123,2 s
Média Ares sem falhas                               119,4 s
Diferença Ares vs lane externa                      1,77× mais lento
Capacidade Ares projetada com três lanes/15 min     22,6 campanhas
```

O tempo percebido de aproximadamente 40 minutos veio da sessão completa. Da confirmação de Rodolfo até o fechamento foram 30,8 minutos: duas tentativas falharam, houve cleanup, correções ao vivo e a separação C12/C13 por janela. O caminho bem-sucedido isolado já está próximo de dois minutos por campanha; o gap real contra o benchmark por lane é cerca de 52 segundos, não vinte vezes.

## Por que aparece tanto “Searching”

Na thread operacional importada houve, nos progressos publicados pelo Ares:

```text
Searching   41
Reading     56
Editing     42
Writing     16
Terminal    64
Scheduling  16
```

Isso não é apenas visual. Ares estava simultaneamente descobrindo a rota, lendo skills/referências, alterando código, testando, criando campanhas e corrigindo produção. Um executor de alta escala não pode fazer desenvolvimento de software dentro da mesma transação que cria campanhas.

A rota operacional deve ser: interpretar pedido → gerar manifest → executar um único comando determinístico. `search_files`, edição de script, testes e criação de cron ficam fora do hot path.

## Estado dos arquivos do Ares

### Integridade mecânica

- 16 scripts Python CPV compilados: zero falhas.
- 10 wrappers shell: zero falhas de `bash -n`.
- 13 scripts referenciados por cron: todos existem.
- Referências absolutas/skill verificadas: zero quebradas no conjunto canônico auditado.
- 43 testes atuais passaram.
- Nenhum literal com padrão de User Access Token Meta foi encontrado nos scripts CPV.

Portanto, o subsistema não está “quebrado” mecanicamente. O problema é organização, duplicação, semântica e arquitetura de execução.

### Problemas estruturais encontrados

1. **Monólito:** o writer tem 1.740 linhas/69 funções e mistura planner, Drive, ffmpeg, upload, copy, creative, ad, quota, Discord, inventário, cleanup e retomada.
2. **Resíduo operacional:** 16 scripts legados/completados e 19 `pycache` CPV permanecem ao lado da rota ativa, ampliando busca e risco de escolher executor antigo.
3. **Skills sobrepostas:** `direct-traffic-cbo-operations`, `direct-traffic-vehicle-finance-operations`, `paid-acquisition-operations`, Meta Intraday e Meta clone possuem regras que se sobrepõem. O pedido CPV deveria resolver diretamente para uma rota, não carregar várias famílias.
4. **Config monolítica:** a operação CPV tem cerca de 75 KB/mais de 1.700 linhas e mistura contrato ativo, decisões, incidentes e histórico. O executor precisa de um contrato pequeno e materializado.
5. **Throttle global:** `ares-meta-common.py` usa um único state/lock e um único `last_request_monotonic` para todo Ares. Isso serializa chamadas de contas diferentes, embora a Meta aplique o limite de mutação por combinação app+ad account.[8]
6. **Execução sequencial:** downloads, crops, seis uploads, três creatives, três `validate_only` e três ads são feitos um após o outro.
7. **Mídia no hot path:** para cada campanha, três originais são baixados e três quadrados são gerados. Na execução bem-sucedida, somente essa fase local mediu 23,6–24,9 segundos; depois ainda vêm seis uploads e processamento.
8. **Ordem ainda subótima:** o código prepara e envia mídias antes de clonar campaign/adset, embora a rota comunicada diga “clone primeiro”.
9. **Esperas cegas:** há `sleep(5)` após a shell e outro `sleep(5)` antes do readback. A Meta documenta `IN_PROCESS` como post-processing normal e permite atualizar objeto/filhos nessa fase; não é necessário esperar cegamente.[6]
10. **Validação repetitiva:** três `validate_only` por campanha continuam no hot path. Depois que o payload versionado passa no canário, a validação deve ser por hash/schema e uma amostra, não por todo ad em todo lote.
11. **Async não ativo:** existem funções de deep copy assíncrono no writer, mas nenhuma chamada de produção as usa.
12. **Score subcontado:** `CLONE_WRITE_CALLS_PER_CAMPAIGN=12`, porém a rota atual executa 13 mutations lógicas: campaign copy+update, adset copy+update, três creatives, três validates e três ads. O budget projetado fica três pontos abaixo do real.
13. **Regras semânticas conflitantes:** SOUL/mapa exigem reconciliação imediata antes do write; v2 exige manifest separado. A skill genérica ainda descreve campanhas PAUSED + ativação posterior, enquanto a operação v1.0.43 passou a preferir ACTIVE com `start_time` futuro. A skill de Vehicle Finance ainda registra janela de criação 18:00, contra 17:00 na operação atual.
14. **Correção durante produção:** duas tentativas falharam por falso positivo de `standard_enhancements_catalog` e HTTP 500 no `validate_only`. Esses casos deveriam ter sido eliminados no canário de versão antes da autorização real.

## Comparação de workloads

“Clonar campanha” pode significar trabalhos muito diferentes:

```text
Modo                       Trabalho real
-------------------------  --------------------------------------------------
Clone fiel                  Copiar campaign/adsets/ads/creatives existentes
Clone + mídia pre-stageada  Copy de estrutura + creatives usando video_id pronto
Clone + mídia crua          Download, crop, upload, processamento, creative e ad
```

O executor externo é desconhecido. Se ele fez clone fiel reutilizando mídias/creatives, o benchmark não é equivalente ao CPV, que trocou seis criativos e enviou doze variações técnicas. A Meta permite criar anúncio usando um `video_id` já associado à conta; por isso a preparação da mídia deve ocorrer antes do pedido da campanha.[5]

## Rotas oficiais de alta escala

- Graph Batch processa operações independentes em paralelo e dependências sequencialmente.[2]
- Batch normal aceita até 50 operações, mas cada child continua contando na quota.[2]
- A documentação de Marketing API recomenda no máximo 10 ads por batch.[1]
- Async Batch permite dependências, JSONPath e até 1.000 requests em uma chamada assíncrona.[1]
- Campaign deep copy suporta até 3 child ads síncronos e 51 assíncronos, com `start_time`, `status_option` e read-after-write.[3]
- Ad Set Copies documenta explicitamente async batch para grande volume, até 50 copies por HTTP request, e aceita `deep_copy`, `start_time` e `status_option`.[4]
- `IN_PROCESS` é fase normal do post-processing e não impede updates do objeto ou filhos.[6]
- Adset aceita `start_time` e criação em `ACTIVE` ou `PAUSED`.[7]
- O SDK oficial já expõe `Campaign.create_copy()` e `AdAccount.create_async_batch_request()`; não é necessário inventar outra camada de HTTP para cada operação.[9][10]

## Arquitetura recomendada — Ares Campaign Engine vNext

### 1. Dispatcher sem searching

Ares transforma o pedido em um manifest curto e chama somente:

```text
ares-campaign execute --operation CPV-G006 --manifest <id>
```

Nenhuma busca, skill adicional, patch, criação de teste ou cron durante a execução. Se o manifest não puder ser construído, falha antes de reservar assets.

### 2. Contrato ativo pequeno

Separar:

- `operation.json`: somente conta, source, timezone, budget, naming, UTM, Page/pixel, modo e gates;
- `state.json`: IDs, idempotência, quota e progresso;
- `history/audit`: incidentes e versões antigas;
- `asset registry`: checksum → vertical video_id + square video_id + processing status.

O hot path não lê um JSON de 75 KB nem várias skills.

### 3. Pre-staging contínuo de mídia

Quando um asset entra em `01_READY`:

1. baixar uma vez;
2. gerar derivados uma vez;
3. sanitizar;
4. subir à Meta antes de existir pedido de campanha;
5. persistir IDs por checksum/conta/Page;
6. mover para `META_READY` lógico.

A criação de campanha passa a receber somente IDs prontos. Isso remove do caminho crítico os 24–25 segundos medidos de download/crop e os seis uploads/processamento por campanha.

### 4. Lanes independentes por conta

- Um worker/lock/state por `app_id + ad_account_id`.
- Três contas = três lanes concorrentes.
- Dentro da conta, serializar apenas mutations que realmente dependem umas das outras.
- Manter app-level guard separado, sem um lock global bloqueando contas independentes.

A Meta documenta QPS por combinação app+ad account, portanto o lock atual global é mais restritivo do que a plataforma exige.[8]

### 5. Três modos de execução

#### Pure clone

- Async batch de campaign/adset copies.
- `deep_copy=true` quando source clean.
- Reusar creatives/mídias.
- Melhor modo para benchmark 40/15.

#### Clone + novos IDs já pre-stageados

- Shallow copy de campaign/adset.
- Uma Graph batch contendo três creative creates e três ads dependentes por JSONPath.
- Sem `validate_only` por ad em produção; payload hash já aprovado no canário.

#### Clone + mídia não preparada

- Não criar campanha imediatamente.
- Enfileirar staging e executar somente quando todos os IDs estiverem `ready`.
- Nunca misturar upload/processamento com a transação da campanha.

### 6. Agendamento nativo

Nomear pela data de entrega; criar adset com `start_time` futuro e status `ACTIVE`; depois de readback exato, deixar campaign `ACTIVE`. A Meta inicia na hora prevista, eliminando o job posterior de ativação.[3][4][7]

Para C12/C13 atuais, o fallback one-shot continua necessário porque os adsets já haviam iniciado e a Meta recusou editar o horário. Isso é exceção histórica, não arquitetura futura.

### 7. Polling orientado a estado

- Aceitar `IN_PROCESS` como não terminal.
- Poll com jitter/backoff e limite, sem sleep fixo.
- Falhar somente em `WITH_ISSUES`, erro terminal ou timeout.
- Readback consolidado por IDs conhecidos.

### 8. Idempotência e observabilidade

Cada order recebe `request_id` e cada campaign `idempotency_key`.

Registrar timestamps por fase:

```text
plan → asset_ready → copy_submit → copy_ready → creatives → ads → readback
```

Sem isso, não é possível otimizar por evidência. O audit atual mostra início/fim, mas não decompõe os 119 segundos bem-sucedidos.

## Meta de desempenho

```text
Métrica                                  Meta vNext
---------------------------------------  ------------------------------
Searching/editing no hot path            0
Falhas por regra já conhecida             0
Pure clone por lane                       <= 45–70 s/campanha
Clone com mídia pre-stageada por lane     <= 60–75 s/campanha
3 contas em paralelo                      lanes independentes
40 pure clones / 3 contas                 <= 15 min após Full/Standard
Ativação posterior                        0 jobs na rota normal
Reconciliação global por criação           0
```

Os tempos vNext são metas/projeções, não medições concluídas. O primeiro piloto deve instrumentar todas as fases e comparar p50/p95.

## Plano de implantação proposto

1. **Higiene e roteamento:** congelar/arquivar os 16 legados, remover `pycache`, fixar uma única rota CPV e impedir live code edits em execução.
2. **Decomposição:** quebrar o monólito em planner, media registry, Meta lane executor, validator e audit/state.
3. **Quota por lane:** trocar throttle global por state/lock por app+account.
4. **Pre-staging:** transformar os 52 assets elegíveis atuais em IDs Meta prontos antes da próxima criação.
5. **Batch engine:** implementar pure clone e clone+pre-staged em async/Graph batch.
6. **Scheduling nativo:** campanha/adset ACTIVE com start futuro e readback; remover ativação recorrente após canário.
7. **Canários:** 1 campanha → 3 → 10; depois 40 em três contas PAUSED/futuras, sem entrega imediata.
8. **Rollout:** somente após throughput, quota, hierarquia, UTMs e rollback passarem.

## Decisão recomendada

Não otimizar novamente dentro do script de 1.740 linhas. Criar um executor vNext modular e deixar o v2 atual apenas como fallback congelado até o canário do novo motor. O ganho principal virá de: eliminar searching/patching no hot path, pre-stagear mídia, usar lanes por conta, batch/dependencies e agendamento nativo.

## Sources

[1] https://developers.facebook.com/docs/marketing-api/asyncrequests — Meta Asynchronous and Batch Requests
    > "Each batched request can contain a maximum of 50 requests."
    > "For ad creation, include 10 or fewer ads per batch."
    > "You can also specify dependencies between related operations."
    > "Each API call can have a maximum of 1000 requests."
[2] https://developers.facebook.com/docs/graph-api/batch-requests — Meta Graph API Batch Requests
    > "Independent operations are processed in parallel while dependent operations are processed sequentially."
    > "Each call within the batch is counted separately for the purposes of calculating API call limits and resource limits."
[3] https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/copies — Meta Campaign Copies
    > "Whether to copy all the child ads. Limits: the total number of children ads to copy should not exceed 3 for a synchronous call and 51 for an asynchronous call."
    > "This endpoint supports read-after-write"
[4] https://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies — Meta Ad Set Copies
    > "If you want to copy large amount of objects, you should use asynchronous batch request."
    > "The start time of the set"
[5] https://developers.facebook.com/docs/marketing-api/guides/videoads — Meta Video Ads
    > "Create a video ad using an existing video ID and a video uploaded to Facebook."
    > "The video_id must be associated with the ad account."
[6] https://developers.facebook.com/docs/marketing-api/using-the-api/post-processing — Meta Ad Post-Processing
    > "When an ad object is IN_PROCESS, you can still make regular updates to the object and its children."
[7] https://developers.facebook.com/docs/marketing-api/reference/ad-campaign — Meta Ad Set Reference
    > "Start time, in UTC UNIX timestamp"
    > "Only ACTIVE and PAUSED are valid for creation."
[8] https://developers.facebook.com/docs/marketing-api/overview/rate-limiting — Meta Marketing API Rate Limiting
    > "Your maximum score is 60."
    > "Your maximum score is 9000."
    > "Rate limiting is at the ad account level, per application."
    > "Limit: 100 requests per second (QPS) per app and ad account combination."
[9] https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/campaign.py — Meta Python Business SDK Campaign
    > "def create_copy(self, fields=None, params=None, batch=None, success=None, failure=None, pending=False):"
[10] https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/adaccount.py — Meta Python Business SDK AdAccount
    > "def create_async_batch_request(self, fields=None, params=None, batch=None, success=None, failure=None, pending=False):"
