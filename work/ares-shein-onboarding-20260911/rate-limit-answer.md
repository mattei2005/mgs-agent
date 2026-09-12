A afirmação do Felipe é parcialmente correta.[1][2] Chamadas Graph API feitas com User Access Token entram na contagem do usuário, em janela móvel de uma hora; portanto tokens de usuários realmente distintos separam essa camada.[1]

A Marketing API não limita apenas por token: a Meta também aplica quotas por conta de anúncios e Business Use Case, calculadas conforme o app e o Marketing API Access Tier.[1][2] Mutações têm ainda limite por combinação app+conta, e edições concorrentes podem ser limitadas por objeto+app.[2]

Assim, um perfil anunciante e token por gestor é uma boa arquitetura de isolamento de credencial e de quota por usuário, mas não cria seis quotas independentes quando app, conta ou objeto forem compartilhados e nunca deve ser usado como bypass de throttling.[1][2]

## Sources

[1] https://developers.facebook.com/docs/graph-api/overview/rate-limiting — Rate Limits - Graph API - Meta for Developers
[2] https://developers.facebook.com/documentation/ads-commerce/marketing-api/overview/rate-limiting — Marketing API Rate Limiting - Meta for Developers
