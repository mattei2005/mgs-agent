## Correção aprendida com playbook externo de clone

Rodolfo trouxe um playbook de outro agente para criação/clonagem Meta. A diferença crítica contra a primeira implementação local é:

```text
Rota antiga local                | Rota correta para Messenger/replacement
---------------------------------|------------------------------------------------
Reaproveitar object_story_spec bruto | Não usar object_story_spec bruto de campanha antiga
Reaproveitar asset_feed_spec bruto   | Recriar creative a partir de video_id ou image_hash
Fallback com creative_id legado      | Evitar como rota padrão, especialmente cross-page
Graph v20.0                          | Preferir v25.0 para o fluxo de criação se validado
Recriar messenger_doc como link      | Não usar messenger_doc como destino externo
```

Para `clone-source` na mesma página:
1. Ler ads ativos da source.
2. Extrair `video_id` para vídeos ou `image_hash` para imagens.
3. Criar novos adcreatives com `object_story_spec` mínimo contendo `page_id` e asset (`video_data.video_id` ou `link_data.image_hash` quando aplicável), mais `degrees_of_freedom_spec` e `page_welcome_message` seguro.
4. Em Messenger, `page_welcome_message` deve usar `is_user_editing=true` e não enviar `template_id` nem `template_version`.
5. Não enviar `standard_enhancements`.
6. Exigir 3 ads utilizáveis; se criar menos de 3, arquivar/deletar a campanha parcial.

Read-only em 2026-06-18 confirmou que os 3 creatives winners atuais possuem `asset_feed_spec.videos` com `video_id` disponível, então há insumo para trocar o script para uma rota baseada em `video_id`, não em `messenger_doc`/creative bruto. Auditoria: `/root/mgs-agent/data/ares/meta-ads/audit/clone/creative-asset-inspect-readonly.json`.

Tentativa controlada posterior criou com sucesso campanha PAUSED, adset PAUSED e adcreative novo usando `video_id + image_url` de thumbnail, sem `messenger_doc`. O bloqueio remanescente ficou no `POST /ads`: `code=31/subcode=3858385`. Ou seja, a rota de criativo foi corrigida; a camada de criação do ad via API continua bloqueada para o token/app atual. Auditoria principal: `/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-videoid-failed-20260618T044855Z.json`. Campanha parcial `120248892823990604` foi marcada `DELETED` e verificada via GET.
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
## Comunicação com Rodolfo em troubleshooting Meta

Se Rodolfo disser que não entendeu por estar técnico demais, reduzir imediatamente para linguagem operacional:

```text
Pergunta executiva                 | Resposta curta esperada
-----------------------------------|------------------------------------------------------------
O token funciona?                   | Sim/não, com /me e conta como evidência
O que a Meta deixou fazer?          | Campanha/adset/creative/ad em passos simples
Onde travou?                        | Nome humano da trava, não só código/subcode
O que precisa fazer agora?          | Ação humana específica no Ads Manager ou permissão da Página
```

Use códigos (`31/3858385`, `1487202`, `1815199`, `190`) como evidência curta em tabela depois da explicação simples. Não liderar com `object_story_spec`, `standard_enhancements`, Graph payloads ou async session salvo se Rodolfo pedir detalhe técnico.
## Preferência operacional do Rodolfo para testes de clone

Quando Rodolfo disser `continue`, `continue os testes` ou equivalente, não responder com plano longo nem narrar cada microteste. Executar a sequência controlada em silêncio, sempre com objetos `PAUSED`, cleanup e audit, e reportar só quando houver resultado útil: rota que passou, bloqueio novo, evidência objetiva ou decisão necessária. Se a pergunta vier junto de uma dúvida operacional, responder a dúvida em ordem e continuar a execução sem transformar isso em loop de confirmação.
