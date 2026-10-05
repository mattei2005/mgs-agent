# Zionn Media — reauditoria após recuperação

Data: 2026-10-04T15:59:31.804967+00:00. Solicitante Rodolfo, mensagem 1556330029301112976, thread 1556015743831646349. Domínio confirmado no histórico: zionnmedia.com (dois n). Execução foreground, read-only em produção; nenhuma remediação, renovação, nova credencial ou envio real de formulário.

## Veredito
Site disponível e camada Elementor funcionando, mas auditoria REPROVADA para limpeza/segurança e qualidade integral. Há spam SEO oculto servido pela homepage e dependências antigas com CVEs aplicáveis. A recuperação visual anterior não foi certificação de segurança; esta reauditoria identifica uma lacuna concreta daquela validação.

## Cobertura e achados
- 5 páginas principais × desktop 1440x900 e celular 390x900 = 10 casos; todas HTTP 200, zero imagens quebradas, zero overflow, zero exceção JavaScript. Menu home abre/fecha; logo permanece no domínio. As dez combinações não são um teste manual WCAG nem aceite visual do proprietário.
- Homepage: 16 anchors de apostas turcas posicionados em top/left -9999px. Fonte: page 5489, _elementor_data, widget text-editor ec36b28. Hash atual d8b767f5cfe637949b7ec33eb19e83d5cb39cbefe1bd6441b31e562134181f42 é idêntico ao baseline de recuperação; trata-se de resíduo histórico que ficou público ao reativar builder, não prova de invasão nova. Mesma configuração de spam agrupada em 1 hash de settings; distribuição de cópias: {'page:publish': 1, 'revision:inherit': 64}. Não removido neste pedido de auditoria. Autoria/vetor original não atribuídos.
- 35 fontes HTTP de matteiservicesinc.com bloqueadas como mixed-content em todas as cinco páginas; fonte confirmada nos três CSS locais roboto/montserrat/robotoslab. URI http://www.w3.org/2000/svg em CSS é namespace, não request inseguro.
- Cinco páginas sem meta description; três sem H1 acessível (Privacy, Terms, Contact). Yoast instalado porém inativo. Sitemap core contém seis URLs: cinco páginas e author/rmmaster; arquivo de autor e categoria vazios respondem 200 sem noindex. Templates Elementor consultados redirecionam para home; não foram classificados como vazamento separado.
- Axe 4.11.0: 7 regras e 58 ocorrências únicas por página/regra/seletor, sem somar viewport duplicado: contraste, landmark/main, landmarks duplicados, link sem nome, distinção de link no texto, H1 e conteúdo fora de landmarks.
- Lighthouse amostra laboratorial canônica: mobile 55/100 e desktop 58/100; LCP 19.04s e 5.06s. Não são Core Web Vitals de visitantes.
- Contact usa marca Digital Trust, copyright 2023; outras páginas usam Zionn e 2025. Terms contém resíduo “Plumber” e jurisdição inválida “laws of Zionn Media”. Privacy efetiva 2022, descreve ecommerce/newsletter/analytics não comprovados no runtime e contém link jogoshoje.io com 404. Não é parecer jurídico.
- DOM final Direct contact e email são mailto corretos; /cdn-cgi/l/email-protection 404 no crawl bruto é fallback Cloudflare e não link quebrado real após decodificação. Outros destinos DNS/502 da home pertencem aos links de spam, não à navegação legítima. 403 externo mysql.com do readme é controle/bot e não link morto provado.
- Form home possui nome/email requeridos e sem upload; CF7 Contact labels e required via ARIA/plugin, não HTML required nativo. checkValidity true nesse CF7 não prova envio vazio nem funcionamento de entrega. Nenhum email ou lead real enviado. Sem cookies nem requests Google/Meta/DoubleClick observados nos contextos frescos; ausência de banner isolada não foi transformada em infração legal.

