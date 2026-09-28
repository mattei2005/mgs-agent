# F010 — Fechamento de limpeza do portalbrasilnews.com

**Estado:** RESOLVIDA E VALIDADA  
**Janela operacional:** 2026-09-22/23 UTC  
**Domínio:** `portalbrasilnews.com`  
**Servidor:** RunCloud 01  
**Autorizações:** Discord `1552114009304727654`, `1552121110122864663` e `1552138883326672899`

## Problema

A auditoria histórica registrou 46.752 publicações incompatíveis. No início desta remediação, esse lote já não estava público, mas o banco ainda conservava 53.685 posts não publicados do mesmo ecossistema, além de páginas, taxonomias e índices derivados residuais.

A classificação ao vivo confirmou como conteúdo legítimo publicado somente 226 artigos financeiros e cinco páginas institucionais. O restante autorizado era composto por cassino/apostas, pharma, SEO externo, conteúdo estrangeiro incompatível, testes e objetos vazios.

## Escopos confirmados

- Principal: `4aee8706b83d24aec6919d9f78ced6cd5232e589d05bbf5902c0c13fa9a10f5e`
- Residual: `2729249c0cff7f9871c51bd17c187f8c7dc8951f5348e14009743f82df7055d7`
- Residual interno final: `87e0ce0c83992fe17b3ac8567afad858d028d87cc411bc4355c62547c360f5e5`

Cada escopo foi congelado por IDs/hashes, confirmado separadamente por Rodolfo e aplicado com backup, dry-run transacional, canário e lote.

## Exclusões aplicadas

### Conteúdo não publicado

- 53.685 posts:
  - 50.502 drafts;
  - 3.032 auto-drafts;
  - 132 trash;
  - 19 future.
- 9.370 revisões.
- 55.299 postmeta.
- 50.666 relações de categorias/tags.
- 226 comentários e 693 commentmeta.
- 260 indexables, 260 hierarquias e 134 links Yoast ligados diretamente ao primeiro conjunto.
- 41 eventos `publish_future_post` removidos após ficar comprovado que não restava conteúdo futuro legítimo.

### Segunda passada

- 106 páginas draft incompatíveis e 109 postmeta.
- 6 relações de taxonomia órfãs.
- 64.306 indexables Yoast sem objeto.
- 165.468 links Yoast órfãos.
- 488 categorias/tags sem uso, um termmeta e seus derivados Yoast.

### Passada interna final

- Três `term_taxonomy` sem termo correspondente e sem relações.
- 110 indexables de termos inexistentes.
- Dois contadores de taxonomia Elementor reconciliados com a relação real (`6→1` e `1→0`).

## Correção de segurança durante a operação

Uma validação intermediária revelou que o primeiro predicado de hierarquia Yoast tratava `ancestor_id=0` como ancestral ausente. No Yoast, zero é sentinela válido de raiz. Isso removeu linhas de hierarquia válidas junto com o resíduo.

A falha foi interrompida, diagnosticada e corrigida automaticamente:

- fonte de restauração: backup post-primary restore-tested;
- manifesto de reparo: 431 linhas válidas ausentes, SHA-256 `b403c809f5a2dc9a2d08d56e5661bf84b6918b4fc4ef25515f19fab46f4bbf21`;
- dry-run: 431 inserções com rollback;
- canário: uma linha;
- lote: 430 linhas;
- três linhas de raiz já haviam sido recriadas pelo runtime;
- estado final: 434 hierarquias válidas, 434 raízes e zero referência inválida.

O hash dos 231 conteúdos publicados permaneceu idêntico antes, durante e depois do reparo. A regra reutilizável foi adicionada à referência `wordpress-irrelevant-posts-incident-audit.md` da skill `wp-plugin-mass-operation`.

## Conteúdo preservado

- 226 artigos financeiros publicados.
- Cinco páginas institucionais publicadas.
- 166 mídias.
- Quatro usuários.
- Três categorias ativas e 195 tags ativas.
- Logs e evidências forenses.
- Estrutura válida do Yoast/Elementor.

SHA-256 canônico dos 231 posts/páginas publicados: `4b029a54b001dbb45a21c2b652b189d54ddfdb94dd9afb2bcb55225bcd7c429a`.

## Backups e rollback

Todos ficam fora do webroot, modo restrito e tiveram restauração real em banco temporário:

1. `portalbrasilnews-full-20260923T003010Z.sql.gz`
   - 248.828.270 bytes
   - SHA-256 `02fe96593621deda36db79cd7ec3abaf695ac80c88daba388982819003e11b1d`
2. `portalbrasilnews-post-primary-20260923T005736Z.sql.gz`
   - 23.731.436 bytes
   - SHA-256 `dd8f63d950fde991cfd663c21df5f07ea4ca490e149aba22b0a7fcbadbb3699d`
3. `portalbrasilnews-final-residual-20260923T020800Z.sql.gz`
   - 4.972.667 bytes
   - SHA-256 `46e0178ebb3b31949eeb96a1527d0866bcaa28c07eec27c54536e505e32db4fd`

Diretório: `/var/backups/mgs-portalbrasilnews-f010-20260922/`.

## Validação final

`final-validation.json`: **PASS**.

- 226 posts publicados; zero posts não publicados.
- Cinco páginas publicadas; zero páginas não publicadas.
- 166 anexos; zero revisões.
- Zero órfãos em posts, metadados, comentários, taxonomias, termos ou Yoast.
- Zero divergência de contadores de taxonomia.
- 431 linhas reparadas presentes; 434 raízes Yoast válidas no total.
- Core checksum: PASS.
- Plugins públicos checksum: PASS.
- `wp db check`: PASS.
- Nenhum PHP executável suspeito em uploads; nove `index.php` inertes foram preservados.
- Zero evento residual `publish_future_post`.
- WP object cache limpo.
- WP Rocket limpo pela função canônica `rocket_clean_domain`; zero arquivo no cache do domínio.
- Cloudflare purge: HTTP 200, com readback de auditoria.
- Origem:
  - home, REST e artigos legítimos: HTTP 200;
  - IDs/slugs removidos testados: HTTP 404.
- A borda continua retornando HTTP 403 ao IP do auditor por Managed Challenge; a origem foi validada diretamente.

## Evidências

Workspace: `/root/.hermes/profiles/zeus/workspace/portalbrasilnews-resolution-20260922/`

Artefatos principais:

- `target-manifest.json`
- `residual-manifest-authorized.json`
- `final-residual-manifest-authorized.json`
- `backup-manifest.json`
- `residual-backup-manifest.json`
- `final-residual-backup-manifest.json`
- `hierarchy-repair-manifest.json`
- `final-validation.json`
- receipts de dry-run, canário e lotes
- receipts de cache e Cloudflare

## Conclusão

F010 está **RESOLVIDA E VALIDADA**. O domínio conserva apenas o conteúdo financeiro e institucional publicado, sem rascunhos/lixeira/futuros, sem resíduos relacionais ou SEO órfãos e com a hierarquia válida do Yoast restaurada e verificada.
