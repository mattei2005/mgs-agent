# Minibot — Marketing API Full Access

> App: `minibot` (`1299247318762949`)  
> Owner: Rodolfo Mattei  
> Status: ativo e validado em 2026-09-04  
> Estado estruturado: `data/ares/meta-ads/permissions/minibot-1299247318762949-full-access.json`

## Resumo executivo

O app recebeu **Marketing API Access Tier: Full Access**. O runtime das três contas operadas pelo Ares retornou `ads_api_access_tier=standard_access`, que é a prova operacional do tier.

A quota é medida por conta de anúncios dentro da combinação **conta + app**. O tier do app define o tamanho da quota:

```text
Limited / development_access   60 pontos, decay 300s, bloqueio 300s no máximo
Full / standard_access       9.000 pontos, decay 300s, bloqueio 60s no máximo
```

O ganho de capacidade é de 150 vezes. Isso melhora throughput de criação, clone, readback e recovery, mas não elimina QPS por conta/app, lock por objeto, CPU/tempo, revisão da Meta, restrições de Page ou erros de payload.

## Estado do app

- Tech Provider: aprovado.
- Marketing API Access Tier: Full Access.
- Header vivo: `standard_access` em CPV13, CPV05 e Eggbev.
- Permissões Advanced confirmadas por Rodolfo:
  - `ads_management`
  - `ads_read`
  - `business_management`
  - `pages_show_list`
  - `pages_read_engagement`
  - `pages_manage_ads`
  - `pages_manage_metadata`
  - `pages_messaging`
- `instagram_basic`: submetida e aguardando aprovação; sem impacto na quota/velocidade discutida.

Não existe outra permissão que aumente a quota acima do Full Access. Advanced Access amplia quais usuários e ativos podem autorizar o app, mas não aumenta o teto de 9.000.

## Validação executada

- Tokens de Roosevelt, Rafael e Carla válidos e vinculados ao app correto.
- `ads_read` e `ads_management` concedidas.
- Três contas HTTP 200 e `standard_access`.
- 14/14 rotas ativas read-only/dry-run aprovadas.
- 13 jobs Hermes verdes; monitor root Eggbev verde.
- Engine v3 validado em `from_zero_prestaged`, `pure_clone` e `clone_prestaged`.
- Simulações PAUSED concluíram `COMPLETE_PAUSED`.
- Zero Meta writes, zero campanhas ativas alteradas e zero budget alterado durante a validação.

## Comparação com o tier anterior

Exemplos históricos no `development_access`:

- CPV13, cinco campanhas/três bundles: cerca de 23m40s; até 15m15s eram cooldowns fixos.
- CPV05, três campanhas/dois bundles: cerca de 14m46s; até 10m10s eram cooldowns fixos.

A remoção do cooldown reduz fortemente o tempo potencial, mas o ganho real de write ainda deve ser medido por um canário Meta `PAUSED` separadamente autorizado.

## Manutenção do Full Access

A Meta exige ao menos 500 chamadas bem-sucedidas em 15 dias e erro abaixo de 15% nas últimas 500. Rodolfo confirmou que o token do `minibot` está conectado ao wrapper Smart Bidding, que consulta diariamente o investimento das contas, cobrindo o volume normal sem chamadas artificiais.

Monitorar tier vivo, taxa de erro, headers de utilização, Data Use Checkup e Ongoing Review.

## Itens que não aumentam velocidade

### Facebook Login for Business

É uma arquitetura opcional de onboarding e emissão de tokens. Não é necessária para os User Access Tokens atuais e não aumenta quota.

### `appsecret_proof`

É um parâmetro de segurança HMAC-SHA256, não uma permissão. Não aumenta quota. Não ativar **Require App Secret** antes de todos os consumidores suportarem o parâmetro, ou as chamadas atuais podem falhar.

### System User

Não é necessário para Full Access. A arquitetura aprovada continua usando User Access Tokens de perfis anunciantes até decisão separada de Rodolfo.

## Gates atuais

- Nenhum canário Meta real foi executado nesta validação.
- Qualquer canário deve ser um pedido separado, exato e `PAUSED`.
- O recovery antigo `pg_8348` permanece congelado e não deve ser misturado com o teste de Full Access.
- C004/C005 permanecem `PAUSED`, USD45 e sem conjuntos/anúncios; C006 permanece ausente; a lease só muda com autorização explícita de Rodolfo.

## Fontes oficiais Meta

- https://developers.facebook.com/docs/marketing-api/overview/rate-limiting/
- https://developers.facebook.com/docs/marketing-api/get-started/authorization/
- https://developers.facebook.com/docs/permissions/
- https://developers.facebook.com/docs/graph-api/overview/access-levels/
- https://developers.facebook.com/docs/development/release/access-verification/
- https://developers.facebook.com/docs/graph-api/guides/secure-requests/
- https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/
