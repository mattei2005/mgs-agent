# Contenção XML-RPC e escrita concorrente — 22/09/2026

## Autorização e estado

> **Fechamento posterior:** `portfolio-final-closure-20260922.md` resolveu a revisão de conteúdo restante e as remediações críticas finais. As pendências descritas abaixo são histórico temporal, não estado atual.

> **Supersessão:** a confirmação `1551988712089456762` foi aplicada; o bloqueio XML-RPC Portal está validado em `portal-xmlrpc-containment-20260922.md`. A decisão crítica citada abaixo foi resolvida. Preserva-se a narrativa histórica; classificação de conteúdo e recuperação integral continuam abertas.

Fonte: Discord `1551768281688580096/1551985121853448304`. Rodolfo confirmou o bloqueio temporário de XML-RPC no Mobileapp e solicitou autonomia operacional para a tarefa. Essa autorização não modifica AGENT.md nem dispensa confirmações do Critical Subset para outros alvos/credenciais. Estado: **Mobileapp contido no endpoint; recuperação integral dos oito domínios pendente; decisão crítica Portal Brasil News aberta**.

## Aplicado e validado

- Criado exclusivamente `/etc/nginx-rc/extra.d/mobileapp.location.main-before.mgs-xmlrpc-containment.conf` no servidor 03, como include específico do app.
- A regra retorna HTTP 403 com marcador `MGS: XML-RPC temporarily disabled.` para `/xmlrpc.php`, case-insensitive e path-info. Query não contorna a regra.
- Configurações geradas do vhost mantiveram seus hashes. `nginx-rc -t` passou antes/depois, reload passou e serviço permaneceu active. Não houve restart de gateway Hermes.
- Backup e plano de rollback em `/var/backups/mgs-mobileapp-xmlrpc-20260922`; para desfazer, mover o include para fora de extra.d, validar Nginx e fazer reload pelo fluxo autorizado. Nenhum arquivo de origem foi removido.
- Hash do include: `641065ebcc084ffe5b9c527b64d34631714ddf8f61939188cdf43ebbbd8f2349`.
- 14 sondagens públicas passaram: GET/POST, query, maiúsculas e path-info em apex/www retornam 403 com o marcador; homepage e REST retornam 200.
- Readback posterior conferiu hash/config e serviço active. Nenhum post/page novo após ID 290 apareceu no Mobileapp até essa coleta; isso é uma janela observada, não prova de eliminação de todas as entradas.

## Portal Brasil News — novo bloqueio decisório

Surgiram quatro novas publicações de cassino após o último saneamento, IDs 237297, 237299, 237301 e 237303, entre 15:36:14 e 15:55:09 UTC. Títulos e corpos foram revisados; todas foram colocadas em rascunho, com conteúdo preservado, backup recuperável, dry-run e readback. Foram tratados seis links Yoast e quatro indexables derivados. Backup remoto em `/var/backups/mgs-portfolio-containment-20260922/portalbrasilnews.com/containment-237297-237303`, relido por hash. Purga Cloudflare dirigida de 11 URLs confirmada; sem purge global.

O log exato `/home/runcloud/logs/nginx/portalbrasilnews_access.log` registra POST `/xmlrpc.php` HTTP 200 às 15:36:15 UTC, correlacionado com a primeira publicação. As outras três não tiveram a mesma correlação demonstrada nesse recorte. Sem request body, não é prova da chamada autenticada, credencial ou autoria. A investigação leu arquivos de log de nomes semelhantes além do alvo por glob excessivamente amplo; nenhuma evidência desses outros domínios foi usada para atribuir a ocorrência ao Portal e nenhum deles foi alterado.

Recomendação: bloqueio temporário de `/xmlrpc.php` no Portal Brasil News, por include Nginx específico do app, com validação e rollback equivalentes. Estado atual: endpoint sem esse bloqueio específico e publicações recentes observadas. Estado proposto: HTTP 403 apenas no XML-RPC; home/REST preservados. Impacto: integrações que publicam via XML-RPC param até rollback. **Não aplicado: alteração crítica de configuração do servidor em outro alvo requer confirmação específica.** Senhas, tokens, usuários, permissões, plugins e PHP não foram alterados.

## Revisão de conteúdo ainda não encerrada

A releitura integral dos 14.776 posts/pages publicados no Portal antes desta contenção mostrou uma falha adicional no critério anterior: `post_type=page`, autores ou IDs iniciais foram tratados como proteção ampla. Páginas também contêm promoções de cassino/pharma. O total anterior de 14.392 inconclusivos não esgota todos os registros que precisam de revisão. Nenhuma dessas páginas adicionais foi removida automaticamente neste turno. A regra mais permissiva, anteriormente rejeitada, continua não aplicada para evitar retirada de conteúdo legítimo por links isolados.

Não marcar os sites como limpos nem substituir a decisão de contenção por ciclos repetidos de apagar spam enquanto novas publicações entram.

## Planilha, continuidade e aprendizado

Mesma planilha `1_8vUodLSgxfIj0vW0DlDpvljHFgygfI8A5Txc_Mc858`, via SA corporativa e helper canônico. Snapshot de alvos e metadata, canário restaurado, comparação contra deriva e readback exato. Quatro células de Resumo atualizadas; quatro linhas adicionadas a Saneamento completo; aba Contenção XML-RPC criada com quatro registros de estado/limitação. O readback deste turno cobre exatamente os ranges gravados, não repete a validação integral de 401.757 células anterior.

Evidência: `/root/.hermes/profiles/zeus/workspace/portfolio-containment-20260922/`. Skill WordPress atualizada: não proteger por tipo/autor/ID sem evidência individual, procedimento RunCloud de bloqueio por app, escopo crítico por alvo. Nenhum cron/daemon criado; execução foreground. Inventário, audit, checkpoint e REPORT-INFRA registram o bloqueio decisório, sem alegar conclusão integral.
