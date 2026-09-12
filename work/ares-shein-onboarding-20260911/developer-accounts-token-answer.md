Resposta curta: você precisa de um User Access Token separado para cada um dos seis perfis anunciantes, mas não precisa obrigatoriamente criar uma Meta Developer Account para todos nem criar seis apps.

O app corporativo minibot já está aprovado localmente como Tech Provider e Marketing API Full Access. A Meta documenta que permissões com Advanced Access podem ser solicitadas de qualquer app user, enquanto Standard Access fica restrito a usuários com papel no app.[4] O Facebook Login for Business é a solução preferida para autorização em integrações com ferramentas empresariais e suporta User Access Tokens.[5]

Se você usar a rota manual por App Roles, não dê Developer por padrão. A Meta exige Meta Developer Account para Administrator, Developer ou Analytics, mas permite convidar usuários regulares como Tester; Authorized App Testers também podem aceitar convite e conceder permissões durante desenvolvimento.[6] Se a superfície Graph API Explorer exigir registro de developer, registre o perfil existente, mas mantenha o papel mínimo necessário.

Para campanhas, cada perfil deve autorizar `ads_management` e `ads_read`; outras permissões só entram quando a conta/Page exigir e o preflight comprovar.[3] Cada token vai para um item separado do 1Password e nunca para o Discord.

A afirmação do Felipe continua parcialmente correta: tokens de usuários distintos isolam a contagem por usuário do Graph API, mas a Marketing API também limita por conta, app, Business Use Case, access tier, burst e objeto.[1][2]

## Sources

[1] https://developers.facebook.com/docs/graph-api/overview/rate-limiting — Rate Limits - Graph API - Meta for Developers
[2] https://developers.facebook.com/documentation/ads-commerce/marketing-api/overview/rate-limiting — Marketing API Rate Limiting - Meta for Developers
[3] https://developers.facebook.com/docs/marketing-api/get-started/authorization — Marketing API Authorization - Meta for Developers
[4] https://developers.facebook.com/docs/graph-api/overview/access-levels — Graph API Access Levels - Meta for Developers
[5] https://developers.facebook.com/docs/facebook-login/facebook-login-for-business — Facebook Login for Business - Meta for Developers
[6] https://developers.facebook.com/docs/development/build-and-test/app-roles — App Roles - Meta for Developers
