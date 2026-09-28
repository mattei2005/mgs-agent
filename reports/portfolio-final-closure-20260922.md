# Fechamento final da limpeza — oito domínios — 22/09/2026

## Resultado executivo

**Limpeza operacional dos achados F001–F008 concluída e validada.** Conteúdo confirmado foi preservado em rascunho, trechos legítimos foram mantidos, caches correlatos foram removidos, Cloudflare foi purgada e os artefatos de acesso paralelo do Folhadaterra foram retirados após backup. O fechamento não atribui autoria nem certifica, em sentido forense, o vetor original dos incidentes.

Autorizações finais:

- Conclusão autônoma: `discord:1551768281688580096/1552029385127890975`.
- Exclusão exata de três artefatos Folhadaterra e quatro caches Autolendpro: `discord:1551768281688580096/1552043681878384641`.
- Remoção do backup de configuração exposto e rotação de credenciais/salts Folhadaterra: `discord:1551768281688580096/1552056417274568785`.

## Conteúdo e SEO

- Revisão final de todos os 14.421 registros que estavam marcados como preservados/inconclusivos na planilha.
- 14.572 registros adicionais convertidos de `publish` para `draft`: Portal 14.541; Mobileapp 14; Seniormenu 6; Zionnmedia 4; Apexwallet 3; Autolendpro 3; Tapsaga 1; Folhadaterra 0.
- O Portal terminou com o conjunto publicado exato de 231 posts/pages classificados como legítimos. Nos demais domínios, os conjuntos publicados foram confrontados integralmente com as listas preservadas.
- 28.144 linhas `yoast_seo_links` e 14.547 `yoast_indexable` adicionais removidas para os alvos finais, com backup.
- Acumulado dos lotes desta investigação: 50.769 posts/pages colocados em rascunho, sem exclusão definitiva, além de sete saneamentos cirúrgicos anteriores.

## Arquivos e cache

- Folhadaterra: além dos 11 arquivos do primeiro lote, foram removidos, após backup e confirmação específica:
  - `wp-admin/user/chankro.so` — ELF Chankro/`LD_PRELOAD`;
  - `wp-admin/user/acpid.socket` — comando de apoio ao artefato;
  - `wp-admin/user/test.txt` — resíduo do mesmo diretório/cadeia.
- Autolendpro: quatro HTMLs de cache que ainda serviam três páginas colocadas em rascunho foram removidos após backup. Nova varredura: zero cache correlato; permalinks e IDs retornam 404; homepage e REST retornam 200.
- Cloudflare: purge global concluído com HTTP 200 nas cinco zonas acessíveis — Portal, Seniormenu, Tapsaga, Zionnmedia e Autolendpro. Apexwallet e Mobileapp permanecem sem zona nos escopos dos tokens aprovados.

## Folhadaterra — configuração exposta e rotação

A verificação posterior encontrou `wp-config.php.bak.20260826183335` no webroot. O acesso público via Cloudflare retornava 403, mas a origem entregava o arquivo completo em HTTP 200. O arquivo continha a mesma senha de banco e as mesmas nove chaves/salts usadas pela configuração ativa. Não houve ocorrência nos access logs disponíveis; ausência de log não prova ausência histórica de acesso.

Após confirmação específica:

- o arquivo foi copiado para backup restrito e removido do webroot;
- a senha do usuário MariaDB exclusivo do site foi rotacionada;
- `AUTH_KEY`, `SECURE_AUTH_KEY`, `LOGGED_IN_KEY`, `NONCE_KEY` e respectivos salts, além de `WP_CACHE_KEY_SALT`, foram rotacionados;
- a credencial nova foi criada e relida no 1Password como `MySQL - folhadaterra.com.br - production`;
- a senha antiga foi testada e rejeitada;
- o novo acesso ao banco, `wp option get home`, homepage e REST foram validados;
- o efeito esperado foi invalidar sessões WordPress anteriores do Folhadaterra.