## Segurança, integridade e regressões
- Core 7.1.2 checksums PASS. GeneratePress 3.4.0: 142/142 arquivos idênticos ao ZIP oficial da mesma versão.
- 16 plugins instalados, seis ativos. Checksum nativo: dez verificados, um com três arquivos extras de storage do All-in-One Migration, cinco comerciais sem checksum público. Arquivos extras e comerciais não foram tratados como malware nem certificado de origem. Cinco árvores da unidade visual idênticas ao clone pré-cutover. MU compat com SHA-256 74f75bcfb361726c13435f5fe207f823e28f374c9a948dd250bfd51612fe6629 preservado.
- PowerPack 2.9.9: CVE-2026-42629 em versões <2.13.0. Sete handlers legados bloqueados: 14 POSTs público/origem, todos 403. Mitigação narrow não certifica todas as CVEs.
- ElementsKit Lite 3.1.3: CVE-2024-37255, <=3.1.4, corrigido 3.2.0. Fonte get_content_editor sem capability check, rota live /elementskit/v1/dynamic-content com permission_callback __return_true; não invoquei ação mutante. Também CVE-2024-8546, XSS contributor+, <=3.2.7, corrigido 3.2.8. Existe editor no inventário de usuários; role requerida é alcançável por uma conta existente, não por registro público (desabilitado).
- Elementor Pro 3.21.0: CVE-2024-4107 contributor+, corrigido 3.21.2, e CVE-2024-35656 reflected XSS <=3.21.2. CVE-2026-32475 upload/RCE <=4.2.1 exige campo upload opcional em formulário publicado: nenhum desses campos apareceu nas páginas e builder coletados; não classificado como RCE demonstrada neste site.
- PHP 8.1.34, branch sem suporte upstream atual; não atualizado. Fonte oficial php.net/supported-versions.php.
- Zero executáveis PHP/phtml/phar/php5 em uploads. Não há declaração de servidor integralmente limpo: não foi uma perícia de todos arquivos, tarefas OS, usuários/sessões, banco inteiro ou incident response.
- Quatro tabelas dirigidas CHECK TABLE OK. Conteúdo/builder/status das cinco páginas, footer oficial, widgets inativos e active_plugins iguais ao baseline. Contadores de todas categorias zero; nenhum post editorial publicado. Backups SQL prévios presentes com hashes originais; importação validada historicamente, não repetida neste turno.
- nginx-rc, apache2-rc, php81rc-fpm, MariaDB, firewalld e fail2ban ativos. Disco 14% usado na coleta; log atual de aplicação sem fatals no intervalo disponível. “nginx” não é o nome real do serviço RunCloud; o primeiro probe desse nome genérico foi corrigido por discovery, não tratado como outage.
- TLS público validado, TLS1.3, certificado até 27/12/2026; origem validou certificado e conteúdo. HTTP/www redirecionam. Headers nosniff/SAMEORIGIN presentes; HSTS/CSP/Referrer-Policy não observados. Cache Cloudflare DYNAMIC e cache local vazio; não há evidência de cache excessivo como causa central.

## Limitações e recomendação
Prioridade 1: limpeza exata do widget oculto e contenção/atualização ElementsKit com canário/rollback, sem redesign. Depois corrigir fontes, metadados/H1/acessibilidade e coerência de identidade/legal. Unidade comercial Pro/PowerPack não deve receber upgrade cego; entitlement e canário de compatibilidade permanecem gates próprios, sem assumir renovação obrigatória para renderizar. Mudanças de routing/indexabilidade, licença/billing, credenciais, arquivos de sistema e exclusões seguem seus gates específicos.

## Coleta, aprendizado e continuidade
Falhas recuperadas: preflight venv sem requests (browser com Playwright já disponível; HTTP via curl), collector WP eval sem global $wpdb (corrigido e repetido), skill research com nome ambíguo (rota categorizada), search DDGS ausente com failover real Exa; extração das fontes funcionou. NVD CVE-2026-42629 retornou registro indisponível apesar do índice de busca, por isso a conclusão usa advisory completo Wordfence. Output de browser/revisões inicialmente volumoso foi agregado; evidência preservada em arquivo, não no fechamento executivo.
Aprendizado adicionado e readback realizado em wordpress-plugin-integrity-audits/references/complete-wordpress-site-reaudit.md: baseline preservado não equivale a clean e reativação de builder exige varrer links ocultos e clusterizar revisions.
Evidência: /root/.hermes/profiles/zeus/workspace/zionn-reaudit-20261004; summary.json e artefatos completos. Nenhum executor background iniciado. Próximo passo depende de Rodolfo autorizar remediação delimitada.

## Fontes públicas de vulnerabilidades
- https://www.wordfence.com/threat-intel/vulnerabilities/wordpress-plugins/elementskit-lite/elements-kit-elementor-addons-314-missing-authorization
- https://www.wordfence.com/threat-intel/vulnerabilities/wordpress-plugins/elementskit-lite/elementskit-elementor-addons-327-authenticated-contributor-stored-cross-site-scripting-via-video-widget
- https://www.wordfence.com/threat-intel/vulnerabilities/wordpress-plugins/powerpack-elements/powerpack-pro-for-elementor-v2130-missing-authorization
- https://nvd.nist.gov/vuln/detail/CVE-2024-4107
- https://nvd.nist.gov/vuln/detail/CVE-2024-35656
- https://www.wordfence.com/threat-intel/vulnerabilities/wordpress-plugins/elementor-pro/elementor-pro-421-unauthenticated-arbitrary-file-upload-via-upload-field-array-validation-bypass
