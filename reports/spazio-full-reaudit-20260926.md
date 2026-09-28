# Reauditoria integral — Spazio Kitchens and Baths

**Data:** 26/09/2026  
**Domínio:** `spaziokitchensandbaths.com`  
**Servidor:** SpazioVPS / RunCloud server `266820` / origem `157.230.212.128`  
**Webapp:** `spaziokitchensandbaths` / app `1376648` / PHP `php83rc`  
**Pedido:** Discord `1553393159940079697`  
**Confirmação do acesso SSH temporário:** Discord `1553393877392556085`

## Conclusão executiva

A reauditoria foi concluída com **saúde operacional aprovada e pendências não críticas**. Não há evidência nova de invasão, malware ativo, persistência indevida, regressão da remediação de 25/09 ou indisponibilidade. Público e origem respondem, banco passou, filesystem foi integralmente hasheado, browser real passou em 16/16 execuções e o backup RunCloud mais recente está concluído.

O site não está em estado perfeito. Permanecem pendências conhecidas de conteúdo/SEO, três destinos internos 404, cadeia TLS incompleta na origem, ausência de três headers modernos, capacidade de disco em 81,3%, atualização incompatível do Elementor a ser mantida bloqueada e uma lacuna de visibilidade Cloudflare: zona/DNS são legíveis, mas settings/rulesets retornam 403 com o token corporativo aprovado.

**Produção alterada nesta auditoria:** não.  
**Credencial SSH temporária remanescente:** zero.  
**Segredos emitidos:** zero.

## Escopo e método

- Crawl integral a partir de 17 sitemaps.
- Testes públicos e diretos na origem.
- Browser Chromium real em desktop e mobile.
- Hash SHA-256 integral do webroot.
- Checksum oficial do WordPress e de plugins públicos.
- Auditoria de plugins privados, temas, MU-plugins e drop-ins por inventário/hash/heurística.
- Banco, usuários, sessões, application passwords, crons, options, posts com código e autoload.
- Logs HTTP/WordPress/SSH, processos, serviços, portas, firewall, Fail2Ban, pacotes e capacidade.
- DNS/zona Cloudflare, TLS público/origem e backups RunCloud.
- Comparação com os artefatos finais de 25/09.

## Resultado público e browser

- Sitemaps: **17**.
- URLs de sitemap: **276**.
- Páginas testadas: **291**.
- HTTP 2xx: **287**.
- Erros de página: **4**, sendo um artefato virtual do Cloudflare Email Protection e três destinos internos reais.
- Assets testados: **1.307**; **1.303** aprovados.
- Browser real: **16/16** execuções aprovadas.
- Fatal visual/JS: **0**.
- Page errors: **0**.
- Imagens quebradas: **0**.
- Mixed content: **0**.
- Overflow horizontal: **0**.
- Referências ao host antigo ou `/~spazio/`: **0**.
- Canonical ausente: **0**.
- W3 Total Cache identificado nas respostas representativas.

O crawl e as 15 classificações são **idênticos ao baseline pós-remediação de 25/09**. Não houve nova regressão pública.

### Links internos 404 confirmados

- `/pricing/`: referenciado por **127** páginas rastreadas; é o problema de link mais disseminado.
- `/portfolio-properties/`: referenciado por `/kitchen-remodeling/`.
- `/hardware/`: referenciado pelo layout público `/layouts/footer-home-hardware/`.
- `/cdn-cgi/l/email-protection`: rota virtual criada pelo Cloudflare; não é página editorial real.

### Conteúdo e SEO ainda incompletos

- A home ainda exibe o texto de verificação `google-site-verification: ...` no conteúdo visível.
- `/our-services/` ainda exibe o shortcode bruto do MC4WP, texto de template/lorem e quatro contadores zerados.
- A home mantém contadores zerados.
- **499** ocorrências de imagens sem `alt`.
- **7** grupos de títulos duplicados entre categorias/tags/layouts e páginas de contato.
- Formulários foram renderizados e inspecionados, mas não submetidos para não criar lead real durante uma auditoria somente leitura.

## Performance

A duração agregada do crawl concorrente ficou artificialmente elevada durante a varredura. O retry sequencial isolou o efeito do próprio scanner:

- Público, segunda passada: TTFB mediano **49,7 ms**; total mediano **71,5 ms**; máximo **81,0 ms** nas oito páginas representativas.
- Origem, segunda passada: TTFB mediano **45,4 ms**; total mediano **71,1 ms**; máximo **76,2 ms**.

Conclusão: não foi confirmada regressão de performance para navegação normal; a lentidão do crawl foi carga/concor­rência do teste, não estado sustentado do site.

## Superfície pública e hardening

Público e origem retornaram o mesmo estado esperado:

- `/`: 200.
- `/wp-json/`: 200.
- `/wp-admin/`: 302 para autenticação.
- `/xmlrpc.php`: 403.
- `/wp-json/wp/v2/users`: 404.
- `/nginx.conf`: 404.
- `/wp-admin/error_log`: 404.
- `/readme.html`: 404.
- Arquivos sensíveis (`.env`, `.git/config`, `wp-config.php`, backups e debug log): bloqueados/ausentes nas sondagens.

