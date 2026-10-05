# F011 — proteção e confirmação de aposentadoria dos dois bancos

Autoridade: Rodolfo Mattei, pedido atual1556668850060267551 na thread1551768281688580096, após pedido de aposentadoria1556660999967215660 e exclusão manual das aplicações informada1556663694811725827. O pedido atual delimita esta preparação aos bancos soluc3_1 e streamcb_480100 e às respectivas contas soluc3_1@localhost e streamcb_5913@localhost. Nenhuma exclusão executada; gate final Critical ainda aberto.

## Alvos live confirmados

MatteiInc02, RunCloud288158,162.55.28.179:

- soluc3_1: banco1278157, conta1148877;145tabelas e15.768.485linhas exatas. Associação exclusiva desta conta no painel; privilégio global real ainda existe.
- streamcb_480100: banco1342020, conta1209408/streamcb_5913;zero tabelas/linhas. Conta global real ainda existe.
- Nenhum consumidor encontrado no escopo varrido; amostras atuais sem conexão. Event scheduler OFF; nenhum evento, trigger ou routine nesses bancos. Soluc combina InnoDB/MyISAM, e a proteção usou evidência independente de ausência de writer mais igualdade estrutural/contagens antes e depois, sem bloquear outros bancos.
-15aplicações restantes explicitamente protegidas; streamcb/mgpbot já foram removidas pelo dono. Bancos streamcb/mgpchat_5182, respectivas contas, Pine e backup histórico, demais apps/bancos e backups ficam fora do manifesto atual.

## Proteção executada e validada

Root privado:/var/backups/mgs-f011-two-1556668850060267551,0700. Dumps schema-neutral root:0600,sem credenciais em argv/logs/manifesta.

- soluc3_1.sql.gz:1.357.428.631bytes;SHA25682b5671117cfcf0b1464368403aa973de15ec8e40a5e557eb4e6cef116f1fcfd.
- streamcb_480100.sql.gz:553bytes;SHA256bc5991f46857bfe27679b70eaa3d47261e1562a6741c7a7351124c31838c4424.
- Pipeline dump+gzip ambos exit0;gzip-t PASS;hash/modo/owner/bytes revalidados por coletor independente.
- Restores criados:mgs_restore_f011_soluc_1556668850060267551 e mgs_restore_f011_stream_1556668850060267551. Sem grant explícito e sem aplicação apontando/conectando; isso não revoga privilégios globais preexistentes das contas do host.
- Restores comparados com fontes:nomes/tipos/engines/collation de tabelas,colunas,indexes,counts exatos por tabela,totais,eventos,routines,triggers;PASS. Origens sem alteração pelas comparações antes/depois.
- Backup preservado no mínimo até2026-11-04;exclusão posterior de backup exige decisão/manifesto independente.

## Manifesto Critical preparado

Path:data/f011-two-retirement-1556668850060267551/manifest.json
SHA256:5590424f1ab1c71fa31a73deb2736fbfeaea008082647e16c76d6c57c0c2870e

Ações:revalidar identidades/grants/consumidores/ausência de conexões/backup+restore;remover apenas os dois restores de teste;excluir os dois bancos/metadados RunCloud com deleteUser=true explícito;verificar e remover somente resíduos runtime desses bancos/localhost-users se persistirem;validar ausência completa e preservação das15apps/controles ebackup.

Efeito:remoção dos dois bancos originais,das duas contas e das duas cópias SQL de teste;recuperação pelos dumps protegidos testados. Nenhuma exclusão de webapp,arquivo,domínio,backup,configuração ou outro banco incluída. Falha interrompe ações posteriores e preserva backup/evidência;sem replay cego.

Estado:backup/restore concluídos;destruição NÃO executada. Próximo passo:confirmação explícita de Rodolfo desse manifesto exato.
