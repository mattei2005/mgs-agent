# Auditoria completa — Spazio Kitchens and Baths

- Operação: `ZEUS-SPAZIO-COMPLETE-REAUDIT-20260927B`
- Observação: 2026-09-27 UTC
- Alvo: `https://spaziokitchensandbaths.com`
- Modo: auditoria somente leitura; nenhuma alteração persistente no site, banco, Cloudflare, RunCloud, Nginx, firewall, pacotes ou serviços
- Acesso interno: dois ciclos SSH temporários explicitamente autorizados; ambos removidos com GET `404`, lista final em zero, autenticação recusada e chaves locais eliminadas

## Resultado executivo

O site está disponível e renderiza corretamente em desktop e mobile, sem imagens quebradas, mixed content, overflow, fatal atual ou exposição pública sensível confirmada. TLS público, headers, redirecionamentos, arquivo de verificação `[REDACTED]`, backups e serviços estão operacionais. Não foi encontrada evidência confirmada de malware, webshell, usuário desconhecido ou persistência não autorizada dentro da cobertura.

A auditoria não classifica o site como pronto: existem pendências relevantes de segurança de plugins, privacidade/legal, indexação de conteúdo de demonstração, acessibilidade, desempenho e tracking.

## Prioridade 1

### 1. Plugins com vulnerabilidades conhecidas e autenticadas

- Elementor Free está em `3.31.2`. O CVE-2025-11220 afeta versões até `3.33.3`: XSS armazenado explorável por usuário Contributor ou superior, CVSS 6.4.
- Slider Revolution está em `6.7.36`. O CVE-2025-9217 afeta versões até `6.7.36`: leitura arbitrária de arquivos por usuário Contributor ou superior, CVSS 6.5; versão corrigida indicada: `6.7.37`.
- O site tem três administradores e uma conta Editor. A pré-condição autenticada reduz exposição externa, mas uma conta comprometida já atende ao nível exigido.
- Elementor Free e Pro estão hoje alinhados em `3.31.2`; o WordPress oferece Free `4.3.2`, mas não oferece atualização do Pro. Atualizar apenas o Free quebraria o princípio de unidade de compatibilidade. O par permanece congelado até existir pacote Pro compatível e canário aprovado.
- Fontes: NVD/OpenCVE para CVE-2025-11220 e NVD/Patchstack para CVE-2025-9217.

### 2. Privacidade e base legal não representam a operação real

- A página de Privacy Policy contém texto do fornecedor do tema: AxiomThemes, Envato, Ticksy, empresa no Chipre e hospedagem na Alemanha.
- Não foi localizada página de Terms.
- Google Analytics/Ads, Meta e DoubleClick criaram `_ga`, `_fbp`, `_gcl_au` e `IDE` na primeira visita; nenhuma interface de consentimento/escolha apareceu nas 2 execuções da home.
- Há dois links quebrados dentro da Privacy Policy: `eugdpr.org` indisponível e uma URL antiga do YouTube retornando `404`.
- Conclusão: risco de conformidade e transparência; não é um parecer jurídico.

### 3. Tracking server-side com falha reproduzível

- O iframe de service worker do host Stape customizado retornou `404` em 3 de 3 execuções: home, contato e Privacy Policy.
- O defeito não impede o site de renderizar, mas pode degradar ou interromper parte da mensuração server-side/Google Tag Manager.

## Prioridade 2

### SEO e conteúdo

- Crawl: 17 sitemaps, 276 URLs de sitemap e 290 páginas testadas; `290/290` responderam `2xx`.
- 163 documentos HTML analisados:
  - 152 sem meta description;
  - 111 sem H1;
  - 7 com múltiplos H1;
  - 27 URLs `/layouts/` retornam `200` e estão `index,follow`;
  - 56 páginas contêm conteúdo demonstrativo/placeholder;
  - 636 ocorrências de `href` vazio.
- A Privacy Policy também faz parte das 56 páginas com resíduos demonstrativos.
- Os três grupos aparentes de título/canonical duplicados são aliases que passam pelos 6 redirecionamentos `301` válidos; não são páginas duplicadas acionáveis.
- Canonicals faltantes: zero. JSON-LD inválido: zero. Mixed content: zero. ALT ausente: `0 de 1.864` imagens.
- Robots responde `200` e aponta para o sitemap. O arquivo de verificação `[REDACTED]` responde `200`, 54 bytes e conteúdo exato; nenhuma string de verificação ficou visível nas páginas.

### Acessibilidade automatizada

