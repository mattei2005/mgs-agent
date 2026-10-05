# F011 — mapa individual das contas SQL do MatteiInc02

Autoridade: Rodolfo Mattei, mensagem 1556648331998928917, thread 1551768281688580096. Servidor validado pela API RunCloud: 288158, MatteiInc02, 162.55.28.179. Coleta em 05/10/2026. Escopo somente leitura de produção; nenhuma senha, permissão, conta ou banco alterado.

## Resultado

Reconciliadas as 11 identidades históricas: 10 continuam reais e com permissões globais; pinechatuser_5932 foi aposentada no F026, com autorização 1552355819058761802 e audit log de 23/09. O estado atual não é 11 contas abertas.

Das 10 atuais, 8 têm configuração de aplicação identificada e autenticação SELECT real aprovada; 2 têm vínculo no RunCloud, mas nenhum consumidor foi encontrado no escopo varrido. Não declarar essas duas sem uso apenas por ausência de conexão em seis amostras curtas. Existem 17 aplicações no control plane e nos roots atuais. As contas root/mysql são de sistema e não fazem parte das 11.

Estas contas são identidades técnicas de banco, não os usuários humanos que entram no WordPress. Uma pessoa administradora WordPress usa o site; o PHP do site utiliza esta identidade MariaDB para ler/gravar suas tabelas.

## Problema comum e causa

As 10 identidades atuais têm privilégios globais de SELECT/INSERT/UPDATE/DELETE/CREATE/DROP, FILE, SUPER, SHUTDOWN, PROCESS, CREATE USER e outros; GRANT OPTION está N. Isso permite alcançar bancos de outras aplicações e administrar aspectos da instância MariaDB. FILE permite operações de arquivos sob o usuário do MariaDB e suas restrições, não equivale a root Unix. Acesso está em localhost e bind 127.0.0.1: não permite login externo direto ao MariaDB, mas não oferece isolamento entre aplicações do mesmo host ou via túnel autorizado.

A causa técnica comprovada é a concessão global; quem ou qual processo concedeu originalmente não foi atribuído. Não há prova de invasão nesta coleta. O painel relaciona cada usuário a um banco, mas essa associação não anula os privilégios globais reais.

## 1. soluc3_1@localhost

- Conta MariaDB e banco de mesmo nome presentes no servidor e no RunCloud.
- Usuário cadastrado no RunCloud em 06/07/2024; essa data é de cadastro no painel, não prova de início do privilégio global.
- Banco com 145 tabelas, 5.222.726.576 bytes lógicos (4,86 GiB). Estrutura de bot/Messenger da família ChatPion: assinantes, drip reports, broadcast serial, visual flow e páginas Facebook.
- Estimativa InnoDB de cerca de 3,07 milhões de linhas em messenger_bot_subscriber, não contagem exata nem pessoas únicas. Nenhum conteúdo/telefone/mensagem consultado.
- Nenhuma aplicação/configuração atual encontrada consumindo essa conta ou banco; não existe app soluc no catálogo atual. Último UPDATE_TIME disponível é de 2024-08-16, mas não demonstra última leitura, envio ou login.
- Estado: consumidor/dono empresarial não identificado. Preservar dados e conta até esclarecer uso, possíveis túneis e integrações externas. Não é descarte autorizado.

## 2. openzedsr_1784082054@localhost

- Consumidor confirmado: WordPress separado em sr.openzed.com, root /home/runcloud/webapps/openzedsr.
- Banco openzedsr_1784082054, 12 tabelas; home/siteurl e identidade de autenticação confirmadas.
- Não é o banco principal de openzed.com. Plugins normais ativos: zero. Finalidade comercial do subdomínio não inferida do nome SR.
- Solução recomendada: manter conexão e, após aprovação, limitar o alcance ao banco correspondente. Não apagar o subdomínio ou seu banco.

## 3. streamcb@localhost

- Consumidor confirmado: streamcb.com, root /home/runcloud/webapps/streamcb; aplicação PHP/CodeIgniter da família ChatPion, não WordPress.
- Configuração application/config/database.php usa banco streamcb; autenticação SELECT aprovada.
- Banco com 148 tabelas de bot/Messenger, SMS/email e módulos relacionados. Não foi confirmado uso empresarial recorrente só pela existência da configuração.
- Solução recomendada: preservar aplicação e restringir posteriormente ao próprio banco com testes específicos dos crons e rotinas necessárias.

## 4. streamcb_5913@localhost

- Conta real presente; painel relaciona ao banco streamcb_480100, cadastrado em 31/10/2024.
- Banco existe mas contém zero tabelas. Não confundir com streamcb, que tem 148 tabelas e consumidor confirmado.
- Nenhuma referência atual à conta ou ao banco encontrada em aplicações, scripts, crons e serviços no escopo varrido.
- Estado: possível resíduo antigo; dono/finalidade ainda não comprovados. Não declarar abandonado apenas pelo banco vazio; globalmente poderia acessar outro banco.
- Solução recomendada: esclarecer dependências antes de propor revogação ou exclusão separadamente.

## 5. allAutolan_1770897973@localhost

