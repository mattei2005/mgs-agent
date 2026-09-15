# Facebook Login for Business — callback Authorization Code

Use esta referência ao implementar o retorno HTTPS e a troca de código de um Facebook Login for Business, especialmente para **Business Integration System User access tokens**.

## Sequência operacional

1. **Congele a identidade da autorização.** Leia o contrato/checkpoint e confirme app, Configuration ID, tipo de token, Business Portfolio cliente e ativos de teste. Não misture user token e system-user no mesmo pedido.
2. **Faça o preflight da callback.** Escolha um domínio HTTPS controlado pela MGS, confirme DNS/TLS e ownership e verifique se a URI exibida no App Dashboard foi realmente criada para este fluxo. Trate URI herdada, padrão ou sem handler comprovado como legado.
3. **Peça a autorização de infraestrutura antes do deploy.** Callback, domínio, App Secret, token e mudança de Redirect URI são camadas diferentes; autorização para navegar no dashboard não autoriza deploy ou troca de credencial.
4. **Implante um receptor mínimo.** Aceite somente `GET`, valide `state` e `code`, escreva o código de autorização de forma restrita e retorne apenas uma confirmação genérica. Não coloque App Secret ou token no host web quando o código puder ser trocado no runtime seguro do Ares.
5. **Adicione a nova Redirect URI sem remover a antiga.** Preserve rollback até o fluxo novo passar de ponta a ponta; remova a URI antiga apenas em ação separada, depois de provar que não há consumidor ativo.
6. **Arme um link único.** Gere `state` com CSPRNG (mínimo 32 bytes), persista apenas seu SHA-256 com TTL curto e contexto do request e invoque o diálogo com `config_id` e `response_type=code`. No SDK, use também `override_default_response_type=true` para system-user.
7. **Delegue o conjunto mínimo e pare diante de claim implícito.** No primeiro login de uma arquitetura ainda não validada, selecione uma única unidade canário: Business Portfolio cliente, uma Página, uma conta de anúncios e somente o Pixel realmente usado no teste. Em uma expansão multi-conta posteriormente autorizada pelo owner, primeiro reconcilie a matriz exata `operação → gestor → conta → Page → Pixel` e selecione somente esse conjunto operation-scoped; nunca marque todo o inventário do Business Portfolio por conveniência. Adicionar ativos ao Business Portfolio não amplia retroativamente o grant/token BISU existente: uma nova autorização precisa selecionar os novos ativos e o readback deve provar cada ID antes do cutover. Antes de avançar, classifique cada ativo como propriedade do portfólio, acesso compartilhado/parceiro ou propriedade de pessoas individuais; aparecer em **Business Settings** não prova ownership. Compartilhar um ativo já pertencente ao portfólio com o app delega acesso ao token e não muda sua propriedade. Porém, se a Meta avisar que uma Página será **claimed and added** ao portfólio, trate o avanço como write estrutural de ownership: pare, explique a diferença entre vínculo e propriedade e exija autorização expressa. Sem essa autorização, escolha uma Página já pertencente ao portfólio ou revise a configuração; não use `Next` para resolver o aviso silenciosamente.
8. **Troque o código server-to-server.** Use a versão Graph vigente na documentação/runtime, App ID e App Secret lido do 1Password apenas em memória. Inclua a mesma `redirect_uri` quando o grant exigir correspondência. Nunca imprima código, segredo ou token.
9. **Armazene antes de habilitar consumo.** Grave o token diretamente no cofre aprovado. Se a identidade disponível do 1Password for read-only, pare antes da emissão ou coordene salvamento pela UI segura; nunca contorne isso exibindo o token numa página ou no chat.
10. **Valide read-only antes de qualquer campanha.** Leia `/me?fields=id,client_business_id`, permissões/expiração, Páginas e contas acessíveis; confirme nome, moeda, timezone, health e headers de rate limit da conta exata. Só então registre alias/credential reference.

## Receptor seguro

- Use comparação constante (`hash_equals`) do SHA-256 de `state`.
- Faça consumo single-use sob lock; persista por escrita atômica e rejeite replay.
- Mantenha pending/completed fora do webroot. Se o PHP-FPM limitar paths, use diretório oculto dentro do webapp **somente após provar HTTP 403/404** para esse diretório; não enfraqueça a jail para facilitar o deploy.
- Proteja a resposta com `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, CSP restritiva, frame deny e `X-Robots-Tag: noindex`.
- Não renderize `code`, `state`, token, erro detalhado da Meta ou stack trace.
- Considere que o authorization code pode aparecer em access logs do proxy por ser query string; troque-o imediatamente, trate-o como curto e single-use e não replique logs em chat/auditoria.

## Matriz mínima de teste antes do login real

```text
Caso                         Esperado
---------------------------  ----------------------------------------
GET sem parâmetros           HTTP 400, mensagem genérica
POST                          HTTP 405
state inexistente/inválido    HTTP 403
state válido + código falso   HTTP 200 e registro restrito
replay do mesmo state         HTTP 403
corpo da resposta             zero code/state/token
TLS                           válido, sem redirect inesperado
headers                       no-store + no-referrer + CSP/noindex
state storage via HTTP        403/404
source versus deploy          checksum idêntico
artefatos de autoteste        zero pendentes ao encerrar
```

Se o teste válido falhar, faça readback do estado e do PHP-FPM antes de alterar: RunCloud pode aplicar `realpath_turbo.open_basedir` mesmo com o `open_basedir` nativo vazio. Corrija o local de armazenamento dentro da jail e repita a matriz completa; nunca conclua a partir de `php -l` ou do PHP CLI, porque o pool FPM é o runtime real. Se um cliente HTTP genérico receber `403` enquanto checksum deployado e diretórios de estado estão íntegros, repita com User-Agent de navegador e abra a URL em navegador real antes de mudar o handler; isso separa bloqueio de edge/WAF da resposta efetiva do PHP.

## Recuperação e auditoria

- Após erro ou timeout, leia pending/completed e o estado externo antes de repetir; nunca reinicie o login ou a troca de código às cegas.
- A tela da Meta pode declarar o Business Portfolio conectado antes de o operador clicar em **Finish**, enquanto o Authorization Code já está envelhecendo. Para a tentativa real, arme antes um watcher foreground de uso único que detecte a callback, troque o código imediatamente, grave o token no cofre e finalize; não dependa de uma mensagem humana posterior para iniciar a troca.
- Se a callback rejeitar por `state` expirado, compare somente o SHA-256 do state retornado com o pending esperado e confirme se completed está ausente antes de reprocessar a camada. Se a Meta responder `code=100/subcode=36007` ou indicar código expirado/usado, não repita a troca: remova o código bruto preservando apenas hash e metadata segura, gere state/request novos e refaça a autorização com o watcher já ativo.
- Apague somente artefatos sintéticos do autoteste; preserve audit do request real sem segredos.
- Mudança de script/callback exige lint, teste HTTP real, checksum/readback do deploy, inventário e REPORT-INFRA.
- A conclusão exige token no cofre, identidade e `client_business_id` reconciliados e acesso read-only aos ativos exatos; callback online sozinha não significa onboarding concluído.

## Fonte oficial

- Meta, Facebook Login for Business: https://developers.facebook.com/documentation/facebook-login/facebook-login-for-business
