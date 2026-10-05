# CarCreditAd — escopo aprovado por Rodolfo

Fonte: Discord thread 1551768281688580096, mensagem 1556493106868649996, Rodolfo Mattei (344196393512075265).

## Decisões ativas para esta operação

- 1: corrigir a URL /es/home-espanol/ em erro, preservando a home funcional https://carcreditad.com/es/; preferência por correção da função duplicada sem mudar rotas, conteúdo ou indexação.
- 2: criar backup integral de filesystem e banco, com restauração isolada comprovada antes de correções. Preservar backup e restore; nenhuma exclusão autorizada.
- 3: Rodolfo perguntou se bastam atualizações de plugins. Responder com compatibilidade/backup/testes; não interpretar pergunta como autorização independente de atualização.
- 4: não adicionar banner ou alterar consentimento/tracking. Rodolfo informa que SB/GAM insere o controle automaticamente; isso é declaração do dono, não certificação técnica do mecanismo. Preservar runtime.
- 5: corrigir o rodapé jurídico alheio, mantendo identidade CarCreditAd e sem alegações empresariais/financeiras não verificadas.
- 6: corrigir grandes vazios e cards invisíveis. Preservar anúncio, identificadores de slots, scripts, rotas, tracking, conteúdo e destinos.
- 7: corrigir referência da imagem, acessibilidade, overflow e localização/apresentação do formulário. Não introduzir CAPTCHA, banner, política de consentimento ou submissão real de lead sem escopo separado.
- 8: conferir Imagify, ativação, configuração não secreta e evidência de otimização. Não iniciar bulk/recompressão nem contratar quota.
- 9: não alterar metadados SEO, títulos ou links editoriais; Rodolfo tratará com redatora. Exceção única: correção técnica da URL em erro do ponto 1, sem mudar indexação.
- 10: não alterar usuários, 2FA, credenciais, editores ou permissões; usuários configurarão 2FA ao fazer login.
- 11: autorizado reiniciar o que estiver pendente. Reboot do VPS continua Critical Subset e exige confirmação adicional com host, kernel e impacto vivos; não atualizar pacotes, PHP, grants ou firewall por implicação.
- 12: preservar Cloudflare SSL Full; não mudar para Strict ou alterar origem/firewall.
- 13: conferir acesso Search Console concedido à Service Account corporativa pelo dono; somente leitura e nenhuma submissão manual.
- 14: explicar readme.html e license.txt na raiz do WordPress; não excluir ou restringir sem autorização.

## Limites

Site: carcreditad.com. Binding previamente auditado: MatteiInc02 162.55.28.179, RunCloud servidor 288158, webapp 2735760, /home/runcloud2/webapps/carcreditad; revalidar home no live antes de operar.

Não há autorização para editar outros sites, credenciais, /etc /usr /boot, firewall, orçamento, instalar serviços ou apagar arquivos/bancos. Backup/restore isolados ficam privados fora do webroot, sem novos usuários ou grants. Produção editorial permanece fora da execução Zeus; o rodapé é configuração técnica do tema autorizada diretamente.
