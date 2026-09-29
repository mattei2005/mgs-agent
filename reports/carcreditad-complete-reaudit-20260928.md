# Carcreditad — auditoria integral read-only

## Autoridade e escopo

- Solicitante: Rodolfo Mattei; autorização Discord `1554312217124540507`; thread `1551768281688580096`.
- Alvo: `carcreditad.com`, RunCloud MatteiInc02 (`288158`), webapp `2735760`, raiz `/home/runcloud2/webapps/carcreditad`.
- Execução: leitura pública, origem, Cloudflare, RunCloud, WordPress admin, SSH permanente autorizado, filesystem completo, banco, logs, checksums, navegador desktop/mobile, axe e Lighthouse.
- Produção: **zero gravações administrativas**. GETs normais podem gerar logs/cache/métricas, mas nenhum conteúdo, arquivo, plugin, configuração, credencial, regra ou serviço foi alterado.

## Conclusão executiva

Não foi confirmado malware ativo nem reinjeção atual dentro da cobertura. A limpeza anterior permanece efetiva: zero domínios/termos de spam conhecidos em 166 rotas HTML e zero candidatos atuais no banco; core e 20/20 plugins verificáveis passaram nos checksums oficiais.

O domínio, porém, **não está pronto para encerramento**. Há sete achados P1 e três P2. Os principais são: página espanhola em HTTP 500; analytics/ads e cookies opcionais antes de consentimento apesar da promessa legal de banner; seis plugins em faixas com correções de segurança pendentes; 7 administradores com apenas 1 TOTP; PHP 8.1 EOL; origem contornando Cloudflare; privilégios globais de banco em dez outras contas; e ausência de restore-test completo atual de filesystem + banco.

## Cobertura saudável confirmada

- WordPress `7.1.2`; core checksum PASS. Único extra de raiz esperado: `ads.txt`.
- Plugins: `20/20` checksums oficiais PASS; 22 componentes inventariados contando 2 MU-plugins.
- Filesystem: 13.495 arquivos, 1.934 diretórios e 1,24 GB hashados integralmente; zero world-writable, zero symlink, zero PHP disfarçado e zero assinatura heurística ativa. Os seis PHP em uploads são `index.php` vazios de proteção.
- Tema CompanyBRs 7.3: 16/16 arquivos de código antes coletados permanecem byte a byte iguais; `functions.php` e `page-home.php` preservam seus hashes históricos. Integridade contra pacote canônico continua não certificada porque é tema personalizado.
- Banco: 25 tabelas, 26,7 MB, `wp db check` PASS, zero trigger/event, zero post/opção com obfuscação detectada, dois WPCode draft sem termos de execução/rede.
- Conteúdo: 165/166 rotas HTML HTTP 200; 209 links internos testados sem destino não-2xx; query de campanha preservou UTM, `fbclid` e `gclid`.
- Segurança pública: XML-RPC 403 na borda e origem; `.env`, `.git`, `.user.ini`, uploads PHP e backups de configuração bloqueados/ausentes; HTTP e `www` redirecionam para o apex HTTPS.
- TLS: borda Cloudflare e origem com certificados válidos; TLS 1.2/1.3 funcionais.

## Achados P1

### F032-01 — Home espanhola HTTP 500

`/es/home-espanol/` retorna 500 na borda, cache-bust e origem. O fatal atual é determinístico:

- `functions.php:409` declara `companybrs_lang_query_args()`;
- `page-home.php:24` declara a mesma função novamente;
- o fatal encerra em `page-home.php:39`.

A página 61595 está publicada, vazia, usa `_wp_page_template=page-home.php` e permanece no sitemap. Nenhum link interno atual aponta para ela. Os hashes das duas fontes não mudaram desde a auditoria anterior: é defeito legado do template, não reinjeção.

### F032-02 — Consentimento inexistente apesar da promessa legal

Em contexto de navegador limpo, antes de qualquer escolha:

