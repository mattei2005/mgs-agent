## Princípios

1. **Comece pela operação piloto** — defina uma operação única (`VERTICAL_COUNTRY_LANG`, ex.: `CC_US_ES`) antes de generalizar.
2. **Estruture antes de conectar credenciais** — taxonomia, Drive, inventário e regras de decisão devem existir antes de API write.
3. **Read-only primeiro** — Meta Ads e Drive começam em leitura; write só em sandbox ou com aprovação explícita.
4. **Credenciais nunca no chat** — buscar via 1Password/vault e reportar apenas presença, item, len/status ou validações sem segredo.
5. **Ações em produção exigem aprovação explícita** — pausar, clonar, subir criativos, tracking/pixels, budget e billing seguem as regras MGS. Billing é critical subset/double-confirm.
6. **Automatizar o manual primeiro** — pergunte/registre como os gestores fazem corte, pausa, replacement e escala antes de propor melhoria.
