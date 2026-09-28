# Spazio — auditoria integral pós-reboot

Data: 2026-09-25
Escopo: SpazioVPS `157.230.212.128` / RunCloud server `266820` / webapp `1376648` / `spaziokitchensandbaths.com`
Modo: auditoria somente leitura em produção, com credencial SSH Ed25519 temporária aprovada na mensagem Discord `1553059031457734657`.

## Resultado executivo

O reboot foi concluído e a infraestrutura voltou saudável. A auditoria integral não encontrou evidência de malware, webshell, PHP em uploads, arquivo disfarçado, diretório/arquivo world-writable, processo suspeito ou serviço quebrado. O banco passou no `wp db check`; o site responde, não há fatal pós-reboot e as páginas representativas renderizam em desktop e mobile.

O ambiente, porém, ainda não está tecnicamente limpo. Foram confirmados resíduos de atualização em dois plugins, um desvio da configuração conservadora do W3 Total Cache, referências antigas do domínio de teste, links/assets quebrados e resíduos históricos públicos. Esses itens não foram alterados nesta fase porque a autorização recebida delimitou a auditoria como somente leitura.

## Reboot e infraestrutura

- Boot ID novo: `b4ceaea0-cec7-4a0c-8648-2742c418bd60`.
- Kernel: `5.15.0-194-generic`.
- Sistema: Ubuntu `22.04.5 LTS`.
- Pacotes APT pendentes: `0`; simulação APT: `0` installs, `0` removals.
- Reboot pendente: não.
- Unidades systemd falhas: `0`.
- Serviços ativos: Nginx RunCloud, PHP `8.3.33`, MariaDB, RunCloud Agent, cron, Fail2Ban, Postfix e unattended-upgrades.
- SSH efetivo: root login desativado, senha desativada, chave pública ativa, X11 desativado.
- Banco `3306` restrito a loopback; firewall e Fail2Ban ativos.
- Logs de Nginx/PHP/MariaDB desde o boot: zero fatal, panic, segfault ou permission denied.
- Credenciais temporárias ao fim: `0`; a chave usada na auditoria foi revogada e o login com ela deixou de funcionar.

## Cobertura de integridade

- Manifesto SHA-256 de `42.536` arquivos e `8.959` diretórios.
- Volume efetivamente hasheado: `4.778.717.273` bytes.
- Arquivos/diretórios world-writable: `0`.
- Symlinks no webroot: `0`.
- PHP em uploads: `0`.
- PHP disfarçado/double extension: `0`.
- Heurísticas de código: dois matches em Really Simple SSL; o plugin passou no checksum oficial, portanto classificados como implementação legítima do pacote, não malware.
- Seis nomes sensíveis encontrados eram arquivos administrativos legítimos de plugins verificados, não shells.
- Scanners de terceiros não foram instalados; a conclusão usa manifesto integral, checksums oficiais, heurísticas, banco, processos e logs.

## WordPress e banco

- WordPress: `7.1.2`.
- Tema ativo: Pantry Child `1.0`; tema pai Pantry `1.4.0`.
- Plugins: `24` ativos, `7` must-use e `2` drop-ins.
- Elementor e Elementor Pro permanecem em `3.31.2`, conforme determinação de não atualizar.
- `wp-config.php`: owner/grupo `runcloud`, modo `0640`, `WP_DEBUG=false`, `DISALLOW_FILE_EDIT=true`, oito salts presentes e sem include externo.
- Banco: `wp db check` aprovado; sem triggers/eventos suspeitos, sem application password, quatro usuários institucionais esperados e nenhuma credencial exposta no relatório.
- Core checksum: todos os arquivos presentes coincidem; o único desvio é `readme.html` ausente, remoção de hardening deliberada já inventariada. Por isso o comando retorna `1`, mas não há arquivo core modificado.

## Achados técnicos confirmados

### 1. W3 Total Cache fora do perfil conservador aprovado

Estado live:

