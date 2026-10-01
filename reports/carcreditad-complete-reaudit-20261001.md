# CarCreditAd — nova auditoria integral read-only

## Escopo e autoridade

- Pedido: Rodolfo Mattei, Discord `1555278827981246596`, thread `1551768281688580096`.
- Alvo: `carcreditad.com`, RunCloud `MatteiInc02` (`288158`), webapp `2735760`, raiz `/home/runcloud2/webapps/carcreditad`.
- Comparação: baseline integral de `2026-09-28`.
- Cobertura: público, sitemap, edge/origem, TLS, Cloudflare, RunCloud, navegador desktop/mobile, axe, Lighthouse, WordPress autenticado, filesystem, banco, usuários/2FA, plugins/tema/MU, logs, cron, host, rede e recuperação.
- Produção: **nenhuma correção ou outra escrita administrativa foi aplicada**. GETs de auditoria geraram apenas logs/cache/métricas normais.

## Conclusão executiva

A limpeza anterior permanece efetiva. Não foi confirmada nova reinjeção, malware ativo, WPCode executável, spam conhecido no conteúdo, trigger/evento de banco ou modificação de core/plugins/tema. Core e `20/20` plugins verificáveis passaram nos checksums; as árvores de plugins e do tema customizado continuam byte a byte iguais ao baseline de 28/09.

O domínio permanece **aberto para remediação**. A nova auditoria confirmou os sete P1 anteriores e ampliou a camada P2 com sete achados, inclusive um erro global não registrado na auditoria anterior: o rodapé de todas as páginas saudáveis contém texto jurídico da GamingAdx sobre jogos/recompensas. Também há grandes espaços vazios gerados por componentes invisíveis, aumento de 775 MB no filesystem desde 28/09 e ausência de acesso corporativo ao Search Console.

## Cobertura saudável

- Filesystem integral: `14.943` arquivos, `2.006` diretórios e `1.967.848.956` bytes hashados.
- Zero world-writable, symlink, PHP disfarçado, assinatura heurística ativa ou alteração em plugin/tema.
- Os nove `.php` em uploads são `index.php` vazios de proteção.
- `wp-includes/Text/Diff/Engine/shell.php` tem nome heurístico, mas pertence ao core oficial e passou no checksum.
- WordPress `7.1.2`; core checksum PASS; plugins `20/20` PASS; 22 componentes contando dois MU-plugins.
- Tema CompanyBRs: 26 arquivos, hash de cada arquivo igual ao baseline; pacote canônico externo continua indisponível.
- Banco: 25 tabelas, 19.808.256 bytes, `wp db check` PASS, zero trigger/evento, zero spam conhecido e zero WPCode publicado/shortcode ativo.
- Sitemap: 214 URLs HTML diretas; 213 HTTP 200 e somente `/es/home-espanol/` em 500.
- Links internos: `288/288` sem destino quebrado.
- Assets únicos: `719/719` HTTP 200.
- Browser: 24 visões; 22 HTTP 200, duas execuções da home espanhola em 500; zero erro de página, imagem quebrada ou spam visível.
- Query de campanha preservou UTM, `fbclid` e `gclid`.
- Edge e origem entregam a mesma home; XML-RPC, `.env` e PHP em uploads ficam bloqueados; HTTP/`www` redirecionam ao apex HTTPS.
- TLS efetivo rejeita 1.0/1.1 e aceita 1.2/1.3, embora o painel Cloudflare ainda mostre `min_tls_version=1.0`.

## Mudanças desde 28/09

- 89 registros WordPress foram modificados: 26 posts, seis páginas, 93 attachments no total atual, 14 itens de menu e seis changesets no conjunto recente.
- Autores do delta: `raqueloliveira` 65 registros, `dev` 18 e `rmmaster` seis.
- Os 26 posts novos passaram `26/26`: HTTP 200, meta description, canonical self, H1 e zero spam/mixed content.
- Não foi encontrado evento correspondente em audit log, inventário, REPORT-INFRA, Git ou sessões Zeus/Atena. Classificação: **mudança concorrente não atribuída, não anomalia**; há autoria WordPress, mas não autorização rastreável na cobertura consultada.
- Desde 28/09: 1.712 arquivos / 774.958.577 bytes alterados. Principais classes:
  - uploads `2026`: 596.955.574 bytes;
  - backups de imagens: 116.285.957 bytes;
  - cache HTML: 38.659.267 bytes;
  - JSON do Spectra: 15.924.341 bytes;
  - PNGs: 702.236.345 bytes.