- Matriz: 18 execuções, desktop e mobile, 9 rotas; `18/18` com HTTP `2xx`, zero page error, zero imagem quebrada e zero overflow.
- axe-core 4.13.0: 127 instâncias de violação e 490 nós afetados:
  - 4 críticas;
  - 59 sérias;
  - 64 moderadas.
- Regras recorrentes: links sem nome acessível, contraste, `tabindex` positivo, região rolável sem foco por teclado, iframe do Google Maps sem título, ARIA inválida, ordem de headings, ausência de landmark `main` e conteúdo fora de landmarks.
- Isto é cobertura automatizada, não certificação WCAG; navegação por teclado, foco visível e leitor de tela ainda precisam de validação manual.

### Desempenho laboratorial

- Lighthouse 13.5.0, home:
  - Mobile: Performance `30`, Accessibility `84`, Best Practices `69`, SEO `92`.
  - Desktop: Performance `47`, Accessibility `84`, Best Practices `73`, SEO `92`.
- Mobile: FCP `16,7 s`, LCP `30,2 s`, TBT `1.450 ms`, CLS `0,024`.
- Desktop: FCP `2,7 s`, LCP `6,9 s`, TBT `250 ms`, CLS `0,089`.
- Transferência aproximada: 4,0 MiB; economia estimada: ~204–207 KiB de CSS e ~607–612 KiB de JavaScript não usados.
- TTFB laboratorial da home foi baixo (`30–40 ms`); o gargalo observado é frontend/terceiros, não origem.
- Estes números são laboratório, não Core Web Vitals reais de usuários.

## Segurança, integridade e host

### Positivo e validado

- WordPress `7.1.2`, PHP `8.3.33`, Ubuntu `22.04.5 LTS`, kernel `5.15.0-194-generic`.
- Zero pacotes pendentes, zero reboot pendente, zero unidades falhas; Nginx, MariaDB, PHP-FPM, unattended-upgrades, Fail2ban, Postfix, RunCloud Agent e rsyslog ativos.
- `wp-config.php` em `0640`, `WP_DEBUG=false`, `DISALLOW_FILE_EDIT=true`.
- XML-RPC bloqueado com `403`; enumeração REST de usuários retorna `404`; endpoints de plugins/temas exigem autenticação.
- TLS público válido: TLS 1.2/1.3 aceitos e TLS 1.0/1.1 rejeitados. Certificado público com hostname válido; origem usa Cloudflare Origin CA, esperado para Cloudflare→origem e não para confiança pública direta.
- CSP, HSTS, Referrer-Policy, Permissions-Policy, X-Content-Type-Options e X-Frame-Options presentes no HTML público e na origem.
- TRACE retorna `405`.
- 39.919 arquivos e 6.236 diretórios, 4,41 GiB, foram percorridos e hashados. Zero world-writable, zero SUID/SGID no webroot, zero symlink, zero PHP em uploads e zero arquivo PHP disfarçado.
- O nome alarmante `wp-includes/Text/Diff/Engine/shell.php` pertence ao core oficial; não foi classificado como webshell.
- Os dois achados heurísticos no Really Simple SSL pertencem a arquivos que passaram no checksum oficial.
- Core WordPress sem arquivo oficial modificado: diferenças limitadas a `readme.html` removido por hardening e arquivos extras intencionais (`robots.txt`, verificação `[REDACTED]` e configuração local de cache).
- `20/24` plugins públicos passaram no checksum. Elementor Pro, Slider Revolution, TRX Addons e TRX Updater não têm checksum público disponível; mapas SHA-256 completos foram preservados. Seis árvores privadas/proprietárias e dois temas foram mapeados integralmente.
- Dez snippets WPCode mantêm exatamente os mesmos IDs e hashes da auditoria confiável anterior; zero adicionado, removido ou alterado.
- Nenhuma assinatura direta de malware foi confirmada. ClamAV, rkhunter e chkrootkit não estão instalados; nenhum pacote foi instalado durante a auditoria.

### Superfície e capacidade