- Page cache: `true`.
- Browser cache: `true`.
- Database cache: **`true`**.
- Minify, object cache, fragment cache, lazy load, CDN e Varnish: `false`.
- `advanced-cache.php`: presente.
- `object-cache.php`: ausente.
- `db.php`: presente e idêntico ao drop-in oficial do W3TC `2.10.6` (`SHA-256 0221a85d...`).

O database cache deveria estar desativado. O desvio explica a criação de `db.php`. Não é malware, mas viola o perfil aprovado e adiciona complexidade/IO em uma VPS de 1 GB.

### 2. Elementor em árvore mista

O cabeçalho ativo continua `3.31.2`, mas o checksum oficial encontrou **1.186 arquivos extras**. Não houve arquivo esperado ausente ou modificado: todos os achados são `File was added`, compatíveis com resíduos de uma tentativa de atualização posterior. O Elementor Pro não foi alterado.

A correção segura é reconstruir atomicamente somente o diretório do Elementor Free a partir do pacote oficial exato `3.31.2`; isso não é atualizar o Elementor.

### 3. GTM4WP em árvore mista

`duracelltomi-google-tag-manager` está em `1.22`, mas contém **104 arquivos extras**, novamente apenas `File was added`. A correção é reconstruir a versão oficial exata `1.22`, sem migrar para `2.0.3`.

### 4. Fontes Elementor apontando para domínio antigo por HTTP

Três CSS gerados em `wp-content/uploads/elementor/google-fonts/css/` contêm `240` ocorrências de `http://srv250.teste.website/~spazio`. Em 16 execuções renderizadas, isso produziu `3.690` bloqueios de mixed content para `28` URLs únicas de fontes. O navegador usa fallback; por isso a página parece estilizada, mas as fontes locais corretas não são carregadas.

O dry-run do banco encontrou `0` ocorrências desse host: a origem está nos CSS gerados. A correção indicada é backup + regeneração de CSS do Elementor + limpeza do cache, seguida de validação das URLs únicas no browser.

### 5. Referências antigas `/~spazio/`

- O dry-run literal inicial encontrou **39 substituições potenciais** de `/~spazio/` para `/`, mas esse número cobria somente a representação não escapada.
- O primeiro canário técnico, posteriormente revertido, provou que esse recorte era insuficiente: as estruturas JSON válidas contêm **2.558 URLs protocol-relative** em `218` registros `_elementor_data` e mais **56 URLs** em `40` células JSON do RevSlider, totalizando **2.614 URLs estruturadas**.
- Distribuição Elementor: `23` registros publicados, `5` privados e `190` inherit (`188` revisões + `2` anexos). Três `_elementor_data` inválidos não contêm `~spazio` e ficam fora do alvo.
- Logs históricos do Check Email possuem `34` linhas com o texto, mas são evidência histórica e ficam explicitamente excluídos da correção.
- Filesystem/cache: `332` ocorrências em `16` arquivos, incluindo page cache W3TC e os CSS de fontes.
- Duas imagens do slider retornam `404`:
  - `/~spazio/wp-content/uploads/revslider/slider-1/236_1-1-copyright1.jpg`
  - `/~spazio/wp-content/uploads/revslider/slider-1/236_1-2-copyright1.jpg`
- Há links públicos quebrados para `/pricing/`, `/portfolio-properties/` e quatro rotas antigas sob `/~spazio/services/`.

O cache não é a única origem: requisições origin com query única ainda exibem as referências. A correção segura exige travessia e regravação JSON estrutural de Elementor e RevSlider; um search-replace literal isolado não fecha o problema.

### 6. Resíduos públicos e históricos

- ZIP público em uploads: `wp-content/uploads/2023/10/slider-2023-10-10__16-55-21.zip`, `1.014.394` bytes, HTTP `200`.
- `.htaccess.backuply`: `6.328` bytes.
- `.tmb/`: diretório histórico de thumbnails.
- `.user.ini`: arquivo vazio.

Não foram apagados. Devem ser removidos somente com backup, busca de referências e confirmação destrutiva.

### 7. Conteúdo/layout publicado incompleto

Confirmado por Playwright, DOM e extração pública:

