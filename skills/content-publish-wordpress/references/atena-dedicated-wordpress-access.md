# Acesso WordPress dedicado da Atena

## Estado validado

Desde a autorização de Rodolfo na mensagem Discord `1551314627374219305`, a Atena possui uma identidade WordPress dedicada nos **45 domínios ativos do portfólio MGS** apontados por `context/sites.md`:

- usuário: `atena`;
- nome público: `Atena MGS`;
- e-mail: `atena@matteiservicesinc.com`;
- função: `editor`;
- uma senha normal forte e uma WordPress Application Password exclusiva por domínio;
- credenciais armazenadas somente no vault `MGS Conteúdo`.

A validação de implantação cobriu 40 instalações RunCloud por WP-CLI e cinco instalações externas por REST autenticada: `openzed.com`, `finanzas.openzed.com`, `cliquet.com`, `finanzas.cliquet.com` e `fincgriffin.com`.

## Contrato canônico no 1Password

Para um domínio `example.com`, resolver o item:

```text
Vault       MGS Conteúdo
Título      Atena WordPress - example.com
Categoria   Login
username    atena
password    senha normal de login/recuperação
WordPress API / wp_app_password   senha de aplicativo para REST
WordPress API / wp_user_id        ID real do usuário naquele WordPress
WordPress API / wp_role           editor
WordPress API / site_domain       example.com
```

Regras:

1. Usar `wp_app_password` somente para WordPress REST API.
2. Usar `password` somente quando um login de formulário ou recuperação estiver explicitamente autorizado; Application Password não funciona no formulário WP Admin.
3. Nunca imprimir, registrar, anexar ou colocar qualquer senha em argumento de processo, log, Discord, arquivo versionado ou documentação.
4. Resolver o item pelo título exato e validar `site_domain`, `wp_user_id` e `wp_role` por readback antes de qualquer write.
5. Não reutilizar uma Application Password em outro domínio.

## Relação com `data/sites.json`

A existência da credencial não ativa automaticamente um domínio no pipeline.

- `context/sites.md` define o portfólio conceitual.
- `data/sites.json` continua sendo a fonte técnica dos sites liberados para automação editorial.
- Se um domínio ainda não estiver em `data/sites.json`, não publicar por improviso. Primeiro criar/validar o `site_key`, vertical, país, idioma, categoria, política de publicação e publishing user.
- Ao integrar um site para a Atena, apontar `credentials_ref.item` para `Atena WordPress - <domain>`, `credentials_ref.field` para `wp_app_password` e usar no `publishing_user` o `id` lido do item/WordPress, nunca um ID copiado de outro site.

Exemplo estrutural, sem credencial:

```json
{
  "publishing_user": {
    "id": "<wp_user_id do domínio>",
    "username": "atena",
    "display_name": "Atena MGS"
  },
  "credentials_ref": {
    "vault": "MGS Conteúdo",
    "item": "Atena WordPress - <domain>",
    "field": "wp_app_password"
  }
}
```

## Validação mínima antes de publicar

1. Resolver o item do 1Password sem expor valores.
2. Confirmar domínio, usuário, ID e função por readback.
3. Fazer smoke autenticado somente leitura em:

```text
GET /wp-json/wp/v2/posts?context=edit&per_page=1&_fields=id,status
```

Resultado esperado: HTTP `200` e uma lista JSON. Esse endpoint é preferido ao `/users/me` porque algumas instalações MGS restringem especificamente a rota de usuário mesmo quando a autenticação editorial funciona.

4. Para chamadas HTTP, usar o wrapper central que mantém a credencial fora de argv; não usar `curl -u usuario:senha` em automação.
5. A autorização editorial, o contrato REC/P1 e os gates de publicação continuam obrigatórios. Ter credencial não concede autonomia fora do playbook.

## Wordfence e Application Passwords

Durante o rollout, 15 instalações RunCloud tinham a opção Wordfence `loginSec_disableApplicationPasswords` ativa. Ela foi desativada somente nesses sites para permitir a autenticação aprovada da Atena; usuário, função e REST foram validados depois da mudança.

Se a REST retornar `401 rest_not_logged_in` ou `rest_forbidden_context` para uma credencial recém-criada:

1. não rotacionar repetidamente a senha sem diagnóstico;
2. confirmar por WP-CLI que o usuário é `editor` e possui `edit_posts`, `publish_posts`, `upload_files` e `edit_others_posts`;
3. verificar se o Wordfence está ativo e se `loginSec_disableApplicationPasswords` voltou a `true`;
4. escalar para Zeus qualquer alteração de segurança; não desativar Wordfence nem elevar a Atena a Administrator;
5. repetir o smoke REST e exigir HTTP `200`.

## Segurança e recuperação

- A Atena permanece `Editor`; não elevar para `Administrator` sem nova autorização crítica de Rodolfo.
- Se uma credencial for perdida ou ficar inconsistente, Zeus deve revogar somente a Application Password nomeada `Atena API - MGS`, gerar outra e atualizar o mesmo item do 1Password com readback.
- Não criar itens duplicados. Deve existir exatamente um `Atena WordPress - <domain>` por domínio.
- Rollback deve ser escopado ao usuário `atena` recém-criado e sem conteúdo; exclusão continua sujeita ao Critical Subset vigente.
