# Pesquisa técnica — Meta Marketing API code 31 / subcode 3858385

## Conclusão executiva

A hipótese de localização da VPS deve ser retirada. A documentação oficial da Meta diz que a maioria dos access tokens é portátil entre navegador, cliente e servidor.[6] A mensagem sobre “login location” é texto genérico do checkpoint, não prova de que o IP da VPS causou o bloqueio.

O caso da operação corresponde a dois fenômenos que precisam ser separados:

1. **Checkpoint real de autenticação do anunciante (#3858385).** Em muitos casos, o botão **Start Authentication** só aparece depois de editar/criar um anúncio e tentar publicá-lo. O fluxo envia código ao e-mail ou telefone conectado ao perfil.[4][9][10]
2. **Variante API-only sem ação visível.** Existem ao menos duas threads no próprio Meta Developer Community com `code=31`, `subcode=3858385`, anúncios existentes normais, criação via API bloqueada e nenhuma ação pendente visível no Ads Manager. As threads continuam marcadas como não resolvidas e apontam para o bug report `3397941523702775`.[1][2][3]

A cronologia da operação favorece o checkpoint de autenticação, não falta de payload: o mesmo token/app conseguiu criar e ler um anúncio PAUSED; o `31/3858385` apareceu somente depois, nas tentativas seguintes. Os testes `validate_only` com criativo fonte ativo e criativo sanitizado retornam o mesmo bloqueio, portanto o payload criativo não é a causa imediata.

## Evidência local validada

- Token `USER`, válido, app `minibot rod`, Graph v26.0.
- Scopes exigidos presentes.
- Conta ativa; Página Garagem Brasil em `/me/accounts`; task `ADVERTISE` presente.
- Um anúncio PAUSED real foi criado e lido antes do checkpoint.
- Depois do checkpoint, dois `validate_only` diferentes retornaram o mesmo `code=31/subcode=3858385`, sem write.
- Header BUC atual indica `ads_api_access_tier=development_access`.

## O que a pesquisa externa mostrou

### 1. O erro é específico de autenticação do anunciante

Jon Loomer documentou a mesma mensagem `#3858385`: o Ads Manager mostra um painel “Verifying your changes” com o botão **Start Authentication**; o usuário escolhe **Send Email**, recebe um código e o envia.[4]

Em uma thread extensa do Reddit, a solução mais repetida foi editar o texto de um anúncio e publicar; isso fez o botão de autenticação aparecer. Outros usuários precisaram criar um anúncio/campanha novo para fazer o prompt surgir.[9] Outra thread relata o botão no topo direito ao entrar no nível de anúncio; há também casos resolvidos por suporte ou pela correção do e-mail/telefone no Accounts Center.[10]

### 2. Existe uma variante API-only aparentemente bugada

Uma thread oficial descreve exatamente: Marketing API falha com `31/3858385`, anúncios existentes continuam, Data Access Renewal já foi concluída e não aparece qualquer ação de segurança no Ads Manager.[1] Outra thread oficial repete “checked my whole ads account page and there is no error”, está marcada `Unresolved` e aponta ao mesmo bug report.[2][3]

Isso não prova que a Meta já reconheceu formalmente a causa; prova que o caso não é isolado e que há um bug report público correspondente.

### 3. Localização da VPS não é uma explicação suficiente

A Meta afirma oficialmente que “Most access tokens are portable” e podem ser usados em navegador ou servidor.[6] Usuários também relatam o mesmo erro sem viagem ou mudança de localização.[10] Portanto, o IP da VPS não deve orientar a correção.

### 4. System User não é obrigatório para o modelo MGS

A documentação oficial distingue:

- **User Access Token:** herda o acesso atual do usuário e pode alcançar os mesmos business assets que ele já acessa.[7]
- **Business Integration System User Token:** recebe assets explicitamente delegados e é associado ao business portfolio do cliente.[7]
- **System User clássico:** endpoints verificam se o system user tem acesso ao recurso; assets precisam ser owned ou shared com o business portfolio.[6]

Assim, Rodolfo está correto: System User funciona, mas introduz onboarding de business portfolio/asset sharing. Não é a única arquitetura. O modelo de User Token é oficialmente suportado e combina melhor com muitos perfis/Páginas externos, desde que o app tenha o nível de acesso adequado.[5][7][11]

## Configuração do app que ainda precisa ser conferida

A documentação atual renomeou o Marketing API tier: `Standard Access → Limited Access` e `Advanced Access → Full Access`.[5]

O header live do app informa `development_access`, equivalente operacional ao tier limitado/desenvolvimento. A documentação diz:

- Limited Access é para desenvolvimento, não para produção com live advertisers;
- app admins/developers podem chamar a API em nome de ad account admins/advertisers;
- Full Access é obtido após App Review;
- `ads_management` standard access basta para o próprio ad account; para contas de terceiros, é preciso advanced access.[5]

Como um anúncio real já foi criado antes do checkpoint, isso não explica sozinho o `3858385`; mesmo assim, é obrigatório conferir:

1. App Dashboard → App Review → Permissions and Features.
2. Marketing API Access Tier: Limited ou Full.
3. `ads_management`, `ads_read`, `business_management`, `pages_manage_ads`: standard ou advanced.
4. App Roles: Rafael está como Admin/Developer/Tester se o app estiver em Limited Access.

## Plano recomendado

### Passo 1 — disparar o prompt correto no Ads Manager

No nível de **anúncio**, fazer uma alteração mínima em um draft isolado e tentar publicar esse único anúncio/campanha como PAUSED. Não publicar as outras mudanças pendentes. Procurar o painel **Verifying your changes → Start Authentication** no topo direito. Concluir o código por e-mail/telefone.[4][9][10]

Se o botão não surgir, criar um único anúncio manual PAUSED de teste e tentar publicar; múltiplos usuários relataram que esse caminho fez a autenticação aparecer.[9]

### Passo 2 — reteste da API

Depois do código, rodar somente `validate_only` Graph v26.0. Se retornar `success=true`, concluir o 1×1×3 PAUSED. Se continuar `31/3858385`, não repetir writes.

### Passo 3 — variante bugada

Se não houver botão ou se o código não limpar a API:

- anexar o JSON sanitizado ao bug report `3397941523702775`;
- abrir Meta Support citando as duas threads oficiais;
- anexar horário, endpoint, app ID, ad account ID e `fbtrace_id`, sem token.[1][2][3]

### Passo 4 — app access audit

Em paralelo, conferir tier/permissões/app role. Se o app estiver Limited Access e Rafael não for App Admin/Developer/Tester, corrigir a role para o piloto. Para produção em escala com perfis externos, avaliar Full Access + Facebook Login for Business User Access Tokens, sem migrar todas as Pages para uma única BM.[5][7]

## O que não recomendo agora

- Não trocar para Playwright.
- Não usar proxy/residential egress.
- Não alterar novamente payload, compliance, criativos ou UTMs.
- Não migrar tudo para System User antes de testar o fluxo de autenticação e auditar tier/roles.
- Não repetir writes via API enquanto `validate_only` continuar bloqueado.

## Sources

[1] https://developers.facebook.com/community/threads/845129991936233 — Meta Community - Marketing API error 31/subcode 3858385
[2] https://developers.facebook.com/community/threads/1820634641959662 — Meta Community - no Ads Manager error, code31/3858385
[3] https://developers.facebook.com/support/bugs/3397941523702775 — Meta Bug Report 3397941523702775
[4] https://www.jonloomer.com/chatgpt-ads-missing-audience-segments-account-authentication-errors — Jon Loomer - Account Authentication Error 3858385
[5] https://developers.facebook.com/documentation/ads-commerce/marketing-api/get-started/authorization — Meta Marketing API Authorization
[6] https://developers.facebook.com/docs/facebook-login/guides/access-tokens — Meta Access Tokens
[7] https://developers.facebook.com/documentation/facebook-login/facebook-login-for-business — Facebook Login for Business
[9] https://www.reddit.com/r/FacebookAds/comments/1glm58s/unable_to_publish_ads_error_3858385 — Reddit - Unable to Publish Ads 3858385
[10] https://www.reddit.com/r/FacebookAds/comments/1gaj7hq/need_help_asap — Reddit - Need Help ASAP 3858385
[11] https://www.facebook.com/business/help/708679622611131 — Meta Business Help - Add Partners