A remediação anterior continua efetiva: XML-RPC e enumeração de usuários bloqueados, arquivos internos não expostos, ZIP público removido e resíduos históricos ausentes do webroot.

### Headers

Presentes:

- HSTS por 1 ano.
- `X-Frame-Options: SAMEORIGIN`.
- `X-Content-Type-Options: nosniff`.

Ausentes:

- Content Security Policy.
- Referrer Policy.
- Permissions Policy.

A inclusão desses headers exige canário porque o site usa GTM, Meta, Tawk, Stape e integrações externas.

## TLS e Cloudflare

- Certificado público válido para o domínio, com expiração em **11/11/2026**.
- TLS 1.2 e TLS 1.3 aprovados no edge.
- Zona Cloudflare `active`, não pausada.
- Apex A e `www` estão proxied.
- DNS foi lido com sucesso.
- Settings e rulesets retornaram **HTTP 403** com `Cloudflare MGS Admin Token - mattei2005`.
- O token alternativo corporativo está ativo, mas não vê esta zona; portanto não é fallback válido.
- A cadeia TLS da origem continua incompleta para cliente que exige validação: erro OpenSSL **20**. A origem responde normalmente com SNI quando a validação da cadeia é ignorada.

A indisponibilidade de settings/rulesets é lacuna de auditoria/permissão, não falha observada do site. Nenhuma configuração Cloudflare foi alterada.

## WordPress

- Core: **7.1.2**.
- Plugins ativos: **24**.
- MU-plugins: **7**.
- Drop-in: `advanced-cache.php`.
- Temas: Pantry Child 1.0 ativo; Pantry 1.4.0 parent.
- Checksum de plugins públicos: **20/20 aprovados**; quatro privados/pro foram pulados por ausência de checksum WordPress.org.
- Plugins sem checksum público: Elementor Pro, Revolution Slider, TRX Addons e TRX Updater.
- Checksum de core: sem modificação inesperada. O retorno não-zero é explicado por `readme.html` removido e pelos arquivos deliberados `robots.txt` e `.mgs-w3tc/spazio-nginx.conf`.
- `wp-config.php`: modo `0640`, `WP_DEBUG=false`, `WP_CACHE=true`, `DISALLOW_FILE_EDIT=true`, oito salts, sem `auto_prepend` e sem include externo.
- O tema Pantry e os quatro plugins privados não puderam receber certificação independente por fonte pública; foram cobertos por hash integral, heurística, banco, logs e browser.

### Atualizações

- Elementor Free instalado em **3.31.2**, com **4.3.2** oferecido.
- Elementor Pro permanece em **3.31.2**.
- A atualização do Elementor Free deve continuar **bloqueada** até canário de compatibilidade com o Pro; a tentativa anterior com ramo 4.x derrubou o site.
- GTM4WP está em 1.22 e o metadata remoto aponta 2.0.3 como indisponível no fluxo atual; não deve ser trocado sem pacote canônico e canário.
- Demais plugins e temas não mostram atualização pendente.

## Filesystem e malware

- Arquivos integralmente lidos/hasheados: **39.585**.
- Diretórios: **5.576**.
- Tamanho lógico do webroot: **4,378 GiB**.
- Digest do manifesto integral: `72f0e70f92b7fe30bf79105044b5c9f3942d34463d624b58055913fa282d6059`.
- Propriedade: 100% `runcloud:runcloud`.
- World-writable: **0**.
- PHP em uploads: **0**.
- PHP disfarçado: **0**.
- SUID/SGID: **0**.
- Symlinks no webroot: **0**.
- Processos com nomes suspeitos: **0**.
- ZIPs em uploads: **0**.

O nome `wp-includes/Text/Diff/Engine/shell.php` é arquivo legítimo do core e está coberto pelo pacote oficial. As duas heurísticas em Really Simple SSL são código esperado do plugin e o checksum oficial passou. Não houve payload externo, shell ou persistência nova comprovada.

Limitação: ClamAV, RKhunter e Chkrootkit não estão instalados. A conclusão é baseada em hash integral, checksums oficiais, comparação de baseline, padrões de código, banco, logs, processos, origem e browser. Isso não equivale a garantia matemática contra toda ameaça inédita.

## Banco e persistência

- `wp db check`: aprovado.
- Tabelas: **126**.
- Tamanho: **143,1 MiB**.
- Triggers: **0**.
- Events do banco: **0**.
- Comentários: **0**.
- Cadastro público: desativado.
- Usuários esperados: `rmmaster`, `raqueloliveira`, `zeus` e `atena`.
- Administradores: `rmmaster`, `raqueloliveira` e `zeus`; Atena permanece editor.
- Application passwords esperadas: duas, sem exposição dos valores.
- Sessão ativa observada: `rmmaster`.
- Autoload: **497 linhas / 1.108.327 bytes**; aproximadamente 875 KiB pertencem ao transient de tamanho de diretórios. É pendência de performance/limpeza, não evidência de invasão.
- Registros históricos de código, Elementor e WPCode têm o mesmo conjunto de IDs/hashes/hosts do baseline profundo: **zero item novo e zero item removido**.
- Nenhum payload decodificado, host inesperado ou credencial em claro foi encontrado pela triagem semântica.

