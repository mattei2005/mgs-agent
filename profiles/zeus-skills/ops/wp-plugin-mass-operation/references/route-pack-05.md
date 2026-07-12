## Política global — 1Password e Credenciais

- Service account: **APENAS LEITURA** no vault "MGS Conteúdo" (`op item get` e `op item list` apenas)
- NUNCA alterar credenciais de produção sem autorização explícita do Rodolfo
- Toda ação que modifica estado: validar ANTES de reportar sucesso
- NUNCA alucinar sucesso após erro — sempre reconhecer e reportar erros literais

### Auditoria de acesso WordPress

Quando Rodolfo perguntar a quais WordPress o agente tem ou não tem acesso:

1. Não responder somente pelo inventário documentado, por `data/sites.json` ou por memória.
2. Consultar ao vivo os itens `LOGIN` do vault `MGS Conteúdo` e considerar como credenciais canônicas de WordPress somente os títulos que começam com `Wordpress - `, com comparação sem diferenciar maiúsculas/minúsculas. Não inferir credencial canônica por URL, slug de login ou nomes legados fora desse prefixo.
3. Separar claramente:
   - credencial direta de WP-Admin/API no 1Password;
   - acesso técnico por SSH/WP-CLI;
   - acesso SFTP/read-only;
   - ausência real de qualquer rota operacional.
4. Fazer teste read-only da rota relevante antes de afirmar acesso atual: `wp core is-installed` via WP-CLI, `GET /wp-json/wp/v2/users/me` com application password ou login normal seguido de GET autenticado no admin.
5. Nunca imprimir usuário, senha, application password, token ou valor de campo; mostrar somente domínio, tipo de rota e resultado sanitizado.
6. A conclusão “sem acesso” exige cruzamento entre o 1Password ao vivo e todas as rotas técnicas conhecidas.

---

## Referência — MGS Chat Funnels top ad/rewarded

Para chats standalone baseados no HTML Ciro/JBF, ver `references/mgs-chat-funnels-top-ad-scroll-and-rewarded-count.md`: rewarded preload padrão = 1 chamada; top ad dentro do chat exige auto-scroll/pin-to-bottom para manter os botões visíveis; validar runtime com `nearBottom=0`, `loop5=0` e helper sem recursão.
