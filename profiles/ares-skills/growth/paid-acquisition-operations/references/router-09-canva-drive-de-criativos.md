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
