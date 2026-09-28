# F026 — Mapeamento detalhado de `pinedb`, `pine` e `pinechatbot_43715`

**Estado:** RESOLVIDO — APOSENTADORIA CONCLUÍDA, FALHA INTERMEDIÁRIA RECUPERADA E READBACK VALIDADO  
**Data:** 2026-09-23 UTC  
**Servidor:** MatteiInc02 (`162.55.28.179`)  
**Autorizações:** Discord `1552312017958866955`; fase reversível `1552345406887821373`; manifesto destrutivo final `1552355819058761802`

## Atualização — resposta do Ciro

Em captura enviada por Rodolfo na mensagem Discord `1552342920475058339`, Ciro respondeu sobre os webapps relacionados ao bot antigo:

> Pode passar o facão. Está mto depreciado esse bot, não usamos nada dele.

Evidência da captura: SHA-256 `e7c5268ee5750046fa8d3c3e270f9f73b86ed05b305959ebc6a67ab94dba3525`.

Essa resposta elimina a lacuna de negócio sobre uso do bot legado. Ela não nomeia tecnicamente `pine`, `pinechatbot_43715` nem `pinechatuser_5932`, e não substitui a confirmação crítica de Rodolfo para exclusão dos alvos exatos. O escopo F026 permanece limitado ao conjunto mapeado; `mgpbot`, `streamcb` e o bot operacional no servidor do Ciro continuam fora dele.  
**Modo atual:** aposentadoria concluída; aplicação, schema original, restore isolado e usuário removidos; backups protegidos preservados.

## Atualização — backup e restore test

Após a primeira confirmação crítica de Rodolfo na mensagem Discord `1552345406887821373`, foi executada somente a fase reversível de proteção e teste:

- backup lógico completo: `/var/backups/mgs-pinedb-f026-20260923/pinechatbot_43715.sql.gz`;
- tamanho comprimido: 2.105.553.540 bytes (1,96 GiB);
- modo: `0600`, owner `root`;
- SHA-256: `38721916a2d181235282fcd495adf44b5df5e9894706bfdaa7a4d5352f8bb068`;
- `gzip -t`: PASS;
- restore isolado: `mgs_restorecheck_pine_f026_20260923`;
- 170/170 tabelas restauradas;
- 22.333.526 linhas exatas comparadas em todas as tabelas;
- nomes/tipos/engines, colunas, índices e objetos: hashes idênticos;
- origem e restore: zero grants, zero conexões e ambos ainda presentes;
- retenção mínima do backup: 2026-10-23.

Neste estágio intermediário nenhum alvo original havia sido excluído. O schema de restore permaneceu isolado e sem grant até a confirmação crítica final posterior à evidência de recuperação, conforme a governança de aposentadoria de banco.

## Fechamento — manifesto destrutivo executado

Rodolfo confirmou o manifesto SHA-256 `73f1a114b532b5def19f4f20871f5946280b54a314e04c40642642404820f77c` na mensagem Discord `1552355819058761802`. A execução e o readback produziram o estado final:

- Web Application `pine`, ID `1766159`: API 404, root e rotas Nginx ausentes;
- schema de teste `mgs_restorecheck_pine_f026_20260923`: ausente;
- banco `pinechatbot_43715`, ID `1276143`: API 404 e schema MySQL ausente;
- metadado `pinechatuser_5932`, ID `1146921`: API 404;
- app count RunCloud: 18 → 17; database count: 20 → 19; user count: 20 → 19;
- nenhum default app foi atribuído automaticamente após a remoção;
- `mgpbot` e `streamcb`: IDs, roots, configs e 12 crons preservados; home e login responderam HTTP 200 na origem e no público;
- bot operacional do Ciro: não acessado e fora do escopo.

### Falha intermediária e recuperação

O primeiro post-check detectou uma divergência criada pela própria chamada RunCloud `deleteUser=true`: embora o usuário não existisse no MySQL antes da operação, o RunCloud materializou `pinechatuser_5932@localhost` com privilégios globais ao remover os metadados. A conta tinha zero conexões. A validação falhou fechada, a causa foi identificada e a conta exata foi removida imediatamente dentro do escopo confirmado. Nenhum hash de autenticação ou material de credencial foi persistido. O post-check repetido passou com usuário MySQL igual a zero.

