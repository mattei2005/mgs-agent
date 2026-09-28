# Saneamento de conteúdo e caches — oito domínios — 22/09/2026

## Estado executivo

> **Fechamento posterior:** `portfolio-final-closure-20260922.md` concluiu a revisão dos 14.421 registros antes inconclusivos, tratou 14.572 alvos adicionais, removeu artefatos/caches residuais e remediou a configuração exposta do Folhadaterra. Este relatório permanece como histórico do lote conservador anterior.

> Continuidade posterior em `portfolio-containment-20260922.md`: bloqueio XML-RPC Mobileapp aplicado, quatro novas publicações Portal tratadas; contenção Portal exige decisão crítica. A revisão de registros anteriormente protegidos por tipo/ID permanece aberta. Este relatório conserva o histórico do lote anterior.

**Manifesto conservador aplicado e validado; recuperação integral NÃO certificada.** A autorização `1551961776919281675`, na thread `1551768281688580096`, ampliou o escopo para conteúdo confirmado e caches correlatos dos oito domínios, preservando casos ambíguos e sem alterações de credenciais, permissões, plugins, PHP ou mecanismos de segurança.

A coleta integral revelou que a estimativa anterior era materialmente incompleta, sobretudo no Portal Brasil News. Foram lidos os campos de conteúdo de todos os posts/pages publicados dos oito domínios. No Portal, os 50.725 publicados foram classificados por regras conservadoras documentadas e controles revisados; isso NÃO representa revisão humana individual de cada artigo nem uma prova forense de autoria.

## Resultado deste turno

- 36.123 publicações convertidas para rascunho; nenhum conteúdo dessas publicações apagado definitivamente.
- Distribuição de rascunhos: Portal Brasil News 35.953; Seniormenu 37; Tapsaga 11; Zionnmedia 43; Autolendpro 17; Apexwallet 41; Mobileapp 21, incluindo um post novo que surgiu durante a operação.
- Sete publicações preservadas com saneamento cirúrgico: Seniormenu 2; Tapsaga 3; Mobileapp 2. Removidos somente parágrafos/anchors de apostas revisados, por offsets, sem reserializar ou apagar o restante do conteúdo.
- 72.618 referências Yoast e 36.010 registros derivados `yoast_indexable` dos alvos saneados/removidos da publicação foram removidos. Backups preservam as linhas.
- 32 objetos HTML de cache Autolendpro removidos com backup, abrangendo todos os 31 caches adicionais listados na etapa anterior. Demais caches não relacionados preservados.
- Cloudflare: 72.231 URLs purgadas em cinco zonas acessíveis, com recibos por lote; sem purge global. Apexwallet e Mobileapp continuam sem zona nos dois escopos aprovados; nenhum token/permissão foi alterado. Seus alvos HTTP foram validados sem a antiga publicação.
- Folhadaterra: os 11 arquivos removidos na etapa inicial continuam ausentes no servidor e suas rotas retornaram 404; não houve nova remoção nesse domínio.

## Classificação e limites

- A triagem Portal exige conjunto de sinais de apostas/adulto/pharma, repetição temática no corpo, tema na abertura/título e promoção externa, protegendo páginas e registros financeiros de controle. IDs, hashes e classificação foram congelados antes da escrita. O código é evidência do critério, não uma garantia semântica de ausência de falsos positivos.
- Uma segunda regra mais permissiva gerou 7.418 candidatos adicionais, mas foi rejeitada e NÃO aplicada: a amostra passou a incluir artigos sobre hotéis, desenhos e tecnologia com links injetados. Esses casos podem exigir limpeza cirúrgica em vez de retirada integral.
- Permanecem 14.392 registros Portal sem decisão segura de remoção integral. Não foram tratados como limpos nem todos como artigos maliciosos integrais. São revisão inconclusiva, não escopo adicional que precise novamente autorizar a simples análise.
- Nos demais domínios, 29 registros foram preservados por ambiguidade ou por serem marcadores numéricos, vazios, verificadores e artigos de finalidade não atribuída. A planilha identifica cada um, incluindo os três `tc-check` do Portal dentro da revisão maior.
- Não foi fechada a porta de entrada. Não confundir quantidade removida da publicação com integridade de segurança do site.

## Escrita concorrente no Mobileapp

Entre as coletas surgiu o post 289, título `Siti di scommesse Non AAMS Senza documenti: Manuale pratico alla Registrazione veloce`, com `post_date_gmt` 2026-09-22 14:37:23 e promoção de `artistidelpanettone.it`. Foi confirmado como artigo de apostas e também colocado em rascunho dentro do escopo aprovado, após dry-run e backup.

