# Meta Ads MCP Server — avaliação operacional MGS (2026-07-17)

## Fontes oficiais consultadas

- Meta Developer Docs — Ads MCP Server overview: `https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-overview`
- Meta Developer Docs — Get started: `https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-get-started`
- Meta Developer Docs — Ad creation and management: `https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-tools-ad-creation-and-management`
- Meta Business Help Center — Manage ads from an AI agent with Meta ads AI connectors: `https://www.facebook.com/business/help/1456422242197840`
- Hermes docs — MCP integration: `https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp`

As páginas da Meta estavam marcadas como atualizadas em 2026-07-14.

## Fatos confirmados

- Endpoint remoto hospedado pela Meta: `https://mcp.facebook.com/ads`.
- Funciona com agentes compatíveis com MCP; app Meta próprio não é pré-requisito.
- Para app próprio, adicionar o use case `Create & manage ads with ads MCP server`.
- Autenticação por OAuth/Facebook Login for Business ou user access token.
- Permissões documentadas para token: `ads_mcp_management`, `ads_read`, `ads_management`, `catalog_management`, `business_management`, `pages_show_list`, `instagram_basic`.
- O MCP expõe ferramentas permission-scoped; não concede ativos ou privilégios novos.
- Ferramentas de descoberta incluem:
  - `ads_get_ad_accounts`: contas acessíveis ao usuário;
  - `ads_get_ad_account_pages`: páginas já usadas numa conta;
  - `ads_get_pages_for_business`: páginas pertencentes ao Business;
  - `ads_get_user_pages`: páginas utilizáveis pelo usuário para publicidade.
- Ferramentas de write criam campanha, ad set e ad em estado pausado. A ativação é uma ação separada (`ads_activate_entity`) e inicia gasto.
- O Business Suite pode permitir/bloquear capacidades por conta/catálogo, inclusive criação de campanha e mudanças de orçamento, com limite máximo de budget.
- Hermes suporta servidores MCP HTTP remotos, OAuth, cliente OAuth pré-registrado e filtro de ferramentas.

## Interpretação operacional

### O que o MCP não deve ser apresentado como

Não tratar o MCP como bypass ou substituto para:

- App Review / Advanced Access;
- Business Verification;
- autenticação ou checkpoint do usuário;
- restrições da conta de anúncios;
- permissões do usuário no Business Manager;
- ownership/vínculo/permissão real de Page.

Ele ajuda a **descobrir e diagnosticar** contas/Páginas visíveis, mas não verifica, libera ou concede acesso. Se um ativo não aparece, reconciliar usuário, Business, Page, conta e permissões nas fontes reais.

### Valor para Ares

Relevância alta para inventário, reporting, campanhas e diagnóstico. O MCP reduz wiring manual de endpoints e oferece guardrails nativos, mas não deve substituir a rota Graph/API existente sem piloto e comparação de readback.

O fato de o servidor ser hospedado pela Meta torna-o uma rota de isolamento interessante para falhas específicas observadas no `POST /ads` (`code=31` / checkpoint). Porém, a documentação não promete que o MCP contorne esse bloqueio. Somente um write pausado controlado pode confirmar se o MCP reproduz ou atravessa a mesma fronteira.

## Piloto recomendado

1. Usar app pertencente e controlado pela MGS; não depender de app de terceiro para ativos de produção.
2. Conectar uma única conta por OAuth.
3. Começar com ferramentas read-only e filtrar tools mutantes no cliente MCP.
4. Comparar contas, Páginas, campanhas e métricas com Graph API/readback atual.
5. Testar criação de campanha/ad set/ad em `PAUSED`, com budget mínimo e escopo autorizado.
6. Não chamar ativação durante o piloto.
7. Verificar via GET/UI os objetos criados e limpar parciais conforme o safety model da skill.
8. Comparar a fronteira do `POST /ads` com a rota atual; reportar sem inferir bypass de verificação.

## Pitfalls

- Uma mensagem de convite recebida por um app específico não prova acesso para todos os apps MGS; validar o use case no app escolhido.
- Não confundir “listar Páginas acessíveis” com “verificar/liberar Páginas”.
- Não conectar ativos MGS por OAuth de app pertencente a amigo/fornecedor sem ownership e controle institucional da MGS.
- Não habilitar todas as tools por conveniência: no Hermes, usar filtro por servidor e liberar mutações gradualmente.
