# Carcreditad — conclusão da limpeza dos resíduos

## Autoridade e escopo

Rodolfo autorizou limpar os resíduos na mensagem `1551795786193575979`, thread `1551768281688580096`, e indicou que a home não estava configurada. Esta etapa limitou-se aos resíduos de spam. Configuração da home e código do tema foram explicitamente preservados; o erro funcional anteriormente observado não foi tratado como invasão nem incluído no reparo.

## Executado e validado

- Removidas as duas meta tags `og:description` contaminadas dos objetos HTML de cache de `/contact-us/` e `/home-english/`. A renderização atual sem cache já não emitia essas descrições. Fora dessas tags, os bytes do cache foram preservados.
- Removidos somente os 93 registros de URLs maliciosas identificados em `wp_yoast_seo_links`, com IDs, URL/domínio, post_id e hash da linha conferidos. DELETE transacional com locks e guardas de hash/count; nenhuma tabela sofreu DROP/TRUNCATE.
- Preservados e comparados por readback os 434 registros legítimos restantes do índice.
- Purge Cloudflare exclusivamente das duas URLs afetadas; HTTP 200/success=true. Sem purge global ou mudança de DNS/regras.
- Dry-run em tabela temporária aprovado antes da alteração real. Canário Contact Us validado publicamente antes de concluir a outra página e o índice.

## Evidência final

- 880 registros de posts/revisões mantiveram os hashes anteriores; nenhum conteúdo, título, slug, status ou data de modificação foi alterado nesta fase.
- 26 arquivos do tema ativo mantiveram os hashes anteriores.
- home/siteurl/template/stylesheet/show_on_front/page_on_front/page_for_posts permaneceram iguais.
- Dois caches correspondem exatamente aos hashes limpos previstos; scripts e atributos dos formulários preservados.
- Verificação repetida das 95 URLs publicadas: zero ocorrências dos domínios maliciosos conhecidos e zero metadados com os indicadores de cassino/apostas consultados.
- Respostas HTTP: 94 URLs com 200; `/es/home-espanol/` permanece com o 500 previamente diagnosticado, fora do reparo por orientação do usuário. Não foi presumido 404 como status técnico medido.
- As duas páginas reparadas passaram também em requisição sem cache e diretamente à origem, sem os indicadores de spam.
- As 80 revisões históricas contaminadas e os backups foram preservados como evidência, sem restauração automática. O resultado não significa eliminação de evidência histórica nem remediação integral das vulnerabilidades.

## Backup/rollback

Backup privado verificado no MatteiInc02:
`/var/backups/mgs-carcreditad-cleanup/20260922T032519Z-residual`.

Contém JSON integral das 93 linhas originais, os dois HTMLs anteriores e manifest. Os três arquivos tiveram hash confirmado por leitura independente. Os backups contêm material contaminado e não devem ser restaurados automaticamente. Restauração eventual deve conferir ausência dos IDs removidos e os hashes do cache atual, preservando quaisquer alterações concorrentes autorizadas.

Nenhum arquivo/diretório foi excluído. Não houve alterações de senha, chave, usuário, permissão, plugin, PHP, firewall ou outros sites.

## Fontes e continuidade

- Evidência privada: `/root/.hermes/profiles/zeus/workspace/carcreditad-residual-cleanup/`.
- Artefatos: `before.json`, `plan.json`, `dryrun-result.json`, `canary-result.json`, `canary-public.json`, `finish-result.json`, `after.json`, `backup-readback.json`, `cloudflare-purge.json`, `public-validation.jsonl`, `variant-validation.json`.
- Esta etapa resolve os achados 1 e 2 de `reports/carcreditad-second-audit-20260922.md`; preserva o relatório anterior como histórico e supersede somente o estado pendente daqueles resíduos.
- A configuração/reparo da home permanece fora do escopo conforme Rodolfo. Riscos de permissões SQL, acessos, plugins/PHP e chaves continuam separados e não foram implicitamente autorizados pela limpeza.
