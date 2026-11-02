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

### Intake Drive atual — `UPLOAD MANUAL`

A pasta operacional vigente é:

```text
MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL
```

`UPLOAD_CANVAS` foi removida após auditoria e aparece somente em referências históricas. Para qualquer pedido novo de tratar/classificar arquivos do Drive:

1. Resolver a raiz `MGS-AGENTS` por API e depois localizar `CRIATIVOS/UPLOAD MANUAL`.
2. Inventariar em modo read-only por Drive ID, nome, MIME, tamanho/checksum e dimensões.
3. Usar a operação/vertical/idioma informados na thread; não inferir o destino apenas pelo nome.
4. Para Brasil + “Português” sem qualificador, usar `LANG=BR`; `PT` é português de Portugal explícito.
5. Classificar `P_ORIENT` somente como `PV`, `NV`, `PH` ou `NH`; square/feed 1:1 usa `PH/NH`.
6. Sanitizar uma cópia com o gate canônico e exigir `clean=true`.
7. Subir a cópia limpa diretamente em `{OPERAÇÃO}/{IMG|VID}/01_READY`, sem subpastas de placement/idioma.
8. Validar o destino por readback; só então mover o original para `{OPERAÇÃO}/{IMG|VID}/99_LEGACY`, preservando ID/nome e sem deletar.
9. Registrar `original_filename → canonical_filename`, IDs, checksums, reserva e elegibilidade.

Pasta de apoio:

```text
GEIZIAN       cópias para upload do gestor; ignorar no pool/inventário canônico
LIBRARY META  referências da Meta Library; nunca asset final automático
```

Procedimento detalhado: `creative-operations-mgs/references/route-pack-02.md` e `creative-operations-mgs/references/mixed-media-drive-intake-ready-legacy.md`.

Os documentos com `upload-canvas-*` permanecem como precedentes históricos do backlog antigo. Não são rota ativa e não autorizam procurar/recriar `UPLOAD_CANVAS`.

