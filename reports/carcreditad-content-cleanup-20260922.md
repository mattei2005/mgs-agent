# Carcreditad — limpeza cirúrgica validada

> **Retificação pela segunda auditoria:** a remoção dos blocos/links do post_content e seus hashes foi confirmada, mas a afirmação ampla de limpeza concluída ficou incompleta. Permaneceram descrições sociais de apostas em dois HTMLs de cache e 93 referências no índice interno do Yoast. A fonte mais recente é `reports/carcreditad-second-audit-20260922.md`. O registro abaixo preserva o que foi executado e validado naquela fase; não é declaração atual de saneamento integral.

## Autoridade e limite

- Rodolfo autorizou em `1551777897759375400`, thread `1551768281688580096`, após explicação específica de limpeza das seis páginas e caches envolvidos.
- Executado: remover somente HTML de spam previamente identificado, preservar conteúdo legítimo, formulário, layout, anúncios e integrações; backups e readbacks.
- Não autorizado nesta fase e não executado: senhas, chaves/2FA, usuários/permissões, plugins/tema, PHP, firewall, exclusão de páginas/revisões ou alterações em outros sites.
- Auditoria anterior: `reports/carcreditad-security-audit-20260921.md`.

## Resultado

Seis páginas saneadas: 80 blocos de HTML injetado, contendo 97 links de spam, removidos dos conteúdos publicados.

- ID 3, Privacy Policy: 14 blocos / 16 links.
- ID 13, Contact Us: 12 blocos / 14 links.
- ID 61581, About Us: 12 blocos / 14 links.
- ID 61590, home - English: 15 blocos / 22 links.
- ID 61652, Cookie Policy: 16 blocos / 18 links.
- ID 61653, Terms of Use: 11 blocos / 13 links.

Os 80 blocos não são as 80 revisões históricas da auditoria: são contagens de conjuntos distintos. As revisões históricas foram preservadas como evidência e não devem ser restauradas automaticamente.

A página auxiliar home-English ficou com post_content vazio porque só continha os blocos injetados. Sua URL e registro continuam existentes. A homepage real usa show_on_front=posts, não essa página; HTML da homepage real permaneceu integralmente igual ao baseline.

## Método e segurança

1. Reconciliados identidade do webapp, tema, IDs/slugs/status, hashes do conteúdo auditado, engine InnoDB e ausência de object-cache.php.
2. Congelados backups individuais locais e remotos por página/cache.
3. Parser por offsets removeu somente span/div ocultos com links de domínios revisados. Nós protegidos (form/script/iframe/input/img) eram proibidos no conjunto removido. Nenhum byte externo aos intervalos foi reserializado.
4. Dry-run real em tabela temporária MariaDB: 6/6 hashes UTF-8 finais confirmados; nenhuma linha de produção alterada no teste.
5. Canário Contact Us: transação com lock, guardas de identidade/hash/rowcount e atualização apenas de post_content. Após HTTP 200 e preservação de formulário/scripts/iframe, aplicadas as outras cinco páginas.
6. Seis objetos de cache HTML foram saneados com as mesmas remoções, hashguard e substituição atômica, preservando owner/mode. Não houve exclusão de arquivos/diretórios nem purge global da aplicação.
7. Cloudflare: purge por lista das seis URLs exatas, HTTP 200/success=true. Nenhuma regra, DNS ou outra zona alterada.

Títulos, autores, slugs, status, datas/modificados e metadados das páginas foram preservados. O audit log é a fonte da data desta limpeza. Fingerprints de todas as linhas de posts foram comparados: somente os seis conteúdos autorizados mudaram.

## Validação final

- Banco: 6/6 conteúdos iguais aos hashes do plano, metadados de destino inalterados; demais post rows/conteúdos inalterados.
- Cache local: 6/6 arquivos iguais aos hashes limpos previstos; nenhum cache fora do alvo contendo os indicadores consultados.
- URLs públicas sem query: seis páginas HTTP 200, sem nenhum dos domínios maliciosos do conjunto; HTML inteiro exatamente igual ao baseline menos os fragmentos removidos.
- Homepage: HTTP 200 e HTML inteiro inalterado.
- Scripts externos, atributos de formulários e fontes de iframes: iguais ao baseline nas seis páginas e na homepage.
- Cachebuster: 6/6 HTTP 200 e limpas.
- Origem direta com hostname/SNI: 6/6 HTML limpo.
- XML-RPC permanece HTTP 403; ads.txt e sitemap_index.xml permanecem HTTP 200.
- Formulário de contato: markup preservado, sem submissão de teste. Código dos anúncios preservado; não foi simulada impressão/clique nem afirmada entrega comercial de anúncios.

## Backups e recuperação

No MatteiInc02, fora do webroot:

- `/var/backups/mgs-carcreditad-cleanup/20260922T021937Z-canary`: página 13 + seu HTML de cache.
- `/var/backups/mgs-carcreditad-cleanup/20260922T022039Z-batch`: outras cinco páginas + cinco HTMLs de cache.

Doze arquivos de backup tiveram hashes relidos e validados contra os manifests. Arquivos privados, diretórios restritos. Cada JSON contém conteúdo anterior e identificação da página; os caches originais têm o mapeamento do destino no manifest. Restaurar somente com CAS sobre o estado limpo conhecido e autorização apropriada; a versão anterior contém spam e não é um destino seguro por padrão.

Evidência privada local: `/root/.hermes/profiles/zeus/workspace/carcreditad-cleanup/`:

- `before.json`, `plan.json`, `backup-page-ID.json`, `page-ID.diff`;
- `dryrun.json`, `canary-result.json`, `canary-public.json`, `batch-result.json`;
- `after.json`, `backup-readback.json`, `cloudflare-purge.json`;
- `public-before.json`, `public-after.json`, `public-validation.json`, `variant-validation.json`.

## Pendências fora da limpeza

A limpeza do conteúdo está concluída; não equivale à remediação integral da invasão. Permanecem decisões sobre acesso rodmaster, versões vulneráveis, origem/PHP/isolamento, rastreabilidade e rotação controlada da chave WP2FA exposta no retorno técnico da auditoria anterior. Nenhuma dessas alterações foi presumida a partir da autorização de limpeza.

Procedimento reutilizável registrado em `wp-plugin-mass-operation/references/wordpress-irrelevant-posts-incident-audit.md`, seção de limpeza cirúrgica. Checkpoint, inventário e audit log registram a fase concluída e os limites restantes.
