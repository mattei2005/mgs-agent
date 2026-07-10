## Política global — 1Password e Credenciais

- Service account: **APENAS LEITURA** no vault "MGS Conteúdo" (`op item get` e `op item list` apenas)
- NUNCA alterar credenciais de produção sem autorização explícita do Rodolfo
- Toda ação que modifica estado: validar ANTES de reportar sucesso
- NUNCA alucinar sucesso após erro — sempre reconhecer e reportar erros literais

---

## Referência — MGS Chat Funnels top ad/rewarded

Para chats standalone baseados no HTML Ciro/JBF, ver `references/mgs-chat-funnels-top-ad-scroll-and-rewarded-count.md`: rewarded preload padrão = 1 chamada; top ad dentro do chat exige auto-scroll/pin-to-bottom para manter os botões visíveis; validar runtime com `nearBottom=0`, `loop5=0` e helper sem recursão.
