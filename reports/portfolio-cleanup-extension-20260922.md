# Ampliação autorizada da limpeza — 22/09/2026

## Estado atual

> Supersedido operacionalmente por `portfolio-cleanup-full-20260922.md`, após a confirmação `1551961776919281675`. Os 31 caches extras foram tratados e o ID 249 recuperado. Permanecem revisão inconclusiva Portal e decisão de contenção da nova escrita Mobileapp. Este documento conserva o histórico da etapa anterior.

**Ampliação executada no manifesto confirmado; recuperação pública e limpeza integral ainda incompletas.** Este relatório supersede o estado pendente dos 33 posts/16 caches/75 referências descrito no relatório `portfolio-cleanup-20260922.md`, preservado como histórico do primeiro lote. Não certifica ausência de outros comprometimentos nem fechamento do vetor de invasão.

- Thread: `1551768281688580096`.
- Confirmação da ampliação: `1551948550080831489`.
- Evidência: `/root/.hermes/profiles/zeus/workspace/portfolio-cleanup-extension-20260922/`.
- Planilha: https://docs.google.com/spreadsheets/d/1_8vUodLSgxfIj0vW0DlDpvljHFgygfI8A5Txc_Mc858/edit

## Operação e resultado validado

- 33 posts convertidos de publish para draft: 17 Autolendpro e 16 Zionnmedia. Conteúdo, títulos, slugs e demais campos coletados foram preservados; nenhuma exclusão definitiva de publicação.
- 16 caminhos exatos de cache Autolendpro removidos, com ausência relida no filesystem.
- 75 referências Yoast exatas removidas: 36 Autolendpro, 38 Zionnmedia e 1 Portal Brasil News.
- Coleta before/after, dry-run, canário, transações com guardas, fingerprints dos demais posts, identidade e indexables conferidos.
- Quatro conjuntos de backup com 53 objetos relidos por hash nos servidores, fora do webroot, sob `/var/backups/mgs-portfolio-cleanup-extension-20260922/`.
- Endpoints `?p=ID` dos 33 posts retornaram HTTP 404. As provas públicas dos permalinks não foram tratadas como equivalentes ao estado do banco.

## Bloqueio de recuperação pública

- Autolendpro ID 249 está draft no banco, mas seu permalink ainda serve o mesmo artigo por cache local fora dos 16 caminhos confirmados. A purga Cloudflare não remove esse HTML de aplicação.
- Autolendpro ID 131 e Zionnmedia ID 6782 têm slugs que redirecionam para outras publicações ainda publicadas; isso não é falha do status draft, mas não representa frontend limpo.
- Foram identificados 31 objetos adicionais de cache Autolendpro que referenciam posts já em rascunho, incluindo home, categorias, autores, paginação e artigos. Alguns contêm apenas referências/trechos; não equivalem a 31 novos artigos. Não foram apagados sem ampliação da confirmação crítica.
- Portal Brasil News permanece com limitação pública HTTP 403; não houve alteração de WAF, rota ou credencial para contorná-la.

## Revisão além dos manifestos anteriores

- 85 candidatos adicionais publicados, todos com HTTP 200 nas sondagens: Seniormenu 20; Tapsaga 12; Zionnmedia 16; Autolendpro 6; Apexwallet 19; Mobileapp 12. Folhadaterra não apresentou candidatos nesse detector.
- A lista distingue conteúdo aparentemente legítimo com indícios de injeção de artigos/listas de apostas incompatíveis. Candidatura não equivale, isoladamente, a confirmação de que todo o post deva ser retirado.
- Portal Brasil News: leitura integral por indicadores de 50.725 posts/pages publicados, com 420.843.638 bytes de conteúdo, encontrou três marcadores `tc-check` cuja função/autoria requer atribuição. Não foram classificados automaticamente como malware.
- Caches revelaram também títulos de conteúdo adulto/IA sexual e marcadores de verificação fora do detector inicial de apostas. A lista de 85 candidatos não é um inventário exaustivo de todo spam.
- Não há prova, nesta operação, de que os novos achados sejam reinjeção. A causa confirmada da cobertura incompleta é a seleção anterior por nós/hosts/índices específicos, insuficiente para todo o conjunto de publicações e caches relacionados.

## Planilha e preservação

- Mesma planilha, via Service Account canônica e helper corporativo.
- 160 células existentes atualizadas; adicionada a aba `Revisão restante`, mantendo `Pendências limpeza` como histórico de execução.
- Readback após formatação: 13 abas, 26.177 células verificadas; canário restaurado e células/fórmulas não planejadas preservadas pela comparação integral.
- Novos achados e caches permanecem explicitamente pendentes; nenhum domínio foi atestado integralmente limpo.

## Decisão necessária

Recomendação: autorizar o saneamento completo dos conteúdos e caches correlatos nos oito domínios originais, sem novos recortes por contagem: revisar todos os publicados, colocar somente spam confirmado em rascunho, remover somente trechos injetados em conteúdo legítimo e invalidar os caches derivados correlatos, com backups e manifestos revalidados. Casos ambíguos devem permanecer preservados e ser reportados. A exclusão dos caches adicionais exige confirmação crítica; não executar antes dela. Credenciais, permissões, plugins, PHP e hardening permanecem fora do escopo.

## Infraestrutura e aprendizado

- Scripts one-shot no workspace Zeus; nenhum cron/daemon iniciado para esta ampliação.
- Skill `wp-plugin-mass-operation`, referência `wordpress-irrelevant-posts-incident-audit.md`, atualizada e relida: fechamento completo dos detectores, rascunho versus redirects, cache local versus Cloudflare, inventário de caches correlatos e leitura streaming limitada.
- Falha de varredura volumosa recuperada com leitura `mysql --quick` e comparações literais limitadas, sem mudança de produção. A evidência de erro foi preservada e o resultado substitutivo passou.
- Inventário, audit log, checkpoint e REPORT-INFRA registram execução parcial e decisão pendente, não encerramento integral.
