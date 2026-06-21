---
name: paid-acquisition-operations
description: "Operações de aquisição paga/ads para MGS: estruturar operações piloto, taxonomia de criativos, Drive de assets, inventário, credenciais read-only/controlled-write, e guardrails antes de Meta/Google Ads em produção."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [ads, growth, meta-ads, google-drive, creatives, taxonomy, mgs]
---

# Paid Acquisition Operations — MGS/Ares

Use esta skill quando Rodolfo pedir para estruturar, auditar ou operacionalizar campanhas pagas, criativos, Drive, inventário, tracking ou integrações Meta/Google Ads. O padrão é **processo primeiro, credencial depois, execução por último**.

## Princípios

1. **Comece pela operação piloto** — defina uma operação única (`VERTICAL_COUNTRY_LANG`, ex.: `CC_US_ES`) antes de generalizar.
2. **Estruture antes de conectar credenciais** — taxonomia, Drive, inventário e regras de decisão devem existir antes de API write.
3. **Read-only primeiro** — Meta Ads e Drive começam em leitura; write só em sandbox ou com aprovação explícita.
4. **Credenciais nunca no chat** — buscar via 1Password/vault e reportar apenas presença, item, len/status ou validações sem segredo.
5. **Ações em produção exigem aprovação explícita** — pausar, clonar, subir criativos, tracking/pixels, budget e billing seguem as regras MGS. Billing é critical subset/double-confirm.
6. **Automatizar o manual primeiro** — pergunte/registre como os gestores fazem corte, pausa, replacement e escala antes de propor melhoria.

## Ordem recomendada para uma nova operação

```text
Ordem | Etapa
------|------------------------------------------------------------
1     | Definir operação piloto: VERTICAL_COUNTRY_LANG
2     | Fechar taxonomia oficial de criativos
3     | Definir estrutura Drive por operação
4     | Criar inventário mínimo/rastreabilidade
5     | Definir regras de decisão dos gestores
6     | Criar/atualizar skills operacionais do Ares
7     | Conectar Drive/Meta em read-only
8     | Gerar relatório diagnóstico
9     | Testar execução em sandbox
10    | Liberar write controlado em produção com aprovação
```

## Taxonomia base de criativos

Para qualquer trabalho de nomenclatura, renomeação, inventário ou classificação de criativos, carregar também a skill dedicada `creative-taxonomy-mgs`. Ela é a fonte operacional detalhada para campos, P_ORIENT, status, inventário mínimo, Drive e metadata gate.

Modelo preferencial:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Regras:

- `STATUS` não entra no nome; fica na pasta ou inventário.
- IDs (`drive_id`, `meta_creative_id`, `campaign_id`) não entram no nome; ficam no inventário/metadados.
- `ANGLE` deve vir de dicionário controlado por operação/idioma.
- Se o ângulo for incerto, usar `UNKNOWN` e preencher `notes`.
- Não inventar classificação confiante sem evidência.
- Nome limpo, uppercase, sem acento, com underscore.

Pitfall: não deixar a taxonomia viva apenas como spec solto ou comentário de sessão. Quando Rodolfo pedir para “criar a skill”/“execute” sobre taxonomia já estabilizada, criar ou atualizar a skill classe `creative-taxonomy-mgs` e apontar esta umbrella para ela, em vez de criar uma skill estreita por sessão.

### P_ORIENT

```text
Código | Person    | Orientation
-------|-----------|------------
PV     | PERSON    | VERTICAL
PH     | PERSON    | HORIZONTAL
NV     | NO_PERSON | VERTICAL
NH     | NO_PERSON | HORIZONTAL
```

Regra atual de Rodolfo: usar somente `PV`, `PH`, `NV`, `NH`. Códigos `PS`, `NS`, `PU`, `NU`, `UU` foram desconsiderados e não devem entrar em nomes finais. Para detalhes, carregar `creative-taxonomy-mgs`.

## Estrutura Drive recomendada

Use pasta por operação, não por site, pois o mesmo criativo pode rodar em sites diferentes.

```text
MGS-CRIATIVOS/
└── <OPERATION>/
    ├── IMG/
    │   ├── 01_READY
    │   ├── 02_TESTING
    │   ├── 03_TESTED
    │   ├── 04_WINNERS
    │   ├── 05_REJECTED
    │   └── 99_LEGACY
    └── VID/
        ├── 01_READY
        ├── 02_TESTING
        ├── 03_TESTED
        ├── 04_WINNERS
        ├── 05_REJECTED
        └── 99_LEGACY
```