### Recuperação preservada

- diretório: `/var/backups/mgs-pinedb-f026-20260923`, modo `0700`;
- dump: 2.105.553.540 bytes, owner `root`, modo `0600`, SHA-256 `38721916a2d181235282fcd495adf44b5df5e9894706bfdaa7a4d5352f8bb068`, `gzip -t` PASS;
- app/Nginx: 2.143 bytes, owner `root`, modo `0600`, SHA-256 `59f73212a72482f320600e3284bd2e314c23146f69e4fed19368c10a93996a48`, teste de arquivo PASS;
- marcador `RETENTION.json`: modo `0600`;
- retenção mínima: 2026-10-23; apagar o backup exige um novo manifesto destrutivo e confirmação crítica separada.

## Resposta executiva

`pinedb` não era um banco. Era uma Web Application RunCloud do tipo phpMyAdmin, usada como interface administrativa. Essa aplicação e seu diretório foram removidos.

O banco que provavelmente motivou seu nome ainda existe:

- schema: `pinechatbot_43715`;
- RunCloud database ID: `1276143`;
- criado em 2024-07-02;
- estrutura completa de ChatPion, com 170 tabelas;
- aproximadamente 7,50 GB de dados/índices lógicos;
- aproximadamente 22,25 GB ocupados fisicamente no diretório MySQL;
- aproximadamente 19,52 milhões de linhas estimadas.

O banco está atualmente órfão/inativo:

- nenhuma Web Application atual declara ligação com ele;
- nenhum arquivo de configuração atual no servidor referencia o schema;
- o usuário registrado no painel RunCloud não existe mais no MySQL;
- não há grants MySQL ativos para o schema;
- o MySQL escuta somente em `127.0.0.1:3306`;
- nenhuma conexão ao schema apareceu em sete amostras ao longo de 30 segundos;
- a última atividade encontrada ocorreu em 2025-09-23, exatamente um ano antes do mapeamento.

## 1. Estado atual no RunCloud

A API ao vivo do RunCloud retornou 18 Web Applications no MatteiInc02.

### `pine`

- App ID: `1766159`;
- tipo: `custom`;
- criada em 2024-05-02;
- domínio: `momochatbot.com`;
- root: `/home/runcloud/webapps/pine`;
- default app do servidor: sim;
- campo `database` na API: `null`.

### `pinedb`

- nenhuma Web Application atual com esse nome;
- `/home/runcloud/webapps/pinedb`: inexistente;
- nenhuma configuração Nginx atual para `pinedb`;
- nenhum log atual `pinedb_access.log`;
- nenhum remanescente com “pinedb” localizado em `/home` ou `/var/backups`, dentro da busca limitada;
- a URL temporária antiga ainda resolve para o servidor, mas cai no fallback e redireciona para `allautolan.matteiservicesinc.com`; não entrega phpMyAdmin.

### phpMyAdmin atuais no servidor

A API mostra somente duas aplicações do tipo phpMyAdmin:

- `mgpbot` — `mgpbot.com`;
- `streamcb` — `streamcb.com`.

A aplicação `phmyaaddmins02`, também existente na auditoria anterior, não está mais no RunCloud.

## 2. O que é o `pine` hoje

O `pine` não contém aplicação ChatPion nem configuração de banco.

O root possui apenas um arquivo:

- `.htaccess`;
- 486 bytes;
- owner `root:root`;
- modo `0747`;
- não contém tokens de banco, formulário ou código PHP;
- não contém redirecionamento no próprio arquivo.

Não existem no root:

- `index.php`;
- `.env`;
- `wp-config.php`;
- `application/config/database.php`;
- diretórios `application` ou `system`;
- código de aplicação.

O domínio `momochatbot.com` não resolve no DNS público. Pela origem direta, o virtual host retorna HTTP 403. Os logs do `pine` contêm somente respostas de erro/fallback — 403, 404, 400, 405 e 499 — sem HTTP 200 no recorte analisado.

Conclusão: `pine` é atualmente um default/catch-all vazio, não uma aplicação operacional e não um consumidor do banco.

## 3. Banco `pinechatbot_43715`

### Identidade e volume

