# Provisionar domínio exclusivo de quizzes

Use após o preflight de domínio de entrada em SKILL.md, quando o pedido inclui hospedagem e painel independentes. Estado de sites, servidores, gestores e credenciais pertence às fontes canônicas; não transforme os exemplos da skill em inventário de produção.

## 1. Fixar escopo e preservar a origem

1. Registrar domínio novo, servidor/IP aprovados, modelos, gestores e REC externo. Se Rodolfo trocar o servidor, superseder o destino proposto no checkpoint antes de escrever; não alterar a origem para acomodar o novo IP.
2. Ler `home`, versão do plugin e `mgs_direct_quiz_landings` por WP-CLI na origem. Guardar a option completa e o pacote do plugin em área privada de trabalho para comparação; emitir somente projeções sem segredos.
3. Construir em código a matriz esperada de modelos × gestores. Preservar configurações e status da origem; uma variante inativa pode ser publicada no domínio novo quando a matriz completa foi solicitada.
4. Guardar os IDs e cada etapa concluída antes de validar a etapa seguinte. Um erro depois de criar app, banco ou item1Password exige reconciliar esses mesmos objetos, não repetir a criação.

## 2. Criar apenas a hospedagem necessária

1. Resolver a zona exata e a delegação NS; apresentar o diff DNS/SSL e as operações sensíveis concretas pela autoridade vigente. Reutilizar decisões já confirmadas de domínio/modelos/gestores/REC.
2. Validar acesso e webroot livre no servidor escolhido. SSH funcional na origem não comprova acesso ao destino.
3. Preferir o provisionamento gerenciado RunCloud. Se a API retornar429, respeitar `Retry-After`; o painel autenticado é uma alternativa validável, não licença para contornar o limite com outras credenciais API.
4. No painel, conferir conta e workspace antes de concluir que não há servidores: `Personal Space` pode estar vazio enquanto o servidor está num workspace compartilhado. Usar o login e eventual2FA pelo fluxo protegido da skill1Password.
5. Para um domínio dedicado, uma aplicação `Empty Web App` com PHP e Native NGINX pode hospedar o WordPress instalado depois por SSH. Conferir explicitamente owner, caminho público, domínio, ausência/presença dewww e opções de backup; não habilitar serviços pagos nem hosts adicionais por default.
6. Capturar e reler o ID do app, servidor e webroot assim que o painel concluir. Validar a existência real no servidor antes de instalar WordPress.
7. Criar credenciais exclusivas apenas com a autorização necessária e armazená-las no1Password. Para WP-CLI com senhas em stdin, seguir `wp-plugin-mass-operation/references/route-pack-02.md`, seção de prompts: capturar e suprimir stdout/stderr sensíveis. Não copiar usuários, tokens ou `wp-config.php` da origem.
8. Conferir o certificado real emitido antes de mudar o método de validação: AutoSSL pode escolher DNS-01 com uma integração existente e concluir de forma assíncrona. Um registro inicialmente sem validade não prova falha nem exige troca para HTTP-01. Validar certificado de origem e modo Cloudflare separadamente.

## 3. Instalar o produto e localizar mídia

1. Instalar uma versão canônica compatível do `mgs-direct-quiz`, registrar o pacote e manifestoSHA-256 e validar PHP no runtime do novo app. Não atualizar o plugin da origem por inferência.
2. Deduplicar as URLs de logo e imagens realmente usadas nas configurações. Importar no novo WordPress com `wp media import <url> --porcelain`; capturar o attachmentID e resolver `wp_get_attachment_url(ID)` em processo novo.
3. Criar um mapa URLorigem → URLlocal e aplicar somente aos campos de mídia. Preservar o REC externo e os links jurídicos aprovados; uma troca global de domínio pode apontar CTAs e páginas legais para rotas inexistentes.
4. Gerar IDs distintos e determinísticos para as novas configurações; definir idioma, gestor, slug e `active` conforme a matriz aprovada. Conferir destinos antes da gravação.
5. Gravar `mgs_direct_quiz_landings` no novo site e chamar `MGS_Direct_Quiz::sync_static_pages()`. Em WP-CLI, passar `--url=https://<dominio>` e validar os assetsHTTPS no resultado real.
6. Ler novamente option, versão ativa, manifesto do plugin e os arquivos físicos. Fazer backup privado final de banco e webroot fora da árvore pública, com permissões restritas e caminho de rollback registrado.

## 4. Provar a entrega

1. Para cada configuração esperada, fazer GET da URL limpa seguindo redirects e exigir URL efetiva correta, HTTP200, marker estático/versionado, zeroform/input e zero assets de tema/`wp-includes`. Conferir404 real numa rota inexistente.
2. Em Chromium mobile, verificar todas as rotas: quantidade de CTAs por modelo, imagens carregadas e ausência de overflow. Aplicar query sintética e exigir cada parâmetro exatamente uma vez em todos os CTAs, não só no primeiro link.
3. Fazer ao menos um clique real por modelo e confirmar o REC finalHTTP200 com os parâmetros preservados. ParaV3, testar também os viewports definidos em SKILL.md.
4. Comparar origem e alvo no mesmo viewport: textos, CTAs, fonte e geometria do card; guardar capturas distintas e inspecionar o visual. Não reescrever copy só por preferência do validador durante uma réplica.
5. Testar login e editor reais no painel, confirmar a lista ativa e os controles de criar/duplicar. Exercitar o ciclo estático em fixture isolada quando não for necessário criar resíduos de teste na produção; registrar separadamente o que foi comprovado por browser e por fixture.
6. Comparar a option da origem com o baseline para provar preservação. Agregar contagens em código e fechar somente após a matriz solicitada inteira, os backups e os registros canônicos estarem validados.