- A home exibe como texto: `google-site-verification: google07e230f5394f9de3.html`.
- `/our-services/` exibe o shortcode bruto `[mc4wp_form id="461" element_id="style-10"]`; o plugin MC4WP não está instalado.
- A página Our Services ainda contém textos `lorem ipsum`, categorias de template de mobiliário e contadores zerados.
- A home também mostra contadores zerados e grandes áreas vazias; não houve fatal, overflow horizontal ou `<img>` quebrado, mas o conteúdo visual precisa de decisão editorial/design.
- `503` imagens no crawl não possuem `alt`, pendência de acessibilidade/SEO.

Esses itens são problemas de conteúdo/design, não efeito do reboot. Não devem ser reescritos automaticamente sem referência editorial.

### 8. Atualização disponível

- Header Footer Elementor: `2.9.4 → 2.9.5`.
- Elementor Free: atualização disponível, mas permanece deliberadamente bloqueada em `3.31.2`.

## Auditoria pública e browser

- Sitemaps: `17`.
- URLs de sitemap: `276`.
- Páginas testadas por HTTP: `299`; `290` retornaram 2xx; as nove falhas foram classificadas e estão nos links legados acima ou em rotas auxiliares, sem fatal global.
- Assets testados: `1.308`; `1.295` aprovados.
- Browser real: `16/16` páginas representativas retornaram `200` em desktop/mobile.
- Fatal visual: `0`; page errors: `0`; overflow horizontal: `0`; `<img>` quebrado: `0`.
- Falhas próprias confirmadas no browser: duas URLs de slider, além das fontes bloqueadas por mixed content.
- O `404` repetido do iframe `uknjybjh.sab.stape.io` pertence a integração externa, não ao servidor Spazio.

## Pacote de correção recomendado

Executar transacionalmente, com backup e rollback:

1. Desativar `dbcache.enabled`, aplicar o environment do W3TC, remover o drop-in `db.php` pelo próprio lifecycle do plugin e validar page/browser cache.
2. Restaurar árvores oficiais exatas do Elementor Free `3.31.2` e GTM4WP `1.22`; manter Elementor Pro intacto e validar checksums/canários.
3. Fazer backup do banco e substituir estruturalmente, dentro dos JSONs válidos, as `2.558` URLs Elementor e `56` URLs RevSlider; excluir os `34` registros históricos do Check Email e os três JSONs inválidos sem referência.
4. Regenerar CSS/local fonts do Elementor, restaurar os três CSS com URLs canônicas se o gerador não os recriar, limpar W3TC e purgar no Cloudflare somente essas três URLs CSS; provar zero requests ao host antigo e zero mixed content.
5. Atualizar Header Footer Elementor `2.9.4 → 2.9.5` em canário separado.
6. Quarentenar/remover ZIP público, `.htaccess.backuply`, `.tmb/` e `.user.ini` vazio após busca final de referências.
7. Corrigir tecnicamente os links `pricing`/`portfolio-properties` somente após mapear o destino desejado.
8. Tratar home/Our Services em uma etapa editorial separada: texto de verificação visível, shortcode órfão, lorem ipsum, contadores e espaços vazios.

## Estado final desta fase

- Produção alterada pela auditoria: **não**. Um primeiro canário técnico passou nas validações internas, mas falhou no navegador por causa da subcontagem das referências escapadas; o rollback integral foi executado e validado antes desta revisão.
- Credencial temporária remanescente: **0**.
- Site/infra em funcionamento: **sim**.
- Auditoria concluída: **sim**.
- Remediações acima: pendentes de confirmação explícita, pois incluem configuração de cache, substituição atômica de árvores de plugin, search-replace de banco e remoção de arquivos.

## Remediação autorizada e aplicada — estado supersessor

Autorização de ampliação e purge seletivo: mensagem Discord `1553073563852869655`.

O estado “pendente” acima foi supersedido pela execução transacional concluída:

- backup/rollback final: `/home/runcloud/.mgs-backups/spazio-tech-remediation-20260925T161220Z`;
- Elementor JSON: `2.558` URLs substituídas em `218` registros válidos;
- RevSlider JSON: `56` URLs substituídas em `40` células válidas;
- total estrutural: **2.614 URLs**;
- três JSONs inválidos sem referência foram preservados;
- os `34` registros históricos do Check Email foram preservados e excluídos da alteração;
- pós-check estrutural: zero referência legada em Elementor/RevSlider e zero ocorrência pública/origem/browser de `/~spazio/`;
- Elementor Free reconstruído com o pacote oficial exato `3.31.2`;
- Elementor Pro preservado ativo e intacto em `3.31.2`;
- GTM4WP reconstruído em `1.22`;
- Header Footer Elementor atualizado em canário para `2.9.5`;
- W3 Total Cache ativo em `2.10.6`, com page/browser cache ativos e minify/database/object/fragment/lazy-load/CDN/Varnish desativados;
- `advanced-cache.php` presente; `db.php` e `object-cache.php` ausentes;
- `240` referências em três CSS foram corrigidas para o domínio canônico; `28` fontes afetadas e `85` fontes totais foram verificadas localmente, sem arquivo ausente;
- o Cloudflare recebeu purge seletivo somente dos três CSS. A primeira chamada sem query eliminou as variantes-base; o browser revelou que as variantes com `?ver=` ainda estavam retidas. As mesmas três URLs, agora com as queries exatas, foram purgadas e retornaram `MISS`, HTTP `200`, hash idêntico à origem e zero host antigo;
- ZIP público, `.htaccess.backuply`, `.tmb/` e `.user.ini` vazio foram movidos para a quarentena do backup após busca de referência igual a zero;
- serviços `nginx-rc`, `php83rc-fpm`, MariaDB, RunCloud Agent, Fail2Ban e cron permaneceram ativos;
- banco, core e checksums previstos passaram; a única exceção do core segue sendo a remoção deliberada de `readme.html`.

### Falhas intermediárias e recuperação

- Duas tentativas do cutover ampliado pararam em validações fail-closed do conjunto de CSS: primeiro porque o backup continha cinco CSS, embora somente três fossem afetados; depois porque os cinco CSS referenciavam `85` fontes no total, enquanto `28` pertenciam aos três afetados.
- Em ambas as tentativas o rollback automático passou integralmente antes do retry.
- A validação foi corrigida para preservar os cinco arquivos, exigir exatamente três afetados, `240` substituições, `28` fontes afetadas e `85` fontes totais. O terceiro cutover terminou aprovado.
- A primeira execução do browser após o purge-base encontrou as variantes query-string ainda no edge. O purge foi refeito sobre as mesmas três folhas com as queries exatas; o browser subsequente passou.

### Validação final

- Validação consolidada público/origem: **PASS** em todos os gates.
- Browser real: `16/16`, HTTP `200`, zero fatal, zero page error, zero imagem quebrada, zero overflow, zero `/~spazio/`, zero `srv250.teste.website` e zero mixed content.
- Assets administrativos W3TC: `176/176` HTTP `200` (`88/88` público + `88/88` origem).
- Crawl final: `17` sitemaps, `291` páginas e `1.307` assets; zero fatal, zero mixed content e zero página sem canonical.
- Os quatro HTTPs de página ainda classificados são conhecidos e fora desta autorização de destino editorial: `/pricing/`, `/portfolio-properties/`, `/hardware/` e a rota auxiliar Cloudflare `/cdn-cgi/l/email-protection`.
- Os quatro HTTPs auxiliares de asset são conhecidos/esperados: email decoder Cloudflare, oEmbed sem parâmetros, usuário REST oculto pelo hardening e XML-RPC bloqueado.
- Imagens sem alt: `499`; permanece pendência editorial, não falha técnica do cutover.
- Credenciais SSH temporárias após a conclusão: **0**; chaves temporárias revogadas.

Artefato de validação consolidada: `/root/.hermes/profiles/zeus/workspace/spazio-tech-remediation-20260925/final-validation.json`.
