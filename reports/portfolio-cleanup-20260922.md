# Limpeza autorizada de oito domínios — 22/09/2026

## Estado executivo

> Atualização posterior: o estado pendente dos 33 posts/16 caches/75 referências abaixo foi supersedido por `portfolio-cleanup-extension-20260922.md`. A ampliação foi executada, mas novos conteúdos e caches fora dos manifestos mantêm a recuperação integral pendente. Este documento preserva o histórico do primeiro lote.

**Lote confirmado executado e validado; limpeza integral NÃO concluída.** A validação ampliada confirmou 33 outras publicações ainda acessíveis com spam, fora das 36 publicações descritas na confirmação. Esses novos alvos não foram alterados; a extensão depende de Rodolfo. A planilha foi atualizada com essa distinção, sem marcar os domínios como integralmente limpos.

- Origem: thread Discord `1551768281688580096`.
- Pedido: `1551920513176182838`; confirmação crítica do plano: `1551921994222665741`.
- Alvos confirmados: folhadaterra.com.br, apexwallet.de, autolendpro.com, mobileapp.com.br, portalbrasilnews.com, seniormenu.com, tapsaga.com, zionnmedia.com.
- Sheet preservada: https://docs.google.com/spreadsheets/d/1_8vUodLSgxfIj0vW0DlDpvljHFgygfI8A5Txc_Mc858/edit
- Evidência restrita: `/root/.hermes/profiles/zeus/workspace/portfolio-cleanup-20260922/`.

## Resultado do lote confirmado

- Folhadaterra: 11 arquivos coincidiram com os hashes da auditoria; backup forense root-only fora do webroot, remoção dos 11 caminhos, ausência relida e 11 respostas públicas HTTP 404. Não foram acionados para autenticação, execução de comandos ou exploração.
- 36 publicações: retirada por offsets de 311 trechos/marcadores de injeção, incluindo 232 links. A contagem de trechos inclui marcadores e textos sem link, não somente nós ocultos. Nenhuma publicação ou revisão excluída; títulos, autores, slugs, status, datas e conteúdo fora dos intervalos revisados preservados.
- Distribuição: Apexwallet 6, Autolendpro 11, Mobileapp 3, Portal Brasil News 1, Seniormenu 6, Tapsaga 7, Zionnmedia 2.
- 11 objetos HTML de cache Autolendpro saneados cirurgicamente, incluindo descrições sociais derivadas quando contaminadas.
- 139 referências maliciosas Yoast dos IDs autorizados removidas: Autolendpro 122 e Zionnmedia 17. Registros fora do target set foram preservados para decisão separada.
- Cloudflare: purge por URLs exatas, sem purge global, em seis zonas acessíveis pelos dois escopos de token aprovados. Apexwallet/Mobileapp não foram encontradas nesses escopos; não houve mudança de credencial ou permissão. As páginas desses dois sites foram validadas sem indicadores no público, cachebuster e origem.

## Validação e rollback

- Dry-run nas sete bases de conteúdo usando tabelas temporárias e rollback; nenhum bootstrap WordPress/PHP executado como root.
- Canário: Autolendpro ID 12, banco/cache/Yoast e HTTP público/cachebuster/origem. Formulários, iframes e fontes de scripts mantidos. Só depois aplicado o restante.
- Transações com locks, compare-and-swap de hashes, guardas de contagem e readback de todos os campos do registro.
- 76.853 registros de posts/revisões fora dos alvos mantiveram seus fingerprints; os únicos 36 conteúdos alterados coincidiram com o manifesto.
- Identidade, configuração de home/tema e hashes dos arquivos protegidos coletados mantidos. Nenhuma alteração de credenciais, permissões, plugins, PHP, firewall, anúncios ou configuração da homepage.
- A leitura pública atualizou dois metadados de runtime no Tapsaga ID 12863: contador de visitas `post_views_count` e transient Pinterest `powerkit_share_buttons_transient_pinterest`. Chaves e código escritor foram verificados; isso não foi ocultado como “metadados integralmente inalterados”. Demais fingerprints de metadata do conjunto permaneceram iguais.
- 35/36 URLs do lote: HTTP 200 sem os indicadores conhecidos. Portal Brasil News: conteúdo limpo no banco, mas HTTP público 403 e sonda de origem 404; condições preexistentes. Sua renderização pública não foi certificada e não houve alteração de WAF/rotas para contornar a limitação.
- Homes/ads.txt/sitemap: estados HTTP preexistentes preservados na comparação. Código presente não certifica entrega real de anúncios nem envio de formulários.
- Backup: nove conjuntos, 61 objetos conferidos independentemente nos três hosts em `/var/backups/mgs-portfolio-cleanup-20260922/`. Inclui 11 objetos forenses, 36 registros, 11 caches e três exports de linhas SEO. Manifestos guardam hashes e atributos necessários. Não restaurar malware em produção como teste.
- Último readback independente: 36 hashes de conteúdo exatos, status publish preservado e 11 caminhos ausentes, em oito domínios (`final-production-readback.json`).

