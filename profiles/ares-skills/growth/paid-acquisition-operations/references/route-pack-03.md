> **Histórico:** as seções sobre `UPLOAD_CANVAS`, `videos2`, `imagens2` e backlog antigo documentam operações encerradas. A entrada ativa é `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`; não procurar nem recriar `UPLOAD_CANVAS`. Para intake atual, usar `creative-operations-mgs` route-pack-02.

### Continuação de classificação após limpeza de duplicatas — precedente histórico

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
