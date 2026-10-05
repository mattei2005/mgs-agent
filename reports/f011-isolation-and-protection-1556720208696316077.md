# F011 — isolamento5/6 aplicado; proteção7/8 validada

Origem: Rodolfo Mattei, discord:1551768281688580096#1556720208696316077.
Servidor MatteiInc02 / RunCloud288158 /162.55.28.179.
Decisão canônica: data/f011-apply-decision-1556720208696316077.json, sucessora explícita da decisão anterior no registry.

## Itens5/6 concluídos
- allAutolan_1770897973@localhost e datinghubpro_1773252658@localhost sem privilégios globais; permissões de aplicação preservadas exclusivamente no próprio schema, com padrões literais escapados e sem GRANT OPTION.
-19privilégios de schema em cada conta;isso não é administração global e não constitui blindagem completa de WordPress/Unix.
- Canário por conta: autenticação no próprio schema aprovada; acesso administrativo mysql.user rejeitado com ERROR1142 após a mudança, enquanto a mesma consulta de constante era autorizada antes.
- Todas as demais concessões/roles/proxies permaneceram iguais, incluindo os quatro alvos explicitamente protegidos por Rodolfo.
- Material de autenticação das duas contas comparado apenas em memória antes/depois: inalterado, não registrado/exposto.
- Estruturas, contagens exatas e agregados de post_type/post_status dos dois WordPress iguais antes/depois; nenhum artigo publicado, removido ou editado.
-15consumidores SQL e15controles HTTPS aprovados e preservados.
- Rollback privado de privilégios, sem senhas/hashes de autenticação: /var/backups/mgs-f011-permission-1556720208696316077/rollback-privileges.json.

## Itens7/8 protegidos, exclusão ainda não executada
- streamcb:148tabelas,144linhas exatas;dump40362bytes.
- mgpchat_5182:170tabelas,414linhas exatas;dump89602bytes.
- Total318tabelas/558linhas exatas;129964bytes de dumps comprimidos.
- Backups específicos root0600, diretório0700: /var/backups/mgs-f011-remaining-1556720208696316077.
- gzip, SHA-256 e restauração aprovados; definição/índices/contagens de origem e restauração iguais em comparação independente.
- Restores preservados: mgs_restore_f011_streamcb_1556720208696316077 e mgs_restore_f011_mgpchat_1556720208696316077.
- Bancos e contas originais continuam presentes. Nenhuma exclusão de produção ou backup nesta etapa.

## Confirmação crítica pendente
- Manifesto exato: data/f011-apply-1556720208696316077/manifest.json.
- SHA-256 d60cdc70fea3a5a446570a42fada9f37fa5479a6ce50c186be45c40264cd39dd.
- Inclui retirada imediata dos dois bancos, duas contas e dois restores; validação completa dos15sites; retenção dos dois dumps até o fim04/11/2026 em America/New_York.
- Descarte condicional proposto às00:05de05/11/2026, horárioEastern (05:05UTC), depois do dia04/11inteiro. Somente os dois dumps novos, conforme hashes/tamanhos exatos; arquivos de auditoria/rollback e todos os backups anteriores ficam excluídos.
- Nova instrução de retenção/recuperação, mensagem posterior ainda ambígua, falha de recuperação de evidências, deriva de arquivos ou referência de processo suspende a exclusão automática até reconciliação.
- Agendamento ainda NÃO ATIVO. Ativar somente após confirmaçãoCritical que abranja o manifesto e o descarte futuro. Silêncio sozinho não aprova uma operação crítica ainda não confirmada.

## Fontes de prova
- data/f011-apply-1556720208696316077/permission-isolation-receipt.json
- data/f011-apply-1556720208696316077/permission-https-postcheck.json
- data/f011-apply-1556720208696316077/backup-receipt.json
- data/f011-apply-1556720208696316077/restore-receipt.json
- data/f011-apply-1556720208696316077/independent-protection-validation.json