Backup/rollback restrito: `/var/backups/mgs-portfolio-final-closure-20260922/folhadaterra.com.br/credential-rotation/`.

## Validação final

- Dry-run de 14.572 alvos, seguido de canários em um app de cada servidor e lotes limitados.
- Readback integral dos 14.572 registros e dos conjuntos publicados preservados dos oito domínios.
- 29 conjuntos de backup relidos por hash, 14.572 linhas de post restauradas em amostras de tabelas temporárias de sete bases.
- 180 requisições de origem a alvos retirados da publicação: todas 404/410.
- 74 requisições de origem a controles preservados: todas 200 após redirects.
- Home e REST: HTTP 200 nos oito domínios.
- XML-RPC: HTTP 403 no Mobileapp e Portal; bloqueios previamente autorizados continuam ativos.
- Folhadaterra: verificação oficial do core passou; os 11 arquivos originais e os três artefatos adicionais estão ausentes. Os avisos restantes são extras conhecidos/legítimos ou protegidos; o backup de configuração exposto não aparece mais.
- Cache correlato final: zero arquivo encontrado nos oito domínios.

## Planilha canônica

Planilha: https://docs.google.com/spreadsheets/d/1_8vUodLSgxfIj0vW0DlDpvljHFgygfI8A5Txc_Mc858/edit

- O fechamento F001–F008 foi atualizado via Service Account canônica e helper `mgs_google_workspace_auth.py`.
- 14.421 linhas antes marcadas como `PRESERVADO / revisão pendente` passaram a `TRATADO — rascunho`.
- Os 14.572 alvos finais aparecem exatamente uma vez em `Saneamento completo`; a aba soma 50.706 registros históricos de execução.
- Quatro registros de arquivos/segurança foram adicionados em `Arquivos`.
- Criada e validada a aba `Fechamento final`, com oito domínios e total executivo.
- `Prioridades`, `Resumo`, `Limpeza`, `Revisão restante`, `Pendências limpeza`, `Preservados revisão`, `Saneamento completo` e `Arquivos` foram relidos após a escrita.
- Recibo: `workspace/portfolio-final-closure-20260922/sheet-final-verified.json`; canário restaurado e `readback=true`.

## Estado visual da planilha

Após o encerramento, a apresentação visual foi corrigida para não confundir criticidade histórica com risco atual:

- as oito linhas F001–F008 estão verdes;
- a coluna passou a se chamar `Estado atual / criticidade histórica`;
- os rótulos agora começam por `RESOLVIDA`, preservando a severidade original em texto;
- `Resumo`, `Limpeza`, `Fechamento final` e as 14.421 linhas encerradas de `Preservados revisão` receberam sinalização verde;
- sete abas relacionadas receberam tab color verde;
- canário em `Prioridades!B2` e readback integral aprovados.

Recibo visual: `workspace/portfolio-final-closure-20260922/sheet-colors-verified.json`.

## Backups e evidência

- Backups finais: `/var/backups/mgs-portfolio-final-closure-20260922/` nos servidores correspondentes.
- Workspace restrito: `/root/.hermes/profiles/zeus/workspace/portfolio-final-closure-20260922/`.
- Evidências principais: `validation-db-backup.json`, `origin-http-validation.json`, `cache-inventory.json`, `critical-removed.json`, `folha-rotation-receipt.json`, `folha-core-after.json`, recibos de aplicação e purga Cloudflare.

## Limite remanescente

O escopo operacional solicitado está concluído: não resta conteúdo F001–F008 aguardando classificação ou autorização. Permanece uma limitação forense: os dados disponíveis não demonstram de forma conclusiva a autoria nem um único vetor original para todos os domínios. O bloqueio XML-RPC do Mobileapp e Portal continua sendo contenção temporária, não prova de que esse endpoint foi o único vetor. Nenhum resultado deste fechamento deve ser interpretado como atribuição a usuário, IP ou agente específico.
