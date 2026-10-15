# TopFeed Yoast — diagnóstico e papel WordPress

Autoridade: Rodolfo Mattei, mensagem `1560362232821588084`, thread `1560319225732669606`.

## Resultado verificado

- Domínio: `finanzas.topfeed.fun`.
- Instalação real: Inc01 `162.55.28.178`, `/home/runcloud/webapps/finanzas-topfeed`, owner `runcloud`; `home` e `siteurl` exatos confirmados.
- Login existente: `/rodloguda/` (opção WPS Hide Login lida; não houve login de navegador).
- Usuário `atena`, ID7: Editor → Administrator. Snapshot anterior em `host-preflight.txt` e `role-change.txt`; rollback nativo apenas de papel para Editor, mediante autoridade aplicável. Fingerprint de senha/email/application-passwords permaneceu idêntico. Readback independente WP-CLI e REST confirmou Administrator e `manage_options=true`.
- Item existente 1Password `noggitrwqhnr4llqlcfv4xq5gq`: somente metadata `wp_role=administrator` alinhada; readback confirmou todos os demais campos preservados. Nenhuma credencial criada/rotacionada.
- `core/get-site-info`: HTTP200 após promoção.
- `yoast-seo/get-seo-scores` e `get-readability-scores`: HTTP200 com GET query `input[number_of_posts]=11`. Falhas intermediárias400 ocorreram porque GET sem query/input em JSON body não é lido pelo controlador; contrato nativo inspecionado e transporte corrigido. As abilities exigem gestão Yoast e apenas consultam scores já persistidos; a resposta contém títulos antigos, não valida os11novos rascunhos.
- `OPTIONS` pós-promoção: só entradas `_yoast_wpseo_focuskw`, `_yoast_wpseo_title`, `_yoast_wpseo_metadesc`; promoção não registra campos de resultado REST.
- Manifesto dos11IDs novos verificado via WP-CLI:54104,54106,54108,54110,54112,54114,54116,54118,54120,54122,54124. Todos continuam `draft`, hashes de conteúdo idênticos ao manifesto, metas de resultado ausentes e score SEO/legibilidade0 nas respectivas linhas `yoast_indexable`. Não são notas calculadas de reprovação; são resultados ainda não persistidos.
- Locale WordPress e usuário: `pt_BR`; idioma não alterado. Yoast28.3. Contexto de análise espanhol precisa ser validado pelo executor editorial antes de persistir.
- GET RunCloud alvo recebeu429; failover para SSH existente com hostkeys fixadas resolveu identificação sem rotação nem expansão a outros hosts.

## Limites e continuidade

Zeus encerra a alteração de papel; não alterou posts, publicação, scores, plugins, temas, runtime ou locale. Atena mantém execução editorial e comunicação na origem. Próximo passo: usar a instalação real para análise genuína dos mesmos11IDs, validar contexto espanhol e fazer canário de persistência/readback nativo antes de ampliar; não repetir criação de posts. Client local que fixa `wp_role=editor` deve reconhecer a mudança autorizada ID7/site, sem rebaixar a conta ou pedir nova credencial.

## Evidências

Diretório privado da solicitação: `/root/.hermes/profiles/zeus/work/topfeed-yoast-1560319225732669606/`.

- `preflight.json`, `host-preflight.txt`, `role-change.txt`, `role-independent-readback.txt`.
- `abilities-query-input-success.json`, `native-ability-contract.txt`.
- `administrator-meta-schema.json`, `new-posts-readonly-layers.json`, `vault-role-metadata-readback.json`.

Aprendizado reutilizável salvo na skill própria `wp-plugin-mass-operation`, referência `yoast-abilities-role-diagnostics.md`; nenhuma skill de Atena foi alterada.
