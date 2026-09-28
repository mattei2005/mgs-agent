# Portal Brasil News — bloqueio XML-RPC confirmado

## Resultado

> **Fechamento posterior:** `portfolio-final-closure-20260922.md` concluiu a classificação de conteúdo restante e a remediação final. Este relatório preserva o histórico específico do bloqueio XML-RPC.

Autorização: `discord:1551768281688580096/1551988712089456762`.

**Bloqueio temporário XML-RPC do Portal Brasil News aplicado e validado.** Esta decisão supersede a pendência crítica do relatório `portfolio-containment-20260922.md`. Mobileapp e Portal agora têm os bloqueios especificamente confirmados. Isso conclui a contenção desses endpoints, não certifica a recuperação integral dos oito sites nem encerra a revisão de conteúdo inconclusivo.

- Alvo: `portalbrasilnews.com`, servidor 01.
- Include: `/etc/nginx-rc/extra.d/portalbrasilnews.location.main-before.mgs-xmlrpc-containment.conf`.
- SHA-256: `419d3243c48a93ceb19d29be5fb959512c51e8327ea5ec0090eaadf4b644d726`.
- Aplicação: `2026-09-22T16:11:04.585924+00:00`.
- Backup: `/var/backups/mgs-portalbrasilnews-xmlrpc-20260922`.
- Vhost gerado preservado por hash; `nginx-rc -t` antes/depois, reload e active validados. Nenhum restart de gateway Hermes.
- Rollback: mover somente esse include para fora de extra.d, validar configuração e recarregar Nginx no fluxo autorizado. A configuração anterior foi preservada.

## Validação de origem versus público

A validação na origem usou curl com SNI/Host do domínio e resolução local `127.0.0.1`, sem alterar DNS. Foram 14 casos antes e 14 depois, abrangendo apex/www, GET/POST, query, maiúsculas e path-info.

- Antes: XML-RPC GET 405; POST no apex 200 com método read-only de listagem; controles home/REST 200.
- Depois: todos os casos XML-RPC 403 com o corpo exato `MGS: XML-RPC temporarily disabled.`; home e REST continuaram 200.
- Público do auditor: home, REST e XML-RPC conservaram o HTTP 403 preexistente, sem o marcador. Esse 403 externo não foi usado como prova do bloqueio Nginx nem como alegação de indisponibilidade causada pela mudança.
- Inclui e backups conferidos independentemente por hash; serviço permaneceu active.

## Publicação anterior ao bloqueio

O post 237305 foi publicado às 16:06:41 UTC, antes do bloqueio: `Casinos online en Argentina 2026: tendencias, hábitos de juego y cómo elegir una plataforma confiable`. Título e corpo confirmaram promoção de cassino. Foi colocado em rascunho dentro do escopo de limpeza vigente, após dry-run e backup; conteúdo integral preservado por hash. Um link Yoast e um indexable derivado foram tratados; cinco URLs purgadas na Cloudflare.

Backup: `/var/backups/mgs-portfolio-containment-20260922/portalbrasilnews.com/postblock-237305`. Readback de conteúdo/status e hash do backup passou. Na consulta de `2026-09-22T16:14:41.594039+00:00`, não havia outros registros de post/page com ID maior que 237305. É uma janela curta observada, não prova de eliminação de todas as entradas ou de ausência de edições em IDs anteriores.

## Planilha e continuidade

Mesma planilha `1_8vUodLSgxfIj0vW0DlDpvljHFgygfI8A5Txc_Mc858`, SA corporativa/helper canônico. Sete ranges atualizados e relidos: Resumo, Contenção XML-RPC e a linha do post 237305 em Saneamento completo. Snapshot anterior, comparação contra deriva e canário restaurado. O recibo cobre os ranges deste turno, não afirma nova validação integral das centenas de milhares de células.

Evidência: `/root/.hermes/profiles/zeus/workspace/portfolio-containment-20260922/`, especialmente `block-portal-receipt.json`, `portal-origin-before.json`, `portal-origin-after.json`, `portal-public-after.json`, `portal-postblock-final.json`, `sheet-portal-block-verified.json`.

A pendência restante é classificação de conteúdo e investigação da origem/credencial da escrita; não há novo pedido de bloqueio Portal/Mobileapp em aberto. Não houve alteração de senhas, tokens, usuários, permissões, plugins, PHP, firewall ou DNS. Nenhum cron/daemon novo; execução foreground. Inventário/audit/checkpoint/REPORT-INFRA registram a contenção concluída e a recuperação integral não certificada.
