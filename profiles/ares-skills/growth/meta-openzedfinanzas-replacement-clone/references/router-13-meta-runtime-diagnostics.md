## Diagnóstico token/app, página alternativa e camada `POST /ads`

Quando Rodolfo trocar VPS/IP, renovar token, pedir "teste novamente" ou perguntar se outra página/campanha da conta pode ser usada, não assumir que a camada bloqueada é a mesma da tentativa anterior. Rodar uma validação em camadas:

```text
Camada                 | Decisão operacional
-----------------------|------------------------------------------------------------
Token 1Password         | Reportar só item/campo/len; nunca imprimir valor
Mapa páginas/campanhas  | Listar campaigns/adsets/page_id antes de concluir bloqueio global
GET source campaign     | Se falhar, parar antes de writes
Create campaign/adset   | Só se GET source estiver OK; página alternativa pode passar adset
Create creative         | Validar `video_id`/`image_hash`; testar sem IG se houver erro de Instagram asset
POST /ads               | Isolar final layer; code=31/subcode=3858385 exige autenticação Ads Manager
Cleanup                 | Deletar/verificar campanha temporária se qualquer write ocorreu
```

Interpretação validada:
- `code=31/subcode=3858385` em `POST /ads`: a rota de campanha/adset/creative pode estar correta; a trava está na criação/modificação de anúncio pela conta/app/usuário.
- `code=190` com `Error validating application. Application has been deleted.` já no primeiro GET: token/app inválido ou app deletado. Corrigir app/token antes de novo clone; mudança de VPS/IP não resolve essa camada.
- `code=100/subcode=1487202` em `create_adset` com título de permissão de Página insuficiente: token/user não tem acesso para anunciar naquela Página; testar outra página da conta pode isolar se o bloqueio é local à Página.
- `code=200/subcode=1815199` em `create_adcreative` com erro de Instagram asset: retestar com `--omit-instagram-user-id` para criar creative page-only e separar erro de IG do bloqueio final.
- Se o clone completo estiver lento por backoff/rate-limit de crons Meta concorrentes, usar um probe focado sem backoff longo para separar token/app vs `POST /ads`, mas manter cleanup/verificação obrigatórios.

Detalhe de sessão e receita do probe: `references/token-app-validation-and-post-ads-retest-2026-06-18.md`.
Detalhe do reteste em outra página e flag `--omit-instagram-user-id`: `references/retest-other-page-and-omit-instagram-2026-06-18.md`.
Detalhe consolidado do token OK + página Elena + no-IG + bloqueio final em `POST /ads`: `references/page-permission-noig-post-ads-block-2026-06-18.md`.