## Logs e ataques

- A janela histórica de logs ainda contém erros anteriores à recuperação; isso não foi mascarado.
- Na janela pós-remediação analisada: **zero fatal, warning, erro de banco ou timeout novo**.
- Sondagens públicas de shell, `.env`, phpinfo, dumps, backups e PHP em uploads não tiveram resposta 2xx suspeita.
- SSH registra força bruta contínua da internet, mas:
  - `PermitRootLogin=no`;
  - `PasswordAuthentication=no`;
  - autenticação por chave ativa;
  - Fail2Ban ativo, com 7 IPs banidos na coleta;
  - um único UID 0: root;
  - nenhum login aceito por senha para root/admin/usuário desconhecido.
- As duas chaves válidas de root e a linha histórica não parseável são o mesmo estado auditado em 25/09; não houve chave nova atribuída a esta execução.

## Servidor

- Ubuntu **22.04.5 LTS**.
- Kernel **5.15.0-194-generic**.
- Reboot requerido: **não**.
- Failed units: **0**.
- Nginx, MariaDB, RunCloud Agent, Fail2Ban, unattended-upgrades e Postfix ativos.
- O control plane confirma o app em PHP 8.3 e público/origem estão servindo. O coletor herdado verificou diretamente a unidade obsoleta `php80rc-fpm`, não a `php83rc-fpm`; esse falso negativo foi corrigido no procedimento institucional para futuras auditorias.
- Portas wildcard observadas: 22, 25, 80, 443 e 34210; MariaDB 3306 somente em loopback.
- Política de firewall do host permanece permissiva, com Fail2Ban protegendo SSH.
- Pacotes atualizáveis: `libaudit-common` e `libaudit1`.
- Disco: **27,42 / 33,74 GiB usados (81,3%)**; **6,31 GiB livres**.
- Memória disponível: aproximadamente **268 MiB**; swap livre: aproximadamente **1,69 GiB**.

Não houve instalação, update, restart ou mudança de firewall durante a auditoria.

## Backups

O control plane RunCloud retornou três snapshots full com status `COMPLETED`:

- 26/09/2026 06:00:13 — banco 104,58 MB; aplicação 1,52 GB.
- 25/09/2026 06:00:12 — banco 104,74 MB; aplicação 1,67 GB.
- 24/09/2026 06:00:13 — banco 105,63 MB; aplicação 1,70 GB.

O backup mais recente é do mesmo dia da auditoria. Não foi executado restore destrutivo nesta fase.

## Credencial temporária

Foi criado **um único** credential SSH Ed25519 temporário, conforme a confirmação:

- criação validada por GET;
- uso somente leitura;
- remoção no `finally`;
- GET final 404;
- lista RunCloud final com zero credentials;
- chave removida recusada pelo SSH;
- material privado local destruído;
- zero segredo emitido.

## Prioridades recomendadas

### P1 — janela controlada / confirmação separada

1. Manter Elementor Free 4.x bloqueado até staging/canário compatível com Elementor Pro.
2. Planejar capacidade antes de o disco ultrapassar 85%; identificar crescimento sem apagar o backup protegido.
3. Corrigir a cadeia TLS da origem.
4. Reduzir exposição do host/firewall preservando RunCloud, SSH canário e rollback.
5. Atualizar `libaudit-common` e `libaudit1` em janela exata; hoje não há reboot pendente.
6. Se for necessária auditoria total de WAF/settings/rulesets, ampliar de forma mínima a permissão read-only do token Cloudflare após confirmação específica.

### P2 — conteúdo, SEO e acessibilidade

1. Corrigir `/pricing/` no componente compartilhado que o publica em 127 páginas.
2. Corrigir `/portfolio-properties/` e decidir se `/hardware/` deve existir, redirecionar ou sair do layout.
3. Remover o texto de verificação da home.
4. Substituir shortcode órfão, lorem/template copy e contadores zerados em Our Services/home.
5. Tratar as 499 ocorrências sem `alt` e os sete grupos de títulos duplicados.
6. Projetar CSP, Referrer-Policy e Permissions-Policy em report-only/canário antes de enforcement.

## Evidência

Workspace restrito:

`/root/.hermes/profiles/zeus/workspace/spazio-reaudit-20260926/`

Artefatos principais:

- `final-validation.json`
- `lifecycle-receipt.json`
- `deep-audit-live.json`
- `deep-audit-followup-live.json`
- `db-semantic-triage-live.json`
- `post-public-crawl.json`
- `post-browser-validation.json`
- `external-preflight-post.json`
- `cloudflare-audit.json`
- `tls-audit.json`
- `performance-audit.json`
- `content-audit.json`
- `runcloud-backup-audit.json`