- Portas externamente alcançáveis: `22`, `25`, `80`, `443` e `34210`.
- `34210` é necessária ao agente RunCloud, mas a documentação oficial recomenda limitá-la aos IPs da RunCloud; o teste atual confirmou alcance externo genérico.
- `25/TCP` também está global e o domínio usa MX da Zoho; deve-se confirmar se entrada SMTP no VPS é realmente necessária antes de manter a exposição.
- SSH atual: root desabilitado, senha desabilitada, somente chave; Fail2ban ativo. O volume histórico mostra forte pressão de brute force, mas nenhuma conta desconhecida foi encontrada.
- Disco: `81,4%` utilizado, 6,25 GiB livres. RAM: 957 MiB total, 246 MiB disponíveis. A própria documentação RunCloud recomenda 2 GiB ou mais para produção com tráfego/cache/backups.
- O banco possui prefixo ativo `wpr1_`, mas mantém conjunto legado `wp_` com aproximadamente 101 MiB. Isso é resíduo/rollback provável, não deve ser removido sem comparação, backup e manifesto destrutivo.

## Backups e controle

- RunCloud: servidor e aplicação online; PHP `php83rc`; zero credenciais SSH remanescentes.
- Três snapshots completos consecutivos, todos `COMPLETED`:
  - 2026-09-27: banco 104,26 MB; aplicação 1,52 GB;
  - 2026-09-26: banco 104,58 MB; aplicação 1,52 GB;
  - 2026-09-25: banco 104,74 MB; aplicação 1,67 GB.
- Arquivos locais protegidos de recuperação continuam íntegros e com teste gzip aprovado: filesystem ~4,18 GiB e banco ~14,6 MiB.
- Cloudflare: zona ativa, não pausada; apex e `www` proxied; DNS foi lido com TXT sanitizado.
- O token aprovado retornou `403` para settings da zona; valores internos de SSL/TLS/Brotli/obfuscation não foram certificados pelo control plane. O comportamento público de TLS e headers foi validado independentemente.

## Comportamento público final

- Browser final: `16/16` execuções aprovadas.
- Home `200`; contato `200`; verificação `[REDACTED]` `200` e 54 bytes.
- Zero fatal atual no navegador, zero imagem quebrada, zero mixed content, zero referência ao host legado e zero overflow.
- O histórico de Nginx contém fatals de Elementor em 25/09 antes da correção. Não houve novo fatal PHP após aquele ponto; os três `500` mais recentes em 27/09 foram POSTs automatizados para `wp-comments-post.php`, sem impacto observado nas páginas auditadas.

## Não acionáveis/esperados

- `/wp-json/oembed/1.0/embed` sem parâmetros: `400` esperado.
- REST user oculto: `404` esperado.
- XML-RPC: `403` esperado.
- Respostas externas `429` durante auditoria de links: rate limiting, não link quebrado.
- Certificado Cloudflare Origin CA não confiável pela trust store pública: comportamento esperado para origem protegida.
- O comando UFW ficou sem resposta; o host usa regras nft/RunCloud. A cobertura do firewall foi fechada por `nft` (274 linhas), API RunCloud e probes externos.

## Ordem recomendada de correção

1. Segurança: reconstruir/atualizar Slider Revolution para `>=6.7.37` e planejar atualização sincronizada Elementor Free+Pro com pacote Pro canônico, backup e canário.
2. Privacidade: substituir a política de demonstração por documento real da Spazio, criar Terms e implementar consentimento/Consent Mode antes de cookies de analytics/ads.
3. Tracking: corrigir o endpoint Stape e validar eventos em browser + server-side.
4. SEO/conteúdo: noindex/retirar/redirecionar layouts e demos que não devem ranquear; depois corrigir descriptions, H1 e links vazios nas páginas efetivamente mantidas.
5. Acessibilidade: corrigir os 12 tipos de regra, priorizando ARIA crítica, nomes de links, teclado, contraste e iframe do mapa.
6. Performance: reduzir JS/CSS, terceiros e peso inicial; repetir Lighthouse e coletar dados de campo.
7. Infra: limitar `34210` aos IPs oficiais RunCloud, decidir sobre `25/TCP` e `22/TCP`, avaliar aumento para 2 GiB de RAM e criar manifesto separado para eventual descarte das tabelas `wp_`.

Cada mudança de plugin, conteúdo, tracking, firewall, capacidade ou banco deve ser uma fase separada, com backup, canário, rollback e readback. A auditoria não executou essas remediações.

## Evidências principais

- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/post-public-crawl.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/post-browser-validation.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/browser-quality-accessibility-audit.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/lighthouse-mobile.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/lighthouse-desktop.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/seo-content-accessibility-audit.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/external-links-audit.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/network-tls-http-audit.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/control-plane-readonly-audit.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/internal-deep-reaudit.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/internal-retry-readback.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/internal-reaudit-lifecycle-receipt.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-complete-reaudit-20260927b/internal-retry-lifecycle-receipt.json`