## Pendência decisória — novos alvos fora do lote

A auditoria anterior enfatizou os nós ocultos e não tratou o conjunto completo de artigos de spam como um único lote de limpeza. A presença de conteúdo inteiro de apostas não deve ser confundida com a contagem das 36 publicações com nós ocultos. Não se demonstrou reinjeção durante esta operação.

- **Autolendpro:** 17 outras publicações ainda publicadas, todas HTTP 200 com indicadores; 16 objetos de cache adicionais ainda servem spam. Os caches se sobrepõem às publicações, não são 16 novos artigos.
- **Zionnmedia:** 16 outras publicações ainda publicadas, todas HTTP 200 com indicadores.
- **Índices adicionais:** 75 referências Yoast fora do target set: Autolendpro 36, Zionnmedia 38, Portal Brasil News 1. Parte aponta para registros ausentes; não equivalem a 75 publicações.
- IDs, títulos, URLs, caminhos e evidências exatos foram publicados na aba **Pendências limpeza** e persistidos em `additional-residuals.json`, `additional-posts-public.json`, `additional-cache-public.json`.
- Recomendação para decisão: backup e quarentena reversível das 33 publicações (rascunho, sem exclusão definitiva; revisar o conteúdo legítimo de Hello world), retirada dos 16 objetos de cache exatos, purge dirigido e saneamento das 75 referências SEO. A remoção dos 16 arquivos exige confirmação crítica explícita. Não executar até Rodolfo ampliar o escopo.
- Hardening e o vetor histórico da invasão continuam separados desta limpeza; o caminho de entrada não foi encerrado nem certificado.

## Sheet, infraestrutura e aprendizado

- Service Account canônica `mgsagent@mgs-core-prod.iam.gserviceaccount.com`, helper corporativo; Drive canEdit e Sheets validados.
- Snapshot antes da gravação; canário em célula vazia com restauração conferida; comparação prévia contra mudanças concorrentes; gravações RAW por células.
- 181 células preexistentes atualizadas; duas abas adicionadas (Limpeza e Pendências limpeza). Total atual: 12 abas, 25.209 células verificadas após formatação. Fórmulas e células não planejadas preservadas pelo readback integral.
- Procedimento salvo na skill Zeus `wp-plugin-mass-operation`, referência `wordpress-irrelevant-posts-incident-audit.md`: não confundir nós ocultos com todos os artigos contaminados, manifestos exatos, bloqueio de extensão de escopo, variantes HTML revisadas, predicados SQL vazios, transients de runtime e verificação de backup/Sheet.
- Utilitários one-shot ficaram no workspace restrito; nenhum cron ou daemon foi criado. Sem workers em background nesta execução.
- Falhas locais de coleta/validação corrigidas: comando de checkpoint com nome inválido; parser antigo não abrangia p/a/listas/texto sem href; predicado de slug vazio ampliava SELECT a drafts; comparação SQL de slugs foi tornada byte-exata; guardas de metadata distinguiram contadores/transients. Nenhuma dessas falhas autorizou escrita fora do manifesto. Dry-run, readback de produção e Sheet passaram após as correções.
