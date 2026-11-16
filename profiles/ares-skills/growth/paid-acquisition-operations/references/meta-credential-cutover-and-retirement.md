# Meta credential cutover and retirement

Use this route when replacing a Meta User Access Token or Business Integration System User token, migrating active consumers, or cleaning obsolete 1Password items.

## 0. Inventário de perfis e tokens sem iniciar migração

1. Resolva as contas do recorte no catálogo positivo e aplique o checker de conta antes da leitura Meta. Leia os nós exatos de `accounts/<ACCOUNT_ID>.json`, dos contratos da operação e de `engine-v3/config.json#/accounts/<ACCOUNT_ID>`; projete apenas nome/ID da conta, `token_1password_item` ou `token_item`, `token_identity`, tipo e estado de onboarding. Não percorra nem imprima a configuração inteira: ela mistura operações e transforma uma consulta pequena em inventário irrelevante.
2. Quando a pergunta incluir tokens guardados, use `op item list --vault 'MGS Conteúdo' --format json` por subprocesso com stdout capturado; filtre em memória pela operação **e por Meta**, projetando somente ID/título. Correspondência apenas pelo nome da operação pode incluir credenciais de outros serviços. Faça a contagem após esse filtro e deduplique por item ID; não leia valores secretos para simplesmente listar cadastros.
3. Cruze os itens com os bindings atuais e marque separadamente `cadastrado`, `vinculado ao runtime`, `histórico/substituído` e `pendente`. A ausência de arquivo ou nó do Engine prova apenas ausência nessa fonte: reconcilie os contratos consultados antes de declarar que não existe binding. Não apresente metadados de identidade de um audit antigo como readback vivo.
4. Se fizer validação atual, use o transporte guardado e a referência exata da conta. Diante de falha de autenticação em cache, confirme uma vez com o item atual do cofre, mantendo o segredo em memória; não substitua a credencial produtiva para testar outra identidade. Capture HTTP, código, subcódigo e mensagem sanitizada no mesmo resultado, sem repetir GETs apenas para recuperar o diagnóstico omitido. Classifique pela mensagem: `code=190` sozinho não prova expiração. Se a resposta exigir login e instruções do Facebook, informe essa ação concreta sem chamar o token de expirado nem prometer recuperação automática.
5. Entregue primeiro os perfis e o papel de cada um, depois as contas sem vínculo confirmado e qualquer falha atual. Declare a cobertura e se houve apenas leitura; não inicie renovação, coleta via AdsPower ou cutover por uma pergunta de inventário.

## 1. Freeze the intended scope

- Identify the operations, exact accounts, Pages, Pixels, managers and active consumers covered by the cutover.
- Treat credential replacement, asset assignment, campaign write, token revocation and permanent deletion as separate actions. One never silently authorizes the others.
- Use plain operator language: say `token corporativo do System User` before introducing any provider acronym.

## 2. Pre-read both identities

For the old and replacement items, resolve secrets only in process and persist only safe metadata:

- 1Password item ID/title, credential presence and length;
- `/me` identity and `client_business_id` when applicable;
- `/debug_token` validity, App ID, user/system-user ID, scopes and expiry;
- account/Page/Pixel access and live rate-limit tier;
- exact asset assignments for app-scoped system users.

Never print or persist the credential value, authorization code or App Secret.

### Diferenciar incompatibilidade de tipo e token inválido

- Em User Access Token de anunciante, não solicitar `client_business_id`: a Meta pode retornar `code=190` com a mensagem explícita de que esse campo exige Business Integration System User. Esse resultado não prova expiração ou invalidez quando as leituras account/Page-scoped retornam HTTP200. Validar identidade por `/me?fields=id,name` e app emissor pela introspecção permitida; GET do app em si prova apenas sua metadata, não o emissor do token. Se o guard local aceitar somente a variante com `client_business_id` e impedir a leitura própria adequada, registrar a incompatibilidade separadamente e preservar os bindings; não remover o guard, não trocar para System User e não chamar a API por transporte paralelo. Ajuste de guard/permissão exige seu escopo crítico próprio. Teste de diagnóstico: code190 citando exclusivamente esse campo + conta/Page200 classifica incompatibilidade de tipo; code190 por token expirado ou inválido continua sendo falha de autenticação.