## Inventário mínimo

```text
filename
vertical
country
language
format
angle
person
orientation
p_orient
variant
status
performance_label
source
page_id
asset_drive_id
meta_creative_id
origin_campaign_id
width
height
aspect_ratio
placement_fit
created_at
notes
```

Valores usuais:

```text
status: READY, TESTING, TESTED, WINNER, REJECTED, LEGACY
performance_label: GOOD, BAD, INCONCLUSIVE, UNKNOWN
```

## Gate obrigatório de metadados antes de campanha

Antes de usar qualquer criativo em campanha/teste, Ares deve validar metadados no VPS:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.png
```

Se retornar `clean: false`, limpar antes de usar:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
```

Usar o arquivo `.metadata-clean` como asset de campanha. Se a limpeza falhar ou o formato for incompatível, escalar para Zeus/Rodolfo antes de subir campanha com arquivo bruto.

Referências canônicas:

- `/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md`
- `/root/mgs-agent/logs/creative-metadata-sanitizer.jsonl`

## Tamanhos e placements

Não colocar tamanho no nome salvo exceção operacional explícita. Guardar em inventário (`width`, `height`, `aspect_ratio`, `placement_fit`). Para operações Meta comuns:

```text
Formato operacional | Dimensão  | Aspect ratio | Uso
--------------------|-----------|--------------|-------------------------
FEED                | 1080x1080 | 1:1          | Feed Facebook/Instagram
STORY               | 1080x1920 | 9:16         | Stories Facebook/Instagram
```

Mapeamento quando só há FEED/STORY:

```text
Dimensão  | Sem pessoa | Com pessoa | Orientation
----------|------------|------------|------------
1080x1080 | NH         | PH         | HORIZONTAL
1080x1920 | NV         | PV         | VERTICAL
```

## Canva Connect / Canva Teams → Drive de criativos

## Canva → Drive de criativos

Quando Rodolfo pedir para organizar criativos que estão em pastas do Canva e jogar no Google Drive, operar como pipeline **read-only primeiro** e escolher o caminho conforme o plano/acesso Canva. Para lotes já extraídos do Canva e enviados ao Drive em `UPLOAD_CANVAS`, usar o fluxo de inventário visual/proposta antes de qualquer write: `references/upload-canvas-drive-inventory-workflow.md`.

### Caminho oficial: Canva Connect API

1. Criar/usar integração Canva Connect privada com usuário que tenha acesso às pastas da Kelly/gestores.
2. Usar scopes mínimos: `folder:read`, `design:meta:read`, `design:content:read`.
3. Inventariar pastas/designs antes de baixar ou subir qualquer arquivo.
4. Exportar designs via job assíncrono (`POST /v1/exports`, depois polling em `GET /v1/exports/{exportId}`); URLs de download expiram em 24h.
5. Classificar Feed/Stories/Reels por dimensão/aspect ratio e idioma por nome/pasta ou OCR quando necessário.
6. Subir para Drive somente após aprovação explícita para write.

Pitfalls:

- `GET /v1/folders/{folderId}/items` lista pastas, designs e image assets, mas a documentação atual indica que **video assets soltos não são retornados**; designs exportáveis ainda podem gerar MP4 quando o formato estiver disponível.
- Integrações privadas do Canva Connect são direcionadas a Canva Enterprise; em Canva Teams/Equipe, validar no Developer Portal antes de prometer API privada.

Detalhes técnicos, endpoints, scopes e estrutura piloto: `references/canva-connect-drive-creative-sync.md`.

### Fallback: automação local no Windows

Se o Canva bloquear o VPS/navegador remoto ou o plano Teams não permitir integração privada, usar automação local com Playwright no computador do Rodolfo. O usuário faz login e códigos manualmente; o script usa a sessão local.

Regra crítica: **não inferir imagem vs vídeo pelo nome do criativo nem pela dimensão**. O fluxo correto é abrir a pasta, clicar nos três pontinhos do item, clicar `Baixar`, manter o formato pré-selecionado pelo Canva (`Vídeo MP4`, `PNG`, `JPG`, etc.) e só depois classificar o arquivo real baixado.

Começar com audit e piloto pequeno:

```text
npm install
npm run setup
npm run login
npm run audit -- "URL_DA_PASTA"
npm run download:pilot -- "URL_DA_PASTA" 3
```