- RunCloud database ID: `1276143`;
- criado: `2024-07-02T15:45:32Z`;
- 170 tabelas;
- aproximadamente 7.498,49 MB em dados + índices;
- aproximadamente 22.254.425.489 bytes físicos no datadir;
- aproximadamente 19.520.574 linhas estimadas.

O filesystem do servidor tinha aproximadamente 1,72 TB disponíveis durante o mapeamento.

### Confirmação de produto

As tabelas são inequivocamente de ChatPion/Messenger Bot. Exemplos:

- `messenger_bot`;
- `messenger_bot_subscriber`;
- `messenger_bot_broadcast_serial`;
- `messenger_bot_broadcast_serial_send`;
- `messenger_bot_drip_campaign`;
- `messenger_bot_drip_report`;
- `facebook_rx_config`;
- `facebook_rx_fb_page_info`;
- `visual_flow_builder_campaign`;
- `users`.

### Maiores conjuntos

Valores InnoDB estimados, não contagens exatas:

- `messenger_bot_broadcast_serial_send`: ~14,02 milhões de linhas; ~4.626 MB;
- `messenger_bot_subscriber`: ~1,96 milhão; ~1.770 MB;
- `messenger_bot_drip_campaign_assign`: ~1,75 milhão; ~318 MB;
- `messenger_bot_drip_report`: ~792 mil; ~215 MB;
- `visual_flow_builder_campaign`: ~21,9 mil; ~164 MB;
- `messenger_bot_broadcast_serial`: ~45 mil; ~98 MB.

Outros indicadores:

- aproximadamente 3.023 páginas Facebook registradas;
- aproximadamente 60 usuários ChatPion;
- aproximadamente 212 mil registros estimados de mensagens enviadas.

O banco pode conter dados pessoais de assinantes e histórico de mensagens; qualquer backup ou descarte precisa de proteção e trilha de auditoria.

## 4. Ligação com aplicações

Foram encontrados 17 arquivos de configuração de aplicações que declaram bancos no MatteiInc02. Nenhum referencia `pinechatbot_43715` ou seu usuário.

A configuração do `mgpbot` aponta para:

- banco `mgpchat_5182`;
- usuário `mgpchatuser_5182`;
- host local.

A configuração do `streamcb` aponta para:

- banco `streamcb`;
- usuário `streamcb`;
- host local.

Nenhuma dessas instalações usa `pinechatbot_43715`.

A busca pelo nome exato do schema em 105.177 arquivos elegíveis sob `/home`, `/etc` e `/var/backups` não encontrou referência ativa.

## 5. Usuário e grants

O painel RunCloud ainda registra:

- database user ID: `1146921`;
- username: `pinechatuser_5932`;
- criado em 2024-07-02;
- associado no control plane ao banco `pinechatbot_43715`.

O estado real do MySQL diverge:

- não existe conta `pinechatuser_5932` em `mysql.user`;
- não existe grant para o schema em `mysql.db`;
- não existem grants por tabela;
- `information_schema.SCHEMA_PRIVILEGES` não retorna privilégios para o banco.

Conclusão: o painel RunCloud possui metadado antigo, mas o usuário e o vínculo não existem no banco real.

## 6. Rede e uso atual

- MariaDB/MySQL escuta somente em `127.0.0.1:3306`;
- não está exposto diretamente à internet nem ao servidor do Ciro;
- sete amostras do process list, distribuídas por 30 segundos, não observaram conexão ao schema;
- nenhuma conexão remota foi observada;
- como não existe usuário/grant e não há aplicação local configurada, o banco não está utilizável pelo fluxo normal.

Um túnel privilegiado ou acesso root ao servidor sempre poderia alcançar o MySQL local, mas não foi encontrada evidência de uso desse tipo.

## 7. Última atividade

Últimos valores encontrados diretamente nas tabelas:

- último login: `2025-09-23 06:50:18`;
- último erro de resposta do bot: `2025-09-23 01:25:55`;
- broadcast mais recente criado: `2025-09-23 06:55:33`;
- último agendamento: `2025-09-23 22:46:00`;
- último envio concluído: `2025-09-22 20:44:30`;
- última conclusão de broadcast: `2025-09-22 20:44:31`;
- última página adicionada: `2025-09-22`;
- último sync de leads: `2025-09-05 15:24:53`.