- Consumidor confirmado: allautolan.matteiservicesinc.com, instalação WordPress auxiliar em /home/runcloud/webapps/all-autolan.
- Banco allAutolan_1770897973, 12 tabelas; autenticação SELECT e home/siteurl aprovadas. Não confundir com autolendpro.com, que usa conta e banco próprios.
- Plugins normais ativos Lazy Blocks e WordPress Importer. Existência desses plugins não prova finalidade de produção ou staging.
- Solução recomendada: preservar conteúdo e operação; futuramente limitar ao banco exato, após testes.

## 6. cliquetsr_1784083435@localhost

- Consumidor confirmado: WordPress separado sr.cliquet.com, root /home/runcloud/webapps/cliquetsr.
- Banco cliquetsr_1784083435, 12 tabelas; autenticação SELECT e home/siteurl aprovadas; zero plugins normais ativos.
- Não é a conta do site principal cliquet.com. Finalidade de SR não inferida automaticamente.
- Solução recomendada: preservar aplicação e restringir ao seu banco mediante aprovação/testes.

## 7. mgpchatuser_5182@localhost

- Consumidor confirmado: mgpbot.com, aplicação ChatPion de teste já descrita no F025, root /home/runcloud/webapps/mgpbot.
- Banco mgpchat_5182, 170 tabelas; usuário e banco têm nomes diferentes. Autenticação SELECT aprovada e conexões reais observadas na amostragem final.
- Estrutura de Facebook/Messenger, fluxos e campanhas. Não confundir com o banco pine aposentado nem com o bot operacional do Ciro em outro escopo.
- Solução recomendada: manter aplicação; limitar depois ao banco mgpchat_5182, preservando crons e funcionalidades necessárias.

## 8. openzedsrf_1784083351@localhost

- Consumidor confirmado: WordPress separado srf.openzed.com, root /home/runcloud/webapps/openzedsrf.
- Banco openzedsrf_1784083351, 12 tabelas; autenticação e home/siteurl aprovadas; zero plugins normais ativos.
- Instalação diferente de sr.openzed.com e do site principal. Finalidade empresarial SRF não comprovada nesta coleta.
- Solução recomendada: preservar e limitar o alcance ao próprio banco após aprovação.

## 9. pinechatuser_5932@localhost

- Conta histórica associada ao banco pinechatbot_43715 e à aposentadoria F026.
- Ausente hoje tanto do MariaDB quanto dos usuários e bancos RunCloud; banco pine também ausente. A origem foi reconciliada pelo audit log da exclusão autorizada e recuperada de 23/09.
- Backup protegido permanece no escopo histórico de retenção; nenhum backup foi removido nesta tarefa.
- Solução: nenhuma ação de revogação necessária nesta conta, pois ela já não existe. Não recriar nem contabilizar como conta aberta atual.

## 10. cliquetsrf_1784083751@localhost

- Consumidor confirmado: WordPress separado srf.cliquet.com, root /home/runcloud/webapps/cliquetsrf.
- Banco cliquetsrf_1784083751, 12 tabelas; autenticação e home/siteurl aprovadas; zero plugins normais ativos.
- É distinta de sr.cliquet.com e do domínio principal. Finalidade empresarial do subdomínio não inferida do nome.
- Solução recomendada: preservar e limitar o alcance ao seu banco após aprovação/testes.

## 11. datinghubpro_1773252658@localhost

- Consumidor confirmado: WordPress datinghubpro.com, root /home/runcloud/webapps/datinghubpro.
- Banco datinghubpro_1773252658, 12 tabelas; autenticação e home/siteurl aprovadas.
- Plugins normais ativos Polylang e WordPress Importer; MU auxiliares encontrados. Função efetiva da identidade é conectar o site ao seu banco de artigos/configurações/usuários, não uma conta humana de redator.
- Solução recomendada: preservar o site e restringir posteriormente ao próprio banco.

## Validação e lacunas

- Conjunto histórico exato: 11 identidades; conjunto atual: 10; oito consumidores confirmados por arquivo/configuração, domínio registrado, banco e SELECT CURRENT_USER()/DATABASE().
- Coleta estrutural segura: mysql.user sem campos de autenticação, mysql.db, mysql.tables_priv, information_schema, API GET-only RunCloud e configurações lidas apenas em memória.
- 2.955 arquivos na coleta primária; 21.420 na varredura complementar para as duas contas sem consumidor e o pine. Contagens não são aditivas, pois há sobreposição; limites de tamanho/profundidade e exclusões de vendor/cache/backups impedem alegar cobertura universal.
- Seis amostras de conexões; ausência de conexão não demonstra inatividade. Sem general log histórico, não foi certificado o último acesso de soluc3_1 ou streamcb_5913.
- Falha auxiliar de autenticação inicial: oito provas CLI falharam quando herdaram opções locais de administrador. Mesma identidade/configuração aprovou 8/8 após mysql --no-defaults, sem nenhuma mudança de senha, concessão ou arquivo do host. Recibos inicial e recuperado preservados; lição salva na skill application-database-retirement-governance.
- Até aprovação de mudança, F011 continua aberto por excesso de permissões; o mapeamento está concluído. Não houve concessão/revogação, DROP, export de banco, restart ou alteração de configuração em produção.

## Recomendação

Separar duas decisões: esclarecer proprietário/uso de soluc3_1 e streamcb_5913; preparar um plano reversível de grants por banco para os oito consumidores confirmados. As contas não precisam ser apagadas para corrigir o excesso. Uma confirmação crítica específica será exigida antes de modificar permissões; nenhum write desse tipo foi autorizado por esta tarefa de mapeamento.
