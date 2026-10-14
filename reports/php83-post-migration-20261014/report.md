# Auditoria pós-migração PHP 8.3 — Mattei 01/02/03

Origem: Discord thread `1559601841036198031`, pedido `1559601841036198031`; aviso de conclusão por imagem `1559785169655697408`.

## Veredito

Migração confirmada ao vivo; aceite funcional global reprovado. Não há prova de que as falhas de roteamento tenham sido causadas pela troca de PHP. Nenhuma configuração de produção foi alterada por Zeus nesta auditoria.

## Cobertura e resultados

- API RunCloud: 109 WordPress, com distribuição 74/15/20, todos configurados em `php83rc`.
- PHP-FPM: serviço ativo nos três servidores, workers observados executando `/RunCloud/Packages/php83rc/sbin/php-fpm`.
- Bootstrap WordPress pelo PHP 8.3.33: 109/109 bem-sucedidos.
- Homepage com cache-buster na origem: 109/109 HTTP 200. Exceção de trust direto no certificado da origem de Wantabrand; diagnóstico de conteúdo usou `-k` explicitamente, sem chamar isso de validação TLS. HTTPS público de Wantabrand funcionou.
- Superfície pública: 105 homepages HTTP 200; Allincraft, Kievportal e Portalbrasilnews apresentaram desafio Cloudflare; `bkp2.ducapes.com` não resolveu no DNS público, embora a aplicação tenha respondido 200 na origem.
- Navegador: 218 cenários de homepage (desktop/mobile dos 109 apps) e 64 cenários de REC (desktop/mobile de 32 publishers com ao menos um destino saudável), total 282. Os seis cenários de desafio e os dois de DNS não são renderização funcional validada. Reabertura de Prospect e Newsoun Finanzas após settle confirmou conteúdo, descartando falso diagnóstico de tela branca. Allautolan exibe `Nothing Found`, sem erro fatal PHP visível. Sem baseline visual confiável, alterações visuais não foram classificadas como regressões da migração.
- SB: 54 publishers enumerados nas duas empresas MGS; 38 com pools, 482 pools, 4.285 entradas configuradas, 4.284 links distintos efetivamente testados. Readback final preservou IDs/nomes e identidades `route + utm_content` de todos os pools; URLs são dinâmicas e não constituem guarda de concorrência.
- Primeiro salto: 4.283 links redirecionaram preservando os sete parâmetros de teste. Quatro falhas 404 iniciais recuperaram em reteste; uma persistiu: `cv-car-br-001`, pool `753` / `cv-car-br-quiz-001`. Ela já estava `healthy=false` e com `utm_content` vazio; reteste com esse vazio literal e medium válido `g003-s` também retornou 404.
- Fim da cadeia: 3.507 links conduziram a páginas 200; 776 a destinos 404; um não resolveu a rota inicial. Estes números são links de teste, não volume de tráfego de usuários.
- Destinos configurados: 1.417 URLs distintas, 1.070 HTTP 200 e 347 HTTP 404, distribuídas em 12 hosts. Os 347 destinos quebrados constavam em entradas marcadas `healthy=true`; esse campo não substitui teste real.
- Diagnóstico dos 347: 305 pertencem à frota migrada e 42 ao Fincgriffin, fora dos 109 apps. Nas 305 URLs da frota: 299 associadas exclusivamente a posts `draft`; duas em Cephyric com `_wp_old_slug` ambíguo entre posts publicados e rascunhos; quatro aliases de rotas sem post/old-slug correspondente. O estado WordPress das 42 URLs Fincgriffin não foi certificado por acesso autenticado nesta auditoria.
- Parâmetros: 14 caminhos com página final 200 perdem a query em redirecionamentos WordPress 301. Distribuição: Ducapes 12, Helixenit um, Xyvlov um. Eles afetam 33 links distintos testados. Abrir a URL canônica diretamente é o canário recomendado antes de propor a correção dos destinos nas pools; não alterar redirects globais ou `_wp_old_slug` em massa.

## Falha de aplicação não encerrada

`receitasdescomplicada.com.br` continuou registrando fatals de timeout de 30 segundos em `wp-rocket/inc/Dependencies/RocketLazyload/Image.php:54`, seguidos de erros de output buffering, em requests de artigos. Homepage e bootstrap passaram, mas não certificam esses artigos. A mesma família de erro já existia nos logs históricos anteriores; a relação causal com PHP 8.3 não foi demonstrada. Não houve mudança em plugin/cache/configuração. É necessária uma remediação separada com canário/rollback, não simplesmente aumentar timeout.

## Pendências e recomendação

1. Corrigir primeiro as URLs legadas de conteúdo já publicado, preservando os pools/identidades e validando operações AdOps existentes; não republicar rascunhos automaticamente.
2. Separar decisão sobre conteúdo despublicado/pools legados da correção técnica de URLs. Restaurar conteúdo ou retirar pools altera escopo/estratégia e requer Rodolfo.
3. Investigar o canário de WP Rocket no Receitas Descomplicada antes de qualquer alteração em produção.
4. Não atribuir desafios Cloudflare, DNS de backup, homepage sem posts ou conteúdo em draft à migração sem baseline/evidência causal.

## Ocorrência de segurança da coleta

Uma resposta bruta excessiva de `/company` foi temporariamente salva no scratch e parcialmente incluída no resultado interno de ferramenta, contendo campos sensíveis de empresas não MGS. Zeus sanitizou o arquivo para uma allowlist MGS, corrigiu o coletor para descartar o objeto bruto e verificou que as mensagens Discord visíveis continham apenas progresso, sem esses valores. O trace interno não foi apagado; eventual tratamento desse registro/credenciais não está autorizado por esta auditoria. Não foram alteradas credenciais. Não reproduzir o payload bruto nem os valores em nenhum report.

## Artefatos e aprendizagem

Evidências selecionadas e sanitizadas ficam no diretório `evidence/` deste relatório. Manifesto e resumo são gerados por ferramenta. Procedimento reutilizável salvo em `smartbidding-dashboard-access/references/post-php-migration-routing-audit.md`: allowlist antes de persistir/logar, contagem exaustiva, validação da cadeia final, diagnóstico de drafts/old-slugs, logs por delta e settle do navegador.