- 2FA melhorou: três dos sete administradores agora têm TOTP (`dev`, Raquel e `rmmaster`); antes era um.

## Achados P1

### F032-R2-01 — Home espanhola continua HTTP 500

`/es/home-espanol/` retorna 500 na borda, cache-bust e origem. A causa permanece byte a byte igual:

- `functions.php:409` declara `companybrs_lang_query_args()`;
- `page-home.php:24` declara novamente;
- o fatal ocorre em `page-home.php:39`.

### F032-R2-02 — Tracking e cookies antes de consentimento

Antes de qualquer escolha:

- oito requests opcionais para Google Ads/GTM/GA;
- cookies `_ga` e `_ga_R0B9L58FXR`;
- nenhum banner ou gerenciador de preferências.

As políticas EN/ES continuam prometendo banner, consentimento prévio e Consent Mode v2. Runtime e texto jurídico divergem.

### F032-R2-03 — Seis plugins em faixas vulneráveis

- Ad Inserter `2.8.15` → `2.8.19`: CVE-2026-9280 e CVE-2026-11900.
- Spectra `2.19.26` → `2.20.4`: CVE-2026-12900; bloco `uagb/image` não observado.
- WPCode `2.3.4` → `2.3.9`: CVE-2026-8832, RCE Author+; XML-RPC está 403 e não há snippet/shortcode ativo.
- Yoast `27.1.1` → `28.6`: CVE-2026-3427; atributo `jsonText` não observado.
- Polylang `3.8.3` → `3.8.10`: correções de XSS/exposição em 3.8.4/3.8.6.
- WP Fastest Cache `1.4.9` → `1.5.2`: cache poisoning/XSS anteriores a 1.5.1; Polylang está ativo.

A ausência das precondições observáveis reduz alguns caminhos, mas não torna as versões corrigidas.

### F032-R2-04 — Acesso administrativo e credenciais locais

- Sete administradores; três TOTP e quatro sem TOTP concluído.
- REST público enumera três usuários.
- `DISALLOW_FILE_EDIT` ausente; editores de plugin/tema visíveis.
- `wp-config.php` permanece `0644`. Em host compartilhado, isso permite leitura local por outros usuários Unix se o caminho for atravessável; a borda pública continua bloqueada.
- A chave WP2FA ainda não foi rotacionada; qualquer rotação continua Critical Subset.

### F032-R2-05 — Host compartilhado e manutenção

- PHP `8.1.34` EOL.
- Kernel em execução `5.15.0-187`, reboot pendente.
- 25 pacotes atualizáveis e 29 serviços sinalizados pelo `needrestart`.
- Dez contas MariaDB não sistêmicas externas ao CarCreditAd mantêm privilégios globais amplos.
- Nove WordPress compartilham `runcloud2`.
- SSH efetivo: root login e password authentication permitidos.
- Firewall RunCloud registra 3306 global, embora MariaDB esteja em loopback e o teste externo tenha ficado filtrado.
- `user@1004.service` ficou failed após SIGKILL; o UID não existe mais. É resíduo de usuário aposentado, sem impacto observado nos serviços do site.

### F032-R2-06 — Origem e configuração Cloudflare

- Origem `162.55.28.179` continua diretamente acessível e entrega corpo igual ao edge.
- Cloudflare segue `ssl=full`, Always Use HTTPS off e painel em min TLS 1.0; o teste efetivo rejeita TLS 1.0/1.1.
- HSTS, CSP, Referrer-Policy e Permissions-Policy ausentes; somente X-Frame-Options e nosniff presentes.

### F032-R2-07 — Recuperação integral não certificada

- Os backups cirúrgicos anteriores continuam íntegros.
- Endpoint RunCloud de backup retorna 404 para o acesso disponível.
- Não existe backup atual de filesystem completo + banco completo com restore isolado comprovado.

## Achados P2