O access log `/home/runcloud/logs/nginx/mobileapp_access.log` registra POSTs em `/xmlrpc.php` às 14:37:22 e 14:37:26 UTC, HTTP 200, e GET do novo slug às 14:37:28, HTTP 200. Correlação temporal não prova o corpo da chamada, autenticação ou autoria. `wp-cron.php` também aparece na janela. Audit/inventário/histórico consultados não atribuíram esse post a uma operação MGS autorizada. O diagnóstico é **nova publicação concorrente não atribuída, consistente com entrada ainda ativa**, não atribuição a uma pessoa/IP.

Recomendação decisória: bloquear temporariamente `/xmlrpc.php` somente no Mobileapp, com backup/rollback e validação, e investigar a origem da escrita. Isso interromperia integrações que publicam por XML-RPC; não exige bloquear REST ou o acesso público. NÃO foi aplicado, pois altera controle de produção fora desta autorização. Rotação de credenciais permanece uma decisão crítica separada.

## Validação e recuperação

- Dry-run com tabelas temporárias para todos os lotes; canários reais em Portal, Seniormenu e Autolendpro antes do restante.
- Lotes de até mil registros, backup recuperável antes da transação, compare-and-swap de hashes/status, guardas de contagem e readback do registro completo após cada alteração.
- Readback independente de todos os fingerprints: sem alteração inesperada de registros preexistentes fora do manifesto. No Mobileapp, IDs novos 289/290 foram registrados; 290 é o registro auxiliar preservado, não exclusão silenciosa.
- 48 conjuntos de backup relidos por hash, contendo os 36.130 registros de posts tratados e dados SEO/cache. Restauração de amostras em tabelas temporárias de sete bases foi exercitada. Nenhum spam foi republicado para testar rollback.
- Caminho de backup remoto: `/var/backups/mgs-portfolio-cleanup-full-20260922/` nos respectivos servidores.
- 281 alvos HTTP conferidos; zero divergência dos critérios definidos. Todos os drafts dos seis domínios públicos foram testados por ID e permalink; 36 amostras Portal permanecem limitadas por HTTP 403. Banco verificado em todo o conjunto Portal não equivale a frontend público certificado.
- Autolendpro ID 249, anteriormente exposto por cache, agora retorna 404 tanto no permalink quanto por ID. Os sete conteúdos saneados continuaram HTTP 200 sem os trechos removidos.
- Homes dos outros sete domínios retornaram 200. Os estados observados de ads.txt/sitemaps estão no artefato HTTP; o presente trabalho não alterou essas configurações nem certifica entrega de anúncios.

## Planilha e evidências

Planilha preservada: https://docs.google.com/spreadsheets/d/1_8vUodLSgxfIj0vW0DlDpvljHFgygfI8A5Txc_Mc858/edit

- Service Account corporativa e helper canônico; Drive canEdit e Sheets validados.
- Snapshot imutável antes da gravação, canário restaurado, comparação prévia contra deriva e gravações RAW.
- 160 células preexistentes atualizadas; adicionadas `Saneamento completo` e `Preservados revisão`.
- 36.130 linhas de execução e 14.421 linhas de revisão preservada; 15 abas e 401.757 células conferidas após a formatação, incluindo fórmulas e células não planejadas.
- Evidência restrita: `/root/.hermes/profiles/zeus/workspace/portfolio-cleanup-full-20260922/`; `validation-summary.json`, `sheet-verified.json`, recibos de aplicação, backups, HTTP, Cloudflare e correlação de logs.

### Fechamento visual F001–F008 após correção de Rodolfo

Rodolfo apontou corretamente que, embora as abas detalhadas e o Resumo já tivessem sido gravados, a apresentação visível das linhas F001–F008 na aba `Prioridades` ainda não encerrava claramente cada item. Em 22/09/2026 foram atualizadas as colunas de execução, autorização e evidência dessas oito linhas, além de quatro células do `Resumo`.

Foram 28 ranges escritos e relidos pela API Sheets com a Service Account canônica; o canário foi restaurado. O fechamento declara o tratamento dos itens confirmados, preserva os limites forenses e continua sem certificar recuperação integral. Recibo: `/root/.hermes/profiles/zeus/workspace/portfolio-sheet-finalize-20260922/verified.json`.

## Infraestrutura e aprendizado

Scripts one-shot em foreground; nenhum cron/daemon criado. O erro de parsing do dry-run foi causado por `str.splitlines()` separando Unicode legal dentro de JSON; corrigido para LF explícito e todos os dry-runs restantes passaram antes da aplicação. Skill WordPress atualizada com a correção, limites da classificação automatizada e a verificação de novos IDs/escritas concorrentes. Inventário, checkpoint, audit e REPORT-INFRA registram estado parcial e decisão de contenção pendente.
