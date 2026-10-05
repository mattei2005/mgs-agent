# F011 — exclusão do conjunto de dois bancos concluída

## Autoridade e escopo
- Rodolfo: confirmação final Discord 1556698397581254729, thread 1551768281688580096.
- Aceitou evidência delimitada de dados legados, sem exigir certificação integral de quatro dias sem qualquer escrita; a lacuna de histórico permanece registrada e não foi convertida em prova.
- Servidor: MatteiInc02 / RunCloud 288158 / 162.55.28.179.
- Manifesto preservado: data/f011-two-retirement-1556668850060267551/manifest.json.
- SHA-256: 5590424f1ab1c71fa31a73deb2736fbfeaea008082647e16c76d6c57c0c2870e.

## Objetos removidos e conferidos
1. Schema soluc3_1, RunCloud database ID 1278157; conta soluc3_1@localhost, database-user ID 1148877.
2. Schema streamcb_480100, RunCloud database ID 1342020; conta streamcb_5913@localhost, database-user ID 1209408.
3. Restore de teste mgs_restore_f011_soluc_1556668850060267551.
4. Restore de teste mgs_restore_f011_stream_1556668850060267551.

Ordem do manifesto respeitada: revalidação → dois restores → primeiro banco/conta no RunCloud → segundo banco/conta → reconciliação de resíduos autorizados → validação completa.
Todos os quatro IDs originais retornaram GET 404 e foram excluídos dos catálogos paginados. Os quatro schemas estão ausentes no MariaDB; as duas contas e respectivas linhas de privilégios estão ausentes em mysql.user/db/tables_priv/columns_priv/procs_priv.

## Preservação e recuperação
- Backups originais mantidos em /var/backups/mgs-f011-two-1556668850060267551, root privado, arquivos 0600, diretório 0700.
- Tamanhos, SHA-256 e gzip revalidados após a exclusão.
- Restore prévio aprovado: soluc3_1 com 145 tabelas e 15.768.485 linhas exatas; streamcb_480100 vazio.
- Retenção até pelo menos 2026-11-04. Remoção futura de backups exige autorização destrutiva separada.
- Preservados streamcb, mgpchat_5182 e respectivas contas, backup Pine e todos os outros schemas, contas, aplicações, arquivos, domínios, rotas e configurações.

## Validações independentes
- 15 aplicações protegidas: catálogo e roots preservados; 15 autenticações SQL configuradas aprovadas antes/depois, mesmas identidades e schemas.
- 15 controles HTTPS aprovados antes/depois, mesmas respostas e destinos.
- Inventários dos schemas e contas não alvo exatamente iguais antes/depois.
- Serviços exatamente iguais antes/depois: mariadb, nginx-rc e php81rc-fpm ativos; php82rc-fpm/php83rc-fpm já inativos antes e permaneceram assim.
- Sem mudança de aplicação default, permissões de outras contas, credenciais, firewall ou restart.
- MatteiInc02 atual: 15 aplicações, UID 1000 com 6 roots e UID 1002 com 9; 8 contas SQL de aplicação com privilégios globais, ainda pendentes de saneamento na F011.

## Falhas de coleta recuperadas
O primeiro preflight abortou antes de qualquer exclusão por escaping do parser de configurações na composição do script remoto. A função foi carregada de arquivo Python próprio, sem nova interpretação de escapes; replay somente leitura preservou recibos anteriores e passou 15/15 autenticações. Uma consulta local auxiliar usou a chave user em vez de username no mapa histórico; corrigida sem mutação. Nenhuma falha de produção ou de exclusão permaneceu pendente.

## Estado final
Aposentadoria deste conjunto: FECHADA E VALIDADA. F011 como um todo permanece ABERTA para isolamento das 8 contas globais remanescentes e avaliação separada dos resíduos preservados de streamcb/mgpchat_5182; não autorizado executar esse escopo adicional nesta confirmação.

## Recibos canônicos
- data/f011-two-retirement-1556668850060267551/authorization-1556698397581254729.json
- data/f011-two-retirement-1556668850060267551/execution-closure_validated-1556698397581254729.json
- data/f011-two-retirement-1556668850060267551/execution-restores_removed-1556698397581254729.json
- data/f011-two-retirement-1556668850060267551/execution-delete_1278157-1556698397581254729.json
- data/f011-two-retirement-1556668850060267551/execution-delete_1342020-1556698397581254729.json
- data/f011-two-retirement-1556668850060267551/execution-runtime_residues_reconciled-1556698397581254729.json