Detalhes do fluxo local, seletores observados, guardrails, retomada/resume e pitfalls de pastas grandes com nomes repetidos: `references/canva-local-browser-automation.md`.
Padrão específico para retomar pastas grandes a partir de lista-mestre/manifest de `designId`, incluindo V2→V3 e seed de manifest: `references/canva-manifest-resume-pattern.md`.
Recuperação específica quando manifests V2 estão parciais, Cloudflare bloqueia Playwright e é preciso conectar ao Chrome real via CDP: `references/canva-nicolas-v3-cdp-recovery.md`.
- `GET /v1/folders/{folderId}/items` lista pastas, designs e image assets, mas a documentação atual indica que **video assets soltos não são retornados**; designs exportáveis ainda podem gerar MP4 quando o formato estiver disponível.

### Caminho sem Enterprise/API privada

1. Não convidar Google Service Account para Canva; ela serve para Drive/API Google, não como usuário Canva.
2. Usar um **e-mail real operacional** para Canva, por exemplo `assets@...` ou `criativos@...`, capaz de receber convite e aceitar login.
3. Guardar login/senha/TOTP/códigos de acesso no vault/1Password; nunca pedir código de login no chat.
4. Evitar usar a conta pessoal/admin de Rodolfo para automação.
5. Fazer piloto com uma pasta de gestor antes de operar o backlog completo.
6. Se o Canva bloquear navegador/headless no servidor via Cloudflare, considerar automação local no computador/browser já logado do Rodolfo, ou fallback manual com organização posterior no Drive.

Atenção: quando Canva baixa designs misturados com um único formato, static/video podem sair errados. Primeiro separar `IMG` vs `VID`; depois exportar estáticos em PNG/JPG e animados/vídeos em MP4.

Detalhes técnicos, endpoints, scopes e estrutura piloto: `references/canva-connect-drive-creative-sync.md`.
Detalhes técnicos, endpoints, scopes e estrutura piloto: `references/canva-connect-drive-creative-sync.md`.

### Inventário read-only de UPLOAD_CANVAS e sanitizer

Quando Rodolfo já tiver subido criativos brutos para `MGS-CRIATIVOS/UPLOAD_CANVAS`, Ares deve começar por inventário read-only recursivo via Drive, não por mover/limpar/renomear arquivos. `UPLOAD_CANVAS` é RAW/original; preservar origem e classificar só com evidência. Se a vertical ficar majoritariamente `UNKNOWN`, não inventar por nome de gestor — fazer amostragem visual/read-only antes do plano final.

Antes de usar criativo em campanha/teste, aplicar o gate de metadata: verificar com `/root/mgs-agent/scripts/clean-creative-metadata.sh verify`; se `clean=false`, limpar uma cópia/staging com `clean --agent ares`; se falhar, escalar antes de usar arquivo bruto. Não sanitizar Drive originals in-place.

Detalhes do padrão, campos de inventário, duplicatas por MD5 e relatório infra: `references/upload-canvas-drive-inventory-and-sanitizer.md`.

### Fallback sem Canva Enterprise/API privada

Quando a API privada não for viável e o Canva bloquear automação no VPS, usar **automação local assistida** no computador do Rodolfo:

1. Rodolfo roda um pacote local Node/Playwright.
2. Login, senha e código de e-mail/MFA são digitados apenas por ele no navegador local — nunca no Discord.
3. A primeira etapa é somente auditoria da pasta: screenshot, texto visível, HTML e inventário de elementos clicáveis.
4. Só depois de revisar a auditoria adaptar o script para baixar estáticos como PNG/JPG e vídeos/animações como MP4.
5. Se anexos `MEDIA:/...` não aparecerem no Discord, entregar o pacote como arquivos texto com caminho + conteúdo completo.

Referência operacional: `references/canva-local-automation.md`.

### UPLOAD_CANVAS → Drive organizado com limpeza de metadata

Quando Rodolfo subir criativos brutos para `MGS-CRIATIVOS/UPLOAD_CANVAS`, a ordem correta é **organizar logicamente antes de limpar/copiar**:

1. Manter `UPLOAD_CANVAS` como RAW/original intacto.
2. Gerar inventário read-only recursivo.
3. Classificar por vertical/operação → `IMG/VID` → placement/tamanho → idioma → status; gestor/origem fica em metadado, não como estrutura final.
4. Deduplicar por checksum antes de limpar/copiar.
5. Montar fila de cópia com destino proposto.
6. Após aprovação explícita de Rodolfo para Drive write, baixar cada canônico, limpar metadata localmente, verificar `clean=true`, criar pastas destino e subir a versão limpa.
7. Registrar relatório com source/destination IDs, hashes e status; parar em erro recorrente/quota/auth.

Destino recomendado:

```text
MGS-CRIATIVOS/<OPERATION>/<IMG|VID>/<FEED|STORY|LANDSCAPE|UNKNOWN>/<LANG>/<STATUS>/
```

Detalhes, pitfall de OAuth/Service Account, sanitizer MP4, comparação pós-reorganização manual e limpeza de pastas `01_READY_CANDIDATE`: `references/upload-canvas-drive-clean-copy.md`.

Quando Rodolfo der autonomia explícita para resolver a fila inteira, reduza narração técnica intermediária: corrija/reinicie/retome com segurança, evite reportar cada alerta de processo em background, e volte ao usuário principalmente com bloqueio real ou relatório final consolidado. Se ele reorganizar manualmente o Drive, trate a nova estrutura dele como fonte de verdade antes de comparar/deletar.
Long-runs com centenas de uploads exigem controle de processo único, refresh OAuth em `401`, reconciliação por `queue_id` e limpeza auditada de duplicados: `references/drive-clean-copy-long-run-recovery.md`.
Para filas longas já aprovadas, usar o padrão de controlador/resume sem upload paralelo: `references/drive-bulk-upload-controller.md`.
Para etapa final de organização, backlog `00_REVIEW`, promoção posterior para `01_READY_CANDIDATE`, validação de report e retry bounded quando 1Password/OAuth rate-limit bloquear, usar `references/drive-final-organization-review-and-promotion.md`. Nunca tratar `00_REVIEW` como pronto para campanha.

Para o fechamento final da organização Drive — promover `01_READY_CANDIDATE` para `01_READY`, zerar `REVIEW`, preservar `UPLOAD_CANVAS` como RAW e explicar a diferença entre RAW e cópias limpas — seguir `references/drive-final-ready-promotion-and-raw-preservation.md`. Pitfall crítico: em reports de clean-copy, `source_drive_id` é normalmente o RAW em `UPLOAD_CANVAS`; ações de promoção/rejeição devem recair sobre o `dest_drive_id` da cópia limpa, salvo pedido explícito de mexer no RAW.

Quando a nomenclatura já foi normalizada e Rodolfo disser para executar a organização final, seguir `references/upload-canvas-final-organization-after-naming.md`: inventário fresco, classificação visual dos pendentes, validação de variante 3 dígitos, fila final executor-compatible (`original_filename` obrigatório), dedup MD5, clean-copy com report e validação por status.

### Continuação de classificação após limpeza de duplicatas

Quando a pasta RAW tiver sido parcialmente ajustada a pedido explícito de Rodolfo — por exemplo, vídeos duplicados movidos de `cartao de credito/videos` para `videos2` — sempre recomeçar a classificação com inventário Drive read-only fresco. Não reutilizar CSV anterior para proposta final.

Antes de propor organização final, gerar uma checagem de anomalias/visual para:

```text
Caso                                | Ação
------------------------------------|--------------------------------------------------
JOBS dentro de cartao de credito    | Confirmar visualmente; não forçar como CC
Idioma UNKNOWN                      | Marcar revisão ou confirmar visualmente
Placement UNKNOWN / sem dimensão    | Marcar revisão técnica; não inventar placement
Duplicata MD5 ou mesmo design Canva | Validar visualmente e propor holding folder
videos2/imagens2 já existentes      | Incluir na auditoria RAW e nos totais
```

Se Rodolfo pedir explicitamente para mover duplicatas para uma pasta holding (`videos2`, `imagens2`), a sequência segura é: preflight de contagens, sinal de duplicata por design ID/MD5, validação visual em contact sheet, mover via Drive parents PATCH, recontar source/destination e verificar duplicatas restantes. Detalhes: `references/upload-canvas-classification-continuation.md`.

### Duplicadas visuais no Drive

