# Meta clone rate-limit — diagnóstico e solução para Ares

## Veredito

A causa principal está confirmada: o Ares está usando um app/token cujo header real informa `ads_api_access_tier=development_access`. Na nomenclatura atual da Meta isso corresponde ao Marketing API Access Tier **Limited**, que a própria Meta classifica como “for development only” e “not for production apps running for live advertisers”.[1][2]

O erro observado na conta foi exatamente `OAuthException code=17`, `error_subcode=2446079`, `User request limit reached`. A documentação atual associa essa combinação ao limite de score da conta: no tier de desenvolvimento o teto é **60 pontos**, com reads geralmente valendo 1 e writes 3; no Full Access o teto sobe para **9.000 pontos**.[1]

## Evidência MGS

- Thread `1539826050765299872`: 31/31 mensagens lidas; 0 anexos.
- Audit real: duas campanhas, dois ad sets, seis ads, seis creatives e doze vídeos foram criados; o bloqueio aconteceu no batch GET de `adsets` do primeiro readback final.
- Header live preservado: `ads_api_access_tier=development_access`.
- O runner atual faz, para duas campanhas, 10 chamadas `validate_only` de endpoints de mutation e 16 mutations reais de Ads Management. Pela regra publicada pela Meta, a projeção mínima é **26 × 3 = 78 pontos antes do readback**, acima do teto de 60. Isso exclui as leituras anteriores e finais, portanto o plano de duas campanhas em uma única janela já nasce incompatível com o tier atual.
- O helper compartilhado monitora `X-Business-Use-Case-Usage`, mas não interpreta `X-Ad-Account-Usage`. Portanto, o `total_time=34%` observado não era prova de folga: o runner estava cego para o score/reset do limite específico de ad account que gerou `17/2446079`.

## O que a pesquisa externa confirmou

1. **Full Access é a correção estrutural.** Limited/development é fortemente limitado; Full Access é o tier para produção e eleva o score de 60 para 9.000.[1][2]
2. **A Meta já define o caminho de upgrade.** O app precisa de pelo menos 500 chamadas de Marketing API nos últimos 15 dias e taxa de erro inferior a 15% nas últimas 500; o upgrade é solicitado em App Dashboard → App Review → Marketing API Access Tier → Upgrade.[1][2]
3. **Clone profundo síncrono é a rota errada para esse source.** O endpoint oficial `/{campaign_id}/copies` limita deep copy a até 3 child ads em chamada síncrona e até 51 em assíncrona; `status_option=PAUSED` é suportado e o retorno inclui o mapa source ID → copied ID.[3]
4. **Async batch é oficial e adequado para dependências.** A Meta documenta `/{ad_account_id}/async_batch_requests`, processamento assíncrono e referências JSONPath entre criação de campaign/adset/ads.[4]
5. **Batch não elimina quota.** Cada operação interna continua contando separadamente para rate/resource limits; batch reduz round-trips e organiza dependências, mas não transforma 20 chamadas em uma chamada de quota.[5]
6. **O SDK oficial confirma a superfície.** O Python Business SDK da Meta implementa `Campaign.create_copy()` com `deep_copy`, `parameter_overrides`, `rename_options`, `start_time` e `status_option`.[6]
7. **Fóruns corroboram somente as mitigações secundárias.** As respostas úteis convergem em ler headers já recebidos, esperar o reset e reduzir chamadas; também alertam que batch por si só não resolve rate limit.[7][8] Como são relatos comunitários e vários são antigos, a decisão deve seguir a documentação oficial acima.

## Solução recomendada

### P0 — corrigir o tier do app emissor do token

1. Abrir o App Dashboard do app que emitiu o token atual e verificar `Marketing API Access Tier`.
2. Se `Upgrade` estiver disponível, solicitar **Full Access**.
3. Se já existir outro app institucional MGS com Full Access, gerar um **User Access Token** válido por esse app para a mesma identidade/conta, sem introduzir System User.
4. Validar por chamada read-only e exigir no header `ads_api_access_tier=standard_access` antes de liberar o runner de produção.

Essa é a mudança que remove o gargalo de forma estrutural: **150× mais score máximo** (9.000/60). Full Access é uma propriedade do app/tier; System User não é requisito para esta solução.

### P1 — tornar o Ares quota-aware de verdade