- 8 requests opcionais para Google Ads/GTM/GA;
- cookies `_ga` e `_ga_R0B9L58FXR` criados;
- zero banner/seletor de consentimento encontrado.

As políticas EN/ES dizem que haverá banner e que usuários EEA darão consentimento explícito antes de cookies não essenciais. O runtime contradiz o texto publicado e a afirmação de Consent Mode v2.

### F032-03 — Seis plugins em faixas afetadas

- Ad Inserter `2.8.15` → `2.8.19`: CVE-2026-9280 e faixas `<=2.8.16` dos CVE-2026-11984/11900; primeira correção relevante 2.8.17.
- Spectra `2.19.26` → `2.20.4`: CVE-2026-12900 afeta `<=2.19.28`, corrigido 2.19.29. O CVE-2026-16302 exige Spectra Pro + Instagram, precondição não observada.
- WPCode Lite `2.3.4` → `2.3.9`: versão `<=2.3.5` com RCE Author+, corrigida 2.3.6.
- Yoast SEO `27.1.1` → `28.5`: CVE-2026-3427 afeta `<=27.1.1`, XSS Contributor+.
- Polylang `3.8.3` → `3.8.10`: antecede correções de XSS e exposição de metadados em 3.8.4/3.8.6/3.8.8.
- WP Fastest Cache `1.4.9` → `1.5.2`: faixa 0.8.7.7–1.5.0 vulnerável a cache poisoning não autenticado por tracking parameters.

Há também nove atualizações rotineiras e uma atualização de tema inativo. O site tem um Editor e sete Administradores; vulnerabilidades Contributor+/Author+ são operacionalmente alcançáveis se uma dessas contas for comprometida. Isso é correlação de exposição, não prova de exploração.

### F032-04 — Acesso e 2FA

- 7 administradores + Atena Editor.
- Somente `rmmaster` possui TOTP presente; duas contas estão explicitamente “Required but not configured” e as demais não têm cadastro concluído.
- Sessões atuais: Raquel e rmmaster.
- Application passwords atuais: Atena API e Zeus API.
- `DISALLOW_FILE_EDIT` ausente; editores de tema/plugin aparecem no admin.
- REST público enumera `dev`, `raqueloliveira` e `rmmaster`.
- A chave de criptografia WP2FA exposta no contexto técnico anterior ainda não foi rotacionada. Rotação sem recriptografia/recadastro pode bloquear usuários e permanece Critical Subset.

### F032-05 — Risco estrutural no host compartilhado

- PHP `8.1.34` está fora das branches suportadas pelo PHP oficial.
- 9 WordPress compartilham o usuário Unix `runcloud2`.
- 10 contas MariaDB não sistêmicas conservam privilégios globais como SUPER, FILE e escrita. A conta própria do Carcreditad está corretamente limitada ao schema, mas privilégios globais das outras contas alcançam o banco local.
- RunCloud expõe regra global 3306, embora MariaDB esteja atualmente em loopback.
- SSH efetivo: `PermitRootLogin yes` e `PasswordAuthentication yes`.
- Host com reboot pendente: kernel em execução `5.15.0-187`; imagem 191 instalada, 194 candidata; 28 pacotes visíveis e 25 serviços marcados pelo needrestart.

Esses itens são compartilhados com outros sites e não podem ser corrigidos como efeito colateral de um patch WordPress.

### F032-06 — Cloudflare/origem

- Origem `162.55.28.179` diretamente acessível, certificado Let’s Encrypt público e corpo igual ao edge: controles apenas na Cloudflare são contornáveis.
- Cloudflare: `ssl=full`, não Strict; `min_tls_version=1.0`; Always Use HTTPS off; WAF managed free presente, campo legado `waf=off`.
- Respostas públicas/origem têm X-Frame-Options e nosniff, mas faltam HSTS, CSP, Referrer-Policy e Permissions-Policy.

### F032-07 — Recuperação integral não certificada