Quando Rodolfo pedir para identificar criativos iguais com nomes diferentes em `UPLOAD_CANVAS`, faça primeiro análise read-only por comparação visual, não por nome nem apenas MD5. Gere CSV auditável com grupos, `KEEP` e `TRASH_DUPLICATE`; só envie duplicadas para a lixeira depois de confirmação explícita. Para detalhes do fluxo, OAuth fallback e formato de relatório, usar `references/drive-visual-duplicate-cleanup.md`.

### Duplicadas MD5 no Drive organizado

Quando Rodolfo aprovar deletar duplicados exatos no Drive, operar por MD5 somente no escopo organizado por padrão; `UPLOAD_CANVAS` continua RAW/intacto salvo autorização explícita para RAW. Gerar plano mantendo 1 keeper por `md5Checksum`, preferindo `01_READY_CANDIDATE` e nome canônico, executar trash via Drive API e validar com novo scan. Atenção: Service Account pode ter `canEdit=true` e ainda assim `canTrash=false`; nesse caso tentar OAuth de usuário real, e se o refresh token estiver expirado/revogado seguir fluxo de recuperação. Detalhes: `references/drive-md5-duplicate-trash-and-oauth-recovery.md`.

### Piloto de nomenclatura de criativos

Quando Rodolfo pedir para testar nomenclatura antes do backlog completo, fazer uma amostra read-only balanceada — por exemplo 3 `IMG` + 3 `VID` — com contact sheet e CSV de nomes sugeridos. Aplicar a regra atual `P_ORIENT` somente `PV`, `PH`, `NV`, `NH`; tratar `FEED` 1:1 como `HORIZONTAL` para fins de nome e deixar `ANGLE=UNKNOWN` quando a evidência visual/textual for insuficiente. Detalhes: `creative-taxonomy-mgs/references/upload-canvas-pilot-naming-review.md`.

## Credenciais Google Drive

Preferir **Google Service Account** para leitura e inventário. Para write/upload em `My Drive` pessoal, validar quota antes: Service Account pode falhar com `403 storageQuotaExceeded` porque não tem armazenamento próprio. Se o destino estiver em My Drive pessoal, usar OAuth de usuário real ou mover a operação para Shared Drive.

Fluxo Service Account/read-only:

1. Criar Service Account.
2. Guardar JSON no 1Password.
3. Compartilhar `MGS-CRIATIVOS` com o e-mail da Service Account.
4. Começar como Viewer; Editor só quando Rodolfo explicitamente quiser testar write.
5. Validar sem expor segredos: item encontrado, JSON parseado, private key presente, folder acessível, permissões/capabilities, filhos listados.

Fluxo OAuth/write em My Drive:

1. OAuth Desktop app com scope mínimo necessário, normalmente `https://www.googleapis.com/auth/drive` para upload/cópia.
2. Refresh token e client secret ficam em arquivo root-only/permissão 600 ou vault; nunca imprimir no chat.
3. Script deve aceitar modo por `.env`, ex.: `ARES_DRIVE_AUTH_MODE=oauth`, e reportar apenas `auth_mode=oauth_user`, `storage=my_drive`, capabilities e status.
4. Fazer smoke test com 1 arquivo antes da fila completa.
5. Antes de rodar centenas de uploads usando quota pessoal de Rodolfo, pedir aprovação explícita de escopo.


Referência de pipeline e pitfall de quota: `references/drive-creative-clean-copy-quota.md`.

Reportar algo como:


```text
Item 1Password | Encontrado
folder access  | OK
can_edit       | true/false
children       | nomes de pastas, sem IDs sensíveis se não necessário
```

## Meta Ads intraday / chatbot operations

Quando Rodolfo pedir gestão de tráfego Meta Ads, cortes intraday, reativação de campanhas, Messenger/chatbot, CPS/subscribers, ou operação determinística de campanhas, carregar também:

- `meta-ads-intraday-operations` — processo intraday: R1-R5, reativar-todas, carência TEST, logs e auditoria.
- `meta-ads-governance-guardrails` — permissionamento, token, budget, rate limit, auditoria e transição read-only/dry-run/write.

Padrão aprendido no piloto Meta Messenger: separar **crons determinísticos** (reativar-todas e cortes intraday) da camada **gestor inteligente/head de aquisição**. Intraday deve executar regras objetivas por operação país+vertical, com logs resumidos apenas quando houver ação/erro. Não misturar ROI externo/Lovable no primeiro corte determinístico antes de mapear a métrica Meta correta de CPS/subscriber.

Pitfalls específicos:

