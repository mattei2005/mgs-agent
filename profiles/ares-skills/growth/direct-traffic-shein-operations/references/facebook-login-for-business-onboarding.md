# Onboarding Facebook Login for Business — SHEIN

Use este playbook para emitir um User Access Token por perfil anunciante usando o app corporativo aprovado, sem expor segredo e sem conceder papel técnico desnecessário.

## Gate inicial — não mudar produção às cegas

O app `minibot` possui consumidores ativos. Antes de clicar em **Switch to Facebook Login for Business**, faça inventário read-only de:

- App type e App mode;
- business portfolio conectado;
- produtos atuais;
- permissões Advanced/Full Access;
- Redirect URIs, Deauthorize Callback e Data Deletion URL;
- tokens/consumidores ativos.

Se a tela mostrar apenas um convite para **Switch**, pare e faça plano/canário. A Meta documenta mudanças potenciais de tipo/permissões e rollback limitado a 30 dias. Se o produto já existir no app Business, prossiga sem converter outro produto.

Conclusão: o estado atual do app foi registrado e nenhum consumidor ativo foi alterado.

## 1. Preparar URLs técnicas

Antes da configuração, definir três endpoints HTTPS reais:

```text
Redirect URI              recebe o retorno do login e valida state/code
Deauthorize Callback URL  recebe remoção/desautorização do app
Data Deletion Request URL atende solicitação de exclusão de dados
```

Nunca inventar URLs nem usar página WordPress pública como callback improvisado. O Redirect URI precisa corresponder exatamente ao valor cadastrado no App Dashboard.

Conclusão: os três endpoints respondem corretamente e o Redirect URI passa no **Check URI**.

## 2. Abrir o app correto

1. Entrar em `developers.facebook.com/apps` com uma conta administradora autorizada.
2. Selecionar o app corporativo `minibot`.
3. Confirmar visualmente App ID/nome e business portfolio, sem copiar App Secret.
4. Abrir **Facebook Login for Business** no menu.
5. Se o produto não existir e o app já for Business, usar **Add product**; se aparecer apenas **Get started/Switch**, parar no gate inicial.

Conclusão: a sessão está no app correto e nenhuma credencial foi revelada.

## 3. Configurar OAuth

Em **Facebook Login for Business → Settings**:

1. Adicionar o Redirect URI HTTPS real.
2. Clicar em **Check URI** e exigir sucesso.
3. Habilitar o fluxo Web OAuth necessário pela integração.
4. Adicionar Deauthorize Callback URL.
5. Adicionar Data Deletion Request URL.
6. Salvar e reler os valores.

Não ativar **Require App Secret** ou `appsecret_proof` globalmente sem confirmar que todos os consumidores atuais suportam essa mudança.

Conclusão: Settings tem readback dos endpoints exatos e nenhum consumidor legado foi quebrado.

## 4. Criar a configuração SHEIN

Em **Facebook Login for Business → Configurations**:

1. Clicar em **Create configuration**.
2. Nome sugerido: `MGS SHEIN Advertiser User v1`.
3. Login variation: `General`, salvo exigência específica validada.
4. Access token: **User access token**.
5. Assets: selecionar **Ad accounts** e **Pages**; marcar como requeridos apenas quando a campanha depende deles.
6. Permissions mínimas para criação de anúncios:
   - `ads_management`
   - `ads_read`
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_ads`
7. Adicionar `business_management` somente quando o onboarding realmente precisar enumerar/validar assets do portfolio.
8. Criar e registrar o Configuration ID como metadata não secreta.

Nunca selecionar System-user access token por semelhança. Essa arquitetura permanece User Access Token enquanto Rodolfo não aprovar outra.

Conclusão: configuração criada com tipo, assets e permissões exatos.

## 5. Implementar a página de login

O dashboard gera apenas a configuração; ainda é necessário um endpoint/app web para invocar o login.

1. Criar uma página interna HTTPS com botão **Conectar perfil Meta**.
2. Invocar o login com o `config_id` da configuração; não misturar scopes divergentes.
3. Gerar e validar `state` anti-CSRF por tentativa.
4. Preferir Authorization Code quando suportado, para não expor token no browser.
5. No callback, validar `state`, origem e código antes de qualquer troca.
6. Trocar o código server-to-server; App Secret nunca entra no cliente, URL, Discord ou log.
7. Gravar o token diretamente no destino seguro ou em variável transitória protegida.

Conclusão: um login de teste retorna identidade esperada sem token em logs/histórico.

## 6. Autorizar cada perfil anunciante

Repetir em sessão/browser isolado para cada perfil:

```text
G001  Aline Rosse
G002  Pasgal ID
G003  Aline Nunes
G004  Ingrid Costa
G005  Arruda Arruda
G006  Manuela Carvalho
```

1. Sair do perfil anterior ou usar um profile de navegador isolado.
2. Entrar no Facebook com o perfil exato.
3. Abrir a página interna de conexão.
4. Conceder somente as permissões e assets esperados.
5. Confirmar que a conta/Page selecionadas pertencem ao gestor correto.
6. Nunca reutilizar o token de um perfil em outro canal.

Conclusão: seis autorizações produzem seis identidades distintas e account scopes corretos.

## 7. Armazenar no 1Password

Criar um item por token:

```text
Meta User Access Token - SHEIN G001 - Aline Rosse
Meta User Access Token - SHEIN G002 - Pasgal ID
Meta User Access Token - SHEIN G003 - Aline Nunes
Meta User Access Token - SHEIN G004 - Ingrid Costa
Meta User Access Token - SHEIN G005 - Arruda Arruda
Meta User Access Token - SHEIN G006 - Manuela Carvalho
```

Guardar no item: token em campo secreto, perfil, gestor, app, issued/expires, scopes e observação operacional. Informar ao Ares somente o nome do item; nunca colar o valor no Discord.

Conclusão: seis referências existem e nenhum token aparece fora do cofre.

## 8. Readback técnico obrigatório

Para cada item, Ares valida sem imprimir segredo:

- `/debug_token`: app, user ID, validade, issued/expires e scopes;
- `/me`: identidade do perfil;
- contas acessíveis e GET da conta selecionada;
- nome, moeda, timezone, status/saúde e business da conta;
- Pages acessíveis quando usadas em criativos;
- `ads_management` e `ads_read` presentes;
- tier e headers `X-Ad-Account-Usage`, `X-Business-Use-Case-Usage`, `X-App-Usage`/Insights quando retornados.

Falha de qualquer item bloqueia somente o alias dependente. Nunca testar validade criando campanha.

Conclusão: cada alias fica `READ_ONLY_VALIDATED`; write só é habilitado no primeiro pedido autorizado.

## 9. Alternativa manual temporária

Se a página OAuth ainda não existir:

1. No mesmo app, usar papel de menor privilégio `Tester`/`Authorized App Tester`.
2. Meta Developer Account só é obrigatória para Administrator, Developer ou Analytics; não conceder Developer para obter token.
3. Se o Graph API Explorer exigir registro em `developers.facebook.com`, registrar o perfil existente, mantendo Tester.
4. Gerar token pelo Quickstart/Explorer apenas como ponte temporária.
5. Converter/renovar conforme validade oferecida e migrar para o fluxo corporativo.

Conclusão: o fallback não altera app ownership nem vira arquitetura permanente.

## Verificação final

- [ ] app e business corretos
- [ ] nenhum switch de produto sem canário
- [ ] três endpoints HTTPS reais
- [ ] configuração User Access Token
- [ ] assets e permissões mínimas
- [ ] seis identidades distintas
- [ ] seis itens 1Password
- [ ] identidade/scopes/expiry/contas validados
- [ ] zero token em chat/log/URL
- [ ] zero campanha criada durante onboarding