Metadados do MySQL também apontam as últimas alterações para 2025-09-23. Não foi encontrada atividade em 2026.

## 8. Relação provável entre os componentes

Fatos confirmados:

1. `pinedb` era uma Web Application phpMyAdmin, não um banco.
2. O banco `pinechatbot_43715` existe e contém uma instalação ChatPion antiga.
3. `pine`/`momochatbot.com` está vazio, sem código ou configuração de banco.
4. Nenhuma aplicação atual referencia o banco.
5. O banco deixou de registrar atividade em 2025-09-23.

Inferência de alta confiança, mas não prova documental:

- pelos nomes `pine`, `pinedb` e `pinechatbot_43715`, e pela estrutura ChatPion, é provável que `pinedb` tenha sido a interface administrativa usada para esse banco e que o `pine` tenha sido a aplicação correspondente antes de seu código ser removido.

Não existe configuração ou backup remanescente que permita provar tecnicamente esse vínculo histórico 1:1.

## 9. Risco pré-aposentadoria

### Risco operacional

Baixo. O banco não está conectado a aplicação, não possui usuário/grant e só aceita conexões locais.

### Risco de dados

Médio/alto. Há grande volume de dados antigos de Messenger/assinantes, potencialmente pessoais, ocupando 22,25 GB físicos sem consumidor ou política de retenção confirmada.

### Risco de exclusão imediata

Alto. A exclusão sem backup eliminaria histórico de aproximadamente 19,5 milhões de registros e não teria rollback simples.

### Risco separado no `pine`

Antes da aposentadoria, o diretório `pine` estava em `0757` e o único `.htaccess` em `0747`, mantendo other-write. A aposentadoria confirmada removeu o app e essas rotas; nenhum default substituto foi atribuído.

## 10. Recomendação executada

Foi executada a recomendação de **aposentar o conjunto antigo somente após proteção e prova de recuperação**.

Sequência segura concluída:

1. Ciro/Dev confirma que não reconhece `pinechatbot_43715` como dependência atual.
2. Gerar backup lógico completo, protegido e com SHA-256.
3. Restaurar o backup em schema isolado e validar estrutura, tabelas e contagens.
4. Reter o backup pelo período definido por Rodolfo.
5. Remover o schema, o metadado stale do usuário RunCloud e a aplicação vazia `pine` somente com confirmação crítica específica.
6. Validar que `mgpbot`, `streamcb` e o bot operacional no servidor do Ciro permanecem inalterados.

Decisão aplicada:

- **não reativar o `pinedb` público**;
- **não ligar o banco antigo ao `pine`**;
- backup e restore test concluídos; após confirmação do Ciro e confirmação crítica final de Rodolfo, resíduos antigos eliminados e readback validado.

## 11. Lacunas

- Não existe backup/configuração antiga que prove documentalmente o vínculo histórico `pine` ↔ `pinedb` ↔ `pinechatbot_43715`.
- O período de amostragem de conexões foi de 30 segundos; a ausência de usuário/grant e de referências de configuração é evidência mais forte que essa amostra.
- A busca local não substitui confirmação humana do Ciro sobre dependências externas ou túneis privilegiados.
- Não foi consultado o conteúdo de mensagens ou dados pessoais; somente estrutura, contagens estimadas e datas máximas.

## Evidências

Workspace:

`/root/.hermes/profiles/zeus/workspace/pinedb-mapping-20260923/`

Arquivos principais:

- `runcloud-live.json`;
- `remote-live.json`;
- `followup-live.json`;
- `db-deep-live.json`;
- `db-user-live.json`;
- `activity-storage-live.json`;
- `runcloud-databases-live.json`;
- `runcloud-db-detail-live.json`;
- `runcloud-db-grants-live.json`;
- `runcloud-webapp-db-settings-live.json`;
- `destructive-manifest.json` — SHA-256 `73f1a114b532b5def19f4f20871f5946280b54a314e04c40642642404820f77c`;
- `destructive-execution-receipt.json`;
- `destructive-postvalidation.json`;
- `backup-restore-receipt.json` e `backup-restore-readback.json`;
- `mysql-user-residue-cleanup-receipt.json`;
- `sheet-closure-receipt.json`.

REPORT-INFRA de fechamento: Discord `1552363375948996690`, canal `#alerts-infra`, readback validado.