- Backups cirúrgicos da limpeza anterior: 18 arquivos / 1,21 MB, hashes lidos.
- Backup de consolidação de usuário: 7.166 bytes, `0600`, gzip PASS, SHA `a852398e…`.
- Não há restore-test atual de filesystem completo + banco completo.
- API RunCloud de backups devolveu 403/404 no caminho/credencial disponível.

## Achados P2

### Frontend e acessibilidade

- Home EN/ES solicita `/images/hero-bg.svg` e recebe 404. A causa é `critical.css` injetado inline mantendo URL relativa; o SVG existe dentro do tema.
- 24 visualizações renderizadas: 23 violações axe / 55 nós.
  - ARIA inválido no menu desktop: 11 nós;
  - contraste: 40 nós;
  - links de avatar sem nome: 4 nós.
- As políticas EN/ES excedem o viewport mobile em 10 px.
- Sem `<main>` no Lighthouse da home.

### Desempenho

- Mobile: performance 42; FCP 3,7s; LCP 20,9s; TBT 960ms; 4,1 MiB.
- Desktop: performance 94; FCP 0,6s; LCP 1,2s; TBT 20ms.
- O Lighthouse estima 2,9 MiB de economia de imagens no mobile; PNGs da home concentram o peso.

### SEO e links

- 77/165 rotas HTML saudáveis sem meta description: 66 tags, 8 páginas, 2 categorias e 1 autor.
- Home EN/ES compartilham título genérico `Car Credit Ad -`.
- Link Progressive em post 6703 retorna 404; URL oficial atual encontrada em `https://www.progressive.com/answers/refinancing-a-car-loan/`.
- Post Santander 52315 usa link HTTP.
- `readme.html` e `license.txt` estão públicos.
- CTAs “Read more” genéricos e dois anchors de menu sem href reduzem SEO/navegação acessível.

## Mudança concorrente reconciliada

A auditoria anterior registrava 347 revisões e a preservação de 80 revisões contaminadas; hoje existem 267 e nenhum indicador conhecido. Também não existe mais o usuário legado `rodmaster` ID 2.

A origem foi reconciliada: a consolidação WordPress autorizada por Rodolfo na mensagem `1551988658741977161` removeu uma conta legada do Carcreditad, reatribuiu 304 posts e criou `rmmaster` ID 8. O backup exato continua presente e íntegro. Portanto, a diferença é ação concorrente autorizada, não anomalia não atribuída.

## Ordem recomendada para remediação

1. Criar backup integral atual de filesystem + banco e provar restore isolado.
2. Corrigir somente a duplicação do template da página 61595, preservando layout/home e validando EN/ES.
3. Atualizar os seis plugins de segurança; depois os nove rotineiros, com rollback e regressão de conteúdo, anúncios, tracking e idiomas.
4. Implementar consentimento real antes de GA/GTM/Ads e reconciliar a promessa legal/Consent Mode v2.
5. Corrigir SVG, acessibilidade, overflow, links, metadados e imagens.
6. Tratar PHP/OS/reboot, SSH/firewall, Cloudflare Strict/TLS/headers/origin e privilégios MariaDB em transações compartilhadas separadas.
7. Rotacionar a chave WP2FA somente com plano Critical de recadastro/recriptografia e revisão de admins/sessões/application passwords.

## Limites e fontes externas

- Nenhuma exploração de escrita foi executada.
- Ausência de assinatura não prova ausência absoluta de malware; a conclusão vale para filesystem completo hashado, banco, checksums, logs e navegadores cobertos.
- Advisories: Wordfence CVE-2026-9280, CVE-2026-11984, CVE-2026-11900, CVE-2026-12900 e CVE-2026-16302; Patchstack WPCode <=2.3.5; NVD CVE-2026-3427; WPScan `b6f8be96-13d9-497a-8e57-5a65b519958b`; changelog oficial Polylang.
- PHP suportado: https://www.php.net/supported-versions.php

Resultado: auditoria integral read-only concluída; produção preservada; remediação não aplicada neste escopo.