- Após aprovação do ajuste técnico, usar `ares-meta-common.py::graph_get_credential_metadata(account_id, token, inspect_token=False|True)`, nunca transporte paralelo: o guard carrega a autorização canônica da conta e permite exclusivamente `me:id,name` e `debug_token` quando `input_token` é o próprio token autenticado. Validar concordância do user ID entre identidade e introspecção, app emissor, validade, conta/Page/pixel e binding do runtime; não promover IDs de identidade ou granular scopes a ativos autorizados. Manter o `/me` corporativo e o inventário de ativos inalterados fora desse contexto. Regressão mínima: outra conta, grant ausente, token alheio, POST, discovery, campos extras e app divergente continuam negados antes do transporte ou no readback. A liberação técnica não autoriza o cutover sem seu gate próprio, nem criação de campanha.

### Cutover entre apps: emissor e capacidade são por operação

- Se o operador atualizar o mesmo item do cofre com um token de outro app, validar a leitura fresca somente em memória ou em contexto isolado, sem alimentar o cache produtivo antigo apenas para testar. O setter `configure_account_cache` exige o diretório/prefixo canônico; não afrouxar essa validação para um probe. Um teste que já recebe o token em memória pode configurar a variável de cache isolada antes do import e não chamar o setter nem o resolvedor que grava o cache.
- Resolver o grant de introspecção própria pelo perfil/app atualmente autorizados no recorte da conta, nunca por um pedido histórico cancelado. Parametrizar o novo emissor exato sob a autorização de teste, mantendo self-only, campos mínimos, GET-only e rejeição de outro token, outro perfil/tipo, issuer anterior, discovery ou hold ativo. Um `ScopeError` local após HTTP200 de identidade não significa token inválido.
- Esperar IDs de usuário app-scoped diferentes após troca de app. Conferir procedência segura da referência, nome do perfil, igualdade `me.id == debug_token.user_id`, tipo User, app emissor e acesso real aos ativos; não transportar o ID do app antigo como se fosse universal nem promover identidades/scopes a ativos autorizados. Preservar a observação anterior como histórica.
- Separar credencial validada de consumidor migrado: GETs bem-sucedidos de conta/Page/PBIA/pixel e tier vivo não alteram bindings, `app_key`, caches, hardcodes ou manifestos parciais. `expires_at=0` é apenas ausência do prazo normal informado nessa resposta, não garantia de validade eterna. Um pedido de teste não retoma campanhas em hold.

- Após confirmação explícita do novo app, parametrizar somente o emissor esperado do grant técnico da conta/ operação aprovada; não substituir um App ID global nem estender a exceção técnica às outras operações. Testar novo emissor exato, app anterior/incorreto, token alheio, outra conta, discovery e POST; todos os casos fora do recorte continuam negados. Aceitação no guard não comprova acesso à Page.
- Recoletar `ads_api_access_tier` nos headers vivos de cada conta com o token novo. Não transportar `standard_access` histórico para outro app: um token válido com scopes equivalentes pode retornar `development_access`, exigindo a quota correspondente na futura lane.
- Diante de Page `code=10`, comparar scopes da introspecção com um GET direto da Page realmente escolhida no pedido e vinculada ao perfil novo antes de culpar o token ou o batch. Não usar as Pages do histórico da conta como inventário do novo anunciante nem exigir acesso a todo o legado para adotar seu perfil. Em BOT com User Access Token, resolver somente a Page/pg solicitada, sem importá-la na BM; autorização expressa para Pages presentes/futuras do perfil dispensa outro OK de escopo por Page, não a validação real nem os gates de campanha. Se o pedido preservar uma Page legada específica, validar somente essa dependência. Scopes presentes e `target_ids` ausentes na introspecção não distinguem sozinhos falta de vínculo, consentimento ou restrição do app. Preservar o erro com seu recorte e suspender apenas a execução que dele depende; não conceder permissões ou trocar de perfil como fallback.

## 3. Inventory the complete consumer chain

Do not stop at the central Engine config. Traverse every live path:

```text
scheduler job
→ wrapper
→ Python/runtime module
→ account or operation contract
→ 1Password item
→ protected local cache
```

Include report jobs, monitors, guardrails, recovery runners and paused jobs that may later resume. Search other active profiles and system schedulers before declaring an item unused. Classify references in historical audits/backups separately from executable consumers.

`last_status=ok` is not proof of cutover: an old valid item or cache can keep a hardcoded consumer green.