- Parsear e persistir também `X-Ad-Account-Usage`: `acc_id_util_pct`, `reset_time_duration`, `ads_api_access_tier`.
- Separar os dois limitadores no state: `ad_account_score` e `business_use_case_usage`; nunca usar BUC 34% como substituto do account score.
- Projetar o score antes do write: reads × 1 + writes/validate-only × 3.
- Bloquear o plano antes do primeiro write se o tier for development e a projeção exceder a janela disponível.
- Em `17/2446079`, preservar objetos PAUSED, marcar `readback_deferred` e retomar após `reset_time_duration`; se o header faltar, usar o bloqueio documentado de 300 segundos. Não apagar objetos íntegros apenas porque o GET final foi limitado.
- Consumir headers das chamadas normais; não fazer requests extras apenas para consultar quota.

### P2 — usar clone nativo assíncrono para clone fiel

- Enviar uma operação assíncrona contendo `POST /{source_campaign_id}/copies` com `deep_copy=true`, `status_option=PAUSED`, `start_time`, `rename_options` e overrides aprovados.
- Polling com backoff no request-set; não loop agressivo.
- Ler o mapa `source_id → copied_id`, aplicar somente patches necessários e validar a hierarquia por IDs conhecidos.
- Usar batch/delta GET para o readback, mas contabilizar cada child call no orçamento de quota.

### P3 — modo de compatibilidade enquanto o app continuar development

- Criar **uma campanha por janela de 5 minutos**, nunca duas no mesmo ciclo.
- Pré-processar e pré-uploadar as mídias fora da janela de criação, guardando os `video_id` por checksum/asset; a rotina das 17:00 deve referenciar IDs já prontos.
- Tirar a reconciliação histórica de 126 ads/226 vídeos do caminho crítico: executar em job separado, manter snapshot com TTL e fazer apenas delta imediatamente antes do write.
- Evitar `validate_only` repetido para cada ad quando um manifest idêntico já passou em canário; manter validação no primeiro objeto de cada payload/versão e readback de todos os objetos.
- Se qualquer header estiver ausente ou o score projetado não couber, falhar antes de criar campanha.

## Decisão operacional

Não recomendo novo retry do runner atual de duas campanhas enquanto o header continuar `development_access`. O retry pode voltar a criar tudo e falhar novamente no readback porque o plano excede o teto publicado antes mesmo de contar as leituras.

A ordem correta é:

1. confirmar/obter Full Access no app emissor;
2. corrigir o monitoramento de `X-Ad-Account-Usage` e o budget de score;
3. implementar o clone nativo assíncrono;
4. manter o modo de uma campanha por janela como fallback temporário.

## Sources

[1] https://developers.facebook.com/docs/marketing-api/overview/rate-limiting — Marketing API Rate Limiting
    > "If your app is in the Marketing API development tier:"
    > "Your maximum score is 60."
    > "If your app has Full access to the Marketing API:"
    > "Your maximum score is 9000."
    > "Related error code:`17, Error subcode: 2446079, Message: User request limit reached."
[2] https://developers.facebook.com/docs/marketing-api/access — Marketing API Authorization and Access Tier
    > "Limited access (default)"
    > "Heavily rate-limited per ad account. For development only. Not for production apps running for live advertisers."
    > "Have successfully made at least 500 Marketing API calls in the last 15 days."
    > "Have made Marketing API calls with an error rate of less than 15% in the last 500 calls."
[3] https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/copies — Ad Campaign Group Copies
    > "Whether to copy all the child ads. Limits: the total number of children ads to copy should not exceed 3 for a synchronous call and 51 for an asynchronous call."
    > "This endpoint supports read-after-write"
[4] https://developers.facebook.com/docs/graph-api/asynchronous-batch-requests — Asynchronous and Batch Requests
    > "Batch API enables you to batch requests and send them asynchronously."
    > "You can also specify dependencies between related operations."
[5] https://developers.facebook.com/docs/graph-api/making-multiple-requests — Graph API Batch Requests
    > "Each call within the batch is counted separately for the purposes of calculating API call limits and resource limits."
[6] https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/campaign.py — Meta Python Business SDK Campaign copy implementation
    > "def create_copy(self, fields=None, params=None, batch=None, success=None, failure=None, pending=False):"
[7] https://stackoverflow.com/questions/54539702/facebookads-http-exception-authorizationexception-code-17-17-user-request — Stack Overflow: Code 17 and response headers
    > "Batching won't help at all with rate limiting."
    > "The best thing you can do is pull in the header x-ad-account-usage and put in a sleep once you hit a high percentage."
[8] https://stackoverflow.com/questions/48573248/overcoming-rate-limiting-in-facebook-marketing-api — Stack Overflow: Marketing API throttling strategies
    > "The issue with the mentioned solutions are that they require making a specific request to the Facebook API every second request to check the limit, which reduces the rate by half"
