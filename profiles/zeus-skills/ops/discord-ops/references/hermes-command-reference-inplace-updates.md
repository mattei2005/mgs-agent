# Atualizar referências de comandos Hermes no Discord

Use quando Rodolfo pedir a atualização de uma thread existente que documenta os comandos do Hermes.

1. Leia a skill Hermes e sua referência de slash commands. Se a skill estiver desabilitada, leia os arquivos diretamente sem habilitá-la nem alterar configuração.
2. Consulte a documentação oficial atual e o `COMMAND_REGISTRY` da instalação realmente usada pelo gateway. Diferencie slash commands de subcomandos do shell: `/version` não significa `hermes version`; use a interface documentada para consultar a versão.
3. Resolva os gates do profile ativo e examine os handlers quando documentação e registro divergirem. Separe CLI/TUI, gateway, Telegram-only, DM-only e comandos condicionais. Presença no registro não prova configuração ativa nem autoriza execução de comandos sensíveis.
4. Leia a thread completa pela API com paginação, dedupe por ID e preserve o snapshot com autoria, tipo, conteúdo e metadados. Mensagens de sistema não são partes editáveis da referência. Confirme que os posts a editar pertencem ao bot autenticado; a API não permite editar conteúdo de outro autor.
5. Construa a referência completa em PT-BR, com nomes e aliases exatos. Conte nativos, aliases e cobertura por código; não reutilize totais históricos. Use regex limitada a nomes para evitar capturar a crase final como parte do comando.
6. Reduza os campos antes de transferir dados de ferramentas para outro parser. Outputs de terminal podem ser truncados; texto de read_file pode incluir números de linha. Não JSON-decode um dump grande/truncado ou numerado. Transporte apenas nomes, aliases e IDs quando isso bastar e mantenha o snapshot completo no disco.
7. Redistribua o conteúdo entre as mensagens existentes respeitando 2.000 caracteres por mensagem. Preserve IDs, ordem, título existente, reply references e mensagens de sistema. Não apague/reposte ou crie mensagens duplicadas para uma tarefa de edição.
8. Antes do PATCH, releia todos os alvos e aborte se autoria/conteúdo divergir do snapshot. Faça backup privado dos conteúdos anteriores e do payload; nunca inclua tokens.
9. Edite por REST autenticado quando a ferramenta Discord não oferecer edição. Defina `content`, `embeds` e `allowed_mentions` explicitamente; não habilite mentions. Respeite `retry_after` e reconcilie resultado ambíguo por GET antes de repetir a escrita.
10. Faça GET de cada ID após a escrita, compare conteúdo exatamente e revalide o conjunto completo, totais, IDs preservados e ausência de novas mensagens/exclusões. Registre recibo e audit e entregue o link da thread com um resumo do que mudou.

Atualizar a documentação não autoriza executar os comandos descritos, mudar configurações, habilitar gates, alterar credenciais/billing ou reiniciar gateways.