## 4. Apply a staged cutover

1. Create a backup of every active config/runtime file to be changed.
2. Update account/operation bindings first.
3. Make runtime modules load `token_1password_item` or the operation credential reference instead of duplicating item titles.
4. Give the replacement a distinct cache path and require the cache payload's `item` to match the requested item.
5. Remove stale credential caches only after the replacement cache is mode `0600`, names the new item and contains a credential.
6. Preserve the old credential as inactive rollback when the identity changes or write capability has not yet been proven. If the operator has explicitly prohibited its further use, retain it only as historical material pending authorized retirement; never reactivate it as fallback. A checkpoint recording that decision does not disable existing schedulers or remove their bindings, so report those technical effects only after their own verified execution.

For a replacement token with the same app-scoped System User, App ID, scopes and target-asset readback, a narrower prior grant may be retired after the replacement proves equivalent access. For a different human/system-user identity, retain the prior credential until an authorized controlled write proves the replacement, unless separately authorized retirement applies; retention never overrides an explicit prohibition on reusing that identity.

## 5. Verify every consumer without side effects

- Em migração entre apps, teste novamente os materializadores com a configuração **já instalada**, além do staging: um smoke pode passar com o app antigo e falhar após o cutover porque o builder conservou um default histórico. Passe `app_key` explicitamente do nó exato da conta a cada consumidor live; mantenha defaults de fixtures/compatibilidade fora do runtime produtivo. Exercite também a troca de conta no mesmo processo: o cache opt-in de uma conta não pode vazar como default para a seguinte. Cache precisa continuar exigindo igualdade de `item`, mesmo com caminho dedicado.
- Quando o operador já concluiu manualmente e proibiu alterações, reconcilie somente a coordenação com receipt de suspensão, CAS/locks e fence durável por request. Libere leitores apenas após validar o receipt; não use `release/COMPLETE`, não marque QA concluído e não reabra o recovery antigo. Preserve checkpoint, IDs, journals, reservas e incertezas; um writer novo substituir a lease não pode apagar a proibição de replay. Teste receipt corrompido, CAS divergente, outra conta e nova admissão sem nenhum POST Meta.

- Import/read back runtime constants and resolved account/operation references.
- Run shell syntax and Python compile checks.
- Execute live `--dry-run` or read-only smokes for every distinct consumer family, suppressing Discord posts and Meta writes.
- Re-list the scheduler and report separately:
  - enabled and scheduled;
  - paused/retired;
  - no cron by design.
- If a natural tick has not occurred after the fix, say that the dry-run passed and the next tick is pending; do not label it a natural successful run.

## 6. Retire 1Password items safely

Before deletion, require all of the following:

- exact item ID/title pre-read;
- zero active executable references;
- replacement or deliberate retirement confirmed;
- external operation ownership checked when the item belongs to another site/team;
- active keepers re-read and healthy.

Never delete a 1Password item merely because its User Access Token field is obsolete when the same item also stores the live App Secret, App ID, Configuration ID or provisioning credential. Split or clear only the obsolete field under its own approved migration.

`op item delete <ITEM_ID> --vault <VAULT>` moves an item to **Recently Deleted** for 30 days; it does not permanently purge it and does not revoke the Meta token. Removing a Connected App or revoking permissions is a separate Meta-side action and may invalidate multiple grants, so never use it as a substitute for vault cleanup.

After deletion:

- confirm every target item is absent from the active vault;
- confirm every keeper remains present;
- re-read a representative account with the active replacement token;
- update rollback status in canonical records;
- record whether permanent purge, Meta revocation or Connected App removal occurred.

## 7. Automate future asset assignment with isolation

An Admin User or provisioning-only Admin System User can assign minimum tasks to an app-scoped System User and manage Business Asset Groups. Keep that provisioning credential out of daily Campaign Ops. Auto-enroll only operation/manager allowlisted assets after ownership, naming, Page, Pixel and account-health reconciliation; ambiguous assets remain approval-gated.

## Completion evidence

- active consumer references point only to the intended item;
- live account/Page/Pixel readback succeeds;
- tier and usage headers are captured when returned;
- dry-runs cover every distinct scheduler consumer;
- old caches/hardcodes are absent from active paths;
- deleted vault items and preserved keepers have exact readback;
- zero unapproved Meta writes, posts, revocations or ownership changes;
- audit/checkpoint and infrastructure report are complete.