- Não assumir moeda do teto informado pelo usuário; validar `currency` da conta Meta. Se divergir (ex.: usuário fala R$ e conta retorna USD), registrar como referência e não usar como kill switch sem confirmação.
- Não usar `reativar-todas` sem lista de exclusão configurável; a lista pode começar vazia, mas perguntar antes de adicionar qualquer campanha.
- Não pausar campanha com `TEST` no nome durante carência de 3 dias; preferir `created_time` da Meta, fallback para `first_seen_at` local.
- Não enviar log intraday a cada 30 minutos se nada aconteceu, salvo política explícita diferente.
- Não reportar leitura Meta como sucesso sem HTTP real da Graph API e sem ocultar token no relatório.
- Se scripts Meta/cron começarem a dar timeout segurando `meta-api-throttle-state.json`, verificar drift de `time.monotonic()` persistido após reboot antes de culpar Graph/API. Corrigir o throttle para zerar `last_request_monotonic` quando `last > now` e limitar sleep ao intervalo configurado. Referência: `references/meta-api-throttle-monotonic-reboot.md`.

## Regras de decisão de campanha

Regra inicial discutida para CPA ponderado:

```text
HOA ponderado = Hoje 50% + Ontem 30% + D-2 20%
```

Decisões atuais para OpenzedFinanzas/Europa:

- Intraday R1-R5 e HOA são camadas separadas e devem coexistir inicialmente.
- HOA roda nos checkpoints `08:00`, `12:00`, `15:00`, `18:00`, `22:00` no timezone da conta.
- Relatório Discord do HOA deve ser legível para gestor: cabeçalho humano com horário no fuso da conta, `ID REC` com 3 dígitos, campanhas ordenadas por sufixo `001...`, sem Meta ID/Campaign ID no report normal. Ao mesclar campanha viva + histórico de insights, ocultar `HIST` duplicado quando já existir linha viva (`ACTIVE`/`PAUSED`/`IN_PROCESS`/`WITH_ISSUES`) com o mesmo nome/número; manter duplicata técnica só em audit JSON.
- Europa/GDPR usa `MO=complete_registration` e `CPMO=spend/MO`, não CPS/subs.
- “Dia ruim” para replacement exige dia completo, gasto mínimo `USD 5.00` e `MO >= 2`; replacement requer 2 dias completos ruins.
- Budget total de referência: `USD 300/dia`; 20% (`USD 60/dia`) reservado para testes de criativos novos.
- CPMO alvo inicial do HOA: `USD 2.00`; Ares deve otimizar para chegar nele.
- Campanha nova nunca deve ser criada com budget maior que `USD 25/dia` inicialmente.
- Replacement deve: mapear loser → identificar melhores criativos da conta inteira por menor CPMO nos últimos 3 dias → clonar campanha/adset/criativos do zero → validar clone → deletar a loser se a Meta/API permitir; se não permitir delete, arquivar. O clone deve usar a mesma página, mas pode usar criativo vencedor de outra página.
- Campanhas de replacement devem ser programadas para o dia seguinte, preferencialmente `01:00` no timezone da conta.
- Cada campanha nova deve ter exatamente 3 criativos.
- Se não houver espaço de budget para testes, não executar; avisar só no relatório final das 22h.
- Para controlled-write de duplicação/normalização em massa, primeiro validar o estado vivo e calcular `needed = target_count - current_count`; não criar campanhas extras quando a conta já está no alvo. Usar `references/meta-controlled-write-bulk-duplicates.md` para o padrão de auditoria, cleanup e verificação.
- Para remover bid cap em campanhas novas, usar `bid_strategy=LOWEST_COST_WITHOUT_CAP` no campaign e omitir `bid_amount` no adset; não tentar resolver apenas no adset.

Guardrails:

- Não cortar teste antes de janela mínima definida sem autorização.
- Exigir gasto mínimo/volume antes de avaliar criativo.
- Separar **pausar** de **substituir/replacement**.
- No começo o Ares recomenda; não executa automaticamente.
- Budget/billing nunca automáticos.

## Referências

- `references/cc-us-es-setup.md` — decisões iniciais da operação piloto CC_US_ES: Drive, taxonomia, ângulos, tamanhos e acesso via Service Account.
- `references/drive-review-duplicate-cleanup-and-00-review-closure.md` — fluxo para revisar/ajeitar pasta inteira no Drive, deduplicar, resolver OAuth delete, fechar `00_REVIEW` e preservar RAW.