### F032-R2-08 — Rodapé jurídico errado em todo o site

- `213/213` páginas HTTP 200 exibem texto da GamingAdx sobre jogos, recompensas, apps e desenvolvedores de games.
- Fonte: `theme_mods_companybrs-theme` nas chaves `companybrs_disclaimer_text_en`, `_es` e padrão.
- Um changeset `90018`, autor `dev`, contém o mesmo conteúdo; autorização rastreável não foi localizada.
- É erro global de marca/jurídico, não malware.

### F032-R2-09 — Grandes áreas vazias e componentes invisíveis

- Home mobile: `#cat-grid` contém nove cards de ~396 px cada com `opacity:0`, gerando milhares de pixels vazios.
- Footer mobile: `.footer-main` tem 480 px com ~93 px de conteúdo.
- Artigo: author box tem 450 px com ~150 px de conteúdo, além de contêiner de anúncio/placeholder vazio.
- Screenshots desktop/mobile confirmam os espaços, sem quebrar imagens.

### F032-R2-10 — Frontend e acessibilidade

- SVG da hero continua 404 em EN e ES.
- Axe: 22 violações / 54 nós — dez `aria-allowed-attr`, 40 contraste e quatro links sem nome.
- Privacy EN/ES têm overflow mobile de 15 px.
- Formulário: sem CAPTCHA visível, sem consentimento próximo, botão muito pequeno e localização misturada EN/ES.

### F032-R2-11 — Desempenho e peso

- Mobile melhorou de 42 para **58**; LCP caiu de 20,9s para **8,8s**; TBT de 960ms para **444ms**.
- Desktop caiu de 94 para **85**; LCP 1,9s.
- Transferência Lighthouse: 7,1 MB mobile e 9,3 MB desktop.
- O crescimento de uploads é dominado por PNGs e cópias de backup; otimização e política de mídia permanecem pendentes.

### F032-R2-12 — SEO e links

- 94/213 páginas saudáveis sem meta description, acima das 77 anteriores.
- 17 grupos de títulos duplicados.
- Link Progressive de post 6703 retorna 404 em navegador real; substituto oficial atual retorna 200 em `https://www.progressive.com/answers/refinancing-a-car-loan/`.
- Santander ainda usa HTTP.
- `readme.html` e `license.txt` permanecem públicos.

### F032-R2-13 — Search Console não certificado

- API Search Console está ativa no projeto `mgs-core-prod`.
- A Service Account canônica não possui a propriedade `carcreditad.com`; não foi possível inspecionar cobertura/indexação.
- Sitemaps públicos estão acessíveis, mas isso não substitui o Search Console.

### F032-R2-14 — Resíduo systemd de UID aposentado

`user@1004.service` permanece failed desde 29/09 após SIGKILL. O UID 1004 não existe mais; serviços Nginx, PHP, MariaDB, RunCloud Agent, Fail2Ban e unattended-upgrades estão ativos.

## Performance laboratorial atual

- Mobile: performance 58, acessibilidade 94, boas práticas 73, SEO 92; FCP 2,1s, LCP 8,8s, TBT 444ms.
- Desktop: performance 85, acessibilidade 95, boas práticas 73, SEO 92; FCP 0,9s, LCP 1,9s, TBT 106ms.

## Limites e decisão operacional

- A auditoria foi read-only; nenhuma remediação foi aplicada.
- Ausência de assinatura não prova ausência absoluta de malware; a conclusão vale para a cobertura integral realizada.
- Tema customizado permanece sem pacote canônico de comparação, embora esteja idêntico ao baseline anterior.
- Search Console depende de um proprietário adicionar a Service Account canônica.
- Correções de plugin/site podem ser agrupadas em um lote reversível; credencial/2FA, host compartilhado, firewall/SSH, reboot, privilégios MariaDB e exclusões permanecem Critical e separados.

## Evidência

- Workspace: `/root/.hermes/profiles/zeus/workspace/carcreditad-complete-reaudit-20261001/`
- Resumo: `audit-summary.json`
- Manifesto: `evidence-manifest.json`
- Aggregate SHA-256: `474b4444f16275ce9dce60131637124f56f46e59c97422d9a51269b4a931c8da`
