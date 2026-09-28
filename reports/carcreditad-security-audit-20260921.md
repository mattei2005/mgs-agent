# Auditoria de segurança — carcreditad.com

## Autoridade e escopo

- Solicitante: Rodolfo Mattei; autorização Discord `1551769090564296718`; thread `1551768281688580096`.
- Janela: iniciada em 2026-09-21 EDT; evidências coletadas também em 2026-09-22 UTC.
- Método: SSH RunCloud, leitura estática, SELECT em transações read-only, checksums oficiais, consultas GET Cloudflare, HTTP público/origin e correlação de logs. Sem bootstrap do WordPress via WP-CLI, exploração destrutiva, alteração de conteúdo/configuração, credencial, plugin, PHP ou firewall.
- Alvo: MatteiInc02, webroot `/home/runcloud2/webapps/carcreditad`, home/siteurl `https://carcreditad.com`, tema ativo CompanyBRs 7.3, WordPress 7.1.1.
- Outros sites: somente descoberta de tema/versão/ativação e isolamento de usuário; não foi executada auditoria completa de vulnerabilidades/conteúdo nos demais.

## Conclusão executiva

A limpeza não está completa. Seis páginas publicadas continuam contendo spam de apostas oculto no HTML, confirmado tanto no banco quanto por HTTP 200 público. Apagar os artigos não eliminou esse comprometimento de conteúdo.

XML-RPC está bloqueado, o banco escuta apenas localhost e o bloqueio PHP em uploads também está ativo. Essas medidas são úteis, mas não limpam o conteúdo adulterado nem corrigem versões vulneráveis. O vetor XML-RPC associado a uso indevido da conta `rodmaster` é uma hipótese de alta confiança para alterações nas páginas, sustentada por revisões e logs; a forma original de obtenção do acesso permanece desconhecida.

## Achados prioritários

### Alto — seis páginas publicadas ainda adulteradas

Alvos confirmados, sem alteração nesta auditoria:

- ID 3 — `/privacy-policy/`: 13 ocorrências de posicionamento off-screen.
- ID 13 — `/contact-us/`: 11 ocorrências.
- ID 61581 — `/about-us/`: 11 ocorrências.
- ID 61590 — `/home-english/`: 10 ocorrências.
- ID 61652 — `/cookie-policy/`: 13 ocorrências.
- ID 61653 — `/terms-of-use/`: 10 ocorrências.

As 68 ocorrências de `left` negativo não são uma contagem de todos os links ou de todos os blocos maliciosos: há também ocultação por altura de 1px. O conteúdo inclui links de cassino/gambling em inglês e outros idiomas, deliberadamente escondidos. São dados persistidos em `wp_posts.post_content`, não somente cache antigo. As seis URLs responderam 200 e continham os indicadores publicamente.

Foram inspecionados 445 registros de posts, páginas e revisões. O banco contém 83 artigos publicados, 12 páginas publicadas, um artigo em rascunho, dois auto-drafts e 347 revisões. O detector não encontrou o mesmo padrão nos artigos remanescentes; isso não substitui revisão editorial integral de cada afirmação e link.

Evidências: `content.json`, `live-injection.json`, `cache-indicators.json`, `final-checks.json`. Conteúdo original preservado localmente para elaboração de reparo cirúrgico e rollback; nenhum payload de limpeza foi aplicado.

### Alto — histórico de uso indevido atribuído à conta rodmaster

- 80 revisões com os indicadores de injeção são atribuídas ao usuário ID 2 (`rodmaster`). Isso identifica a conta registrada pelo WordPress, não a pessoa física que operou.
- Janela dessas revisões: 2026-08-26 11:19:59 UTC a 2026-09-19 01:39:06 UTC (última alteração: 18/09 21:39:06 EDT).
- Todas as 80 têm POST `/xmlrpc.php` em janela de ±2 segundos; 65 coincidem com o mesmo user-agent autodeclarado Firefox/45.0. As demais também estão documentadas.
- Foram processadas 1.974.486 linhas de access logs de fevereiro a setembro, sem falha de parsing: 1.327.352 POSTs XML-RPC, dos quais 1.327.191 HTTP 200. HTTP 200 não prova sucesso de autenticação: XML-RPC pode responder faults dentro de HTTP 200.
- Os corpos XML-RPC e os usuários autenticados de cada request não constam dos access logs. A correlação é forte, mas não permite afirmar se houve senha reutilizada/roubada, application password antiga, outra integração ou outro mecanismo inicial.
- Fonte histórica já existente: `reports/wordpress-spam-audit/20260817-irrelevant-posts.json` documentava 40 artigos incompatíveis neste domínio, atribuídos a rodmaster, desde 20/07 até 17/08. Não é uma nova contagem dos mais de 200 artigos relatados pelo proprietário.
- Os registros atuais não permitem reconstruir com exatidão todos os artigos já excluídos. Não há revisões órfãs/Yoast órfão recuperáveis nas consultas feitas. Binlog e general log MariaDB estão desligados; backup offsite/RunCloud não foi validado.

### Alto — componentes com correções de segurança pendentes

15 dos 20 plugins instalados têm versões mais recentes no WordPress.org. Não são todas atualizações de segurança.

Prioridades justificadas por fonte:

- Ad Inserter 2.8.15: faixa afetada pelos avisos CVE-2026-11984 (divulgação de código de header/footer sem autenticação) e CVE-2026-11900 (leitura indevida de conteúdo por Contributor+), corrigidos em 2.8.17. Versão mais recente consultada: 2.8.18. O changelog também registra correção XSS em 2.8.16. Não foram exploradas as falhas em produção, nem demonstradas como causa histórica do incidente.
- Polylang 3.8.3: changelog registra correções de segurança posteriores em 3.8.4, 3.8.6 e 3.8.8; versão consultada mais recente 3.8.9.
- Spectra 2.19.26: changelog registra correções posteriores em 2.19.29, 2.20.0, 2.20.1 e 2.20.3; mais recente 2.20.3.
- WP Fastest Cache 1.4.9: melhorias/correções posteriores de autorização e proteção de cache em 1.5.1/1.5.2; mais recente 1.5.2.
- WPCode Lite 2.3.4: verificações adicionais de permissão em versões posteriores; mais recente 2.3.9.

Evidência completa de todas as versões: `plugin-updates.json`; fontes dos pacotes: `official-checksums.json`.

### Alto — origem acessível diretamente; proteção de borda contornável

- DNS Cloudflare de apex e www está proxied, porém HTTPS direto à origem, com hostname/SNI correto, respondeu 200. Logo, uma regra aplicada somente na Cloudflare não cobre todo o acesso ao site.
- XML-RPC e PHP em uploads responderam 403 também na origem, confirmando que esses bloqueios não dependem apenas da Cloudflare.
- UFW está inativo; iptables tem política INPUT ACCEPT e cadeias Fail2Ban. Não equivale a ausência absoluta de controles: Fail2Ban está presente e um firewall externo não foi auditado.
- SSH e porta do agente RunCloud acessíveis da VPS auditora. Configuração efetiva SSH permite root e senha; revisar via plano lockout-safe, sem alteração automática.
- Banco MariaDB confirmado em `127.0.0.1:3306`; conexão externa testada expirou sem estabelecer sessão. Usuários MariaDB listados com host localhost.

### Médio/alto — runtime e isolamento

- O pool do site usa PHP 8.1; binário identificado como 8.1.34. PHP 8.1 não está entre as branches com suporte upstream oficial. Não foi verificada eventual manutenção estendida específica do fornecedor RunCloud.
- Oito outros webapps no Inc02 compartilham o usuário de sistema `runcloud2`: creditoparaveiculo, gamingadx, autolendpro, autocreditadxx, financiamentoautoadx, gamezonead, gamehubad e financiarveiculo. A conta de sistema consegue ler as respectivas configurações por teste de permissão sem retornar valores de credenciais.
- Há restrição de caminho pelo `realpath_turbo` e funções PHP desabilitadas; portanto não foi demonstrado acesso lateral a partir de um request PHP. Compartilhamento de usuário continua ampliando o impacto potencial de comprometimento no nível de sistema/execução.

### Médio — permissões, 2FA e rastreabilidade

- Sete usuários: seis administradores e Atena com papel editor.
- Somente `dev` e `rodmaster` têm método TOTP com chave presente; quatro administradores ainda não têm cadastro TOTP completo. Política all-users/no-grace-period está configurada, o que não equivale a todos terem concluído o cadastro.
- Uma application password atual, com nome Atena API - MGS, pertence ao usuário editor criado em 20/09; não prova por si só identidade/autorização institucional. Nenhum valor/hash de application password ou de sessão foi incluído nos resumos.
- Os metadados de sessão e logs frequentemente registram IPs Cloudflare; não permitem atribuir diretamente a origem real do atacante. A leitura dos arquivos Nginx inspecionados não encontrou configuração real-ip. Uma correção deve confiar somente nos ranges oficiais do proxy.
- Edição de arquivos pelo painel não está desabilitada por `DISALLOW_FILE_EDIT`; revisar privilégios e necessidade dos plugins executores de código.
- Cloudflare: plano Free, SSL Full (não Strict), TLS mínimo 1.0; nenhum ruleset customizado/rate-limit específico retornado na listagem, nem regra legacy. Há rulesets gerenciados disponíveis; não se conclui WAF totalmente desligado pelo campo legado `waf=off`.

## O que não foi encontrado e limites

- 9.003 arquivos comparados com checksums oficiais da versão: 3.338 do core e 5.665 dos 20 plugins, sem diferenças, arquivos faltantes ou extras nos conjuntos comparados.
- Na revisão estática do CompanyBRs 7.3 e dos dois MU-plugins, não foi identificada rotina de publicação sem autenticação, criação de administrador ou backdoor evidente. AJAX público do tema faz consulta de posts publicados, não publicação. Isso não é certificação de ausência de vulnerabilidades nem auditoria dinâmica completa de todas as combinações de entrada.
- Não foram encontrados executáveis PHP inesperados em uploads ou cache na varredura; nenhum evento/trigger de banco e nenhum hook cron inexplicado identificado no escopo consultado.
- Não há prova de que o invasor mantenha sessão/acesso ativo agora; há prova de conteúdo malicioso ainda servido agora. Não confundir as duas conclusões.
- Não houve validação de backup remoto, restauração isolada, auditoria integral do painel RunCloud/control plane, endpoint do computador dos usuários, GTM ou exploit test autenticado. A origem de obtenção da credencial continua em aberto.
- CompanyBRs instalado em 26 webapps e ativo em 25 registros de banco, incluindo uma instância de backup bkp2.ducapes.com. Versões 7.3 a 8.1. Compartilhar o tema não prova que todos estejam comprometidos; nenhuma equivalência de código entre versões foi presumida.

## Plano recomendado, ainda não autorizado/aplicado

1. Preservar evidências e estabelecer backup/rollback verificável antes de alterações.
2. Remover cirurgicamente o conteúdo injetado nas seis páginas, preservando o conteúdo institucional legítimo; invalidar os caches envolvidos; validar banco, HTTP, sitemap, layout e anúncios.
3. Tratar a credencial de rodmaster como suspeita: planejar rotação de senha e revisão de sessões/application passwords, incluindo eventual reutilização em outros sites. Toda rotação precisa de confirmação crítica; não inferir autorização para outros domínios.
4. Atualizar plugins prioritários com canário e regressão de anúncios/integrações; depois os demais atrasados.
5. Planejar PHP suportado e isolamento por usuário, sem mudar produção antes do canário/rollback.
6. Restringir origem e fortalecer borda/login com allowlist correta, preservando RunCloud, SSH, automações e validação de certificados. Firewall e arquivos de sistema exigem confirmação crítica específica.
7. Completar 2FA das contas humanas e implementar rastreabilidade por usuário/IP real e detecção de alterações em artigos E páginas; não criar monitor novo sem autorização.
8. Fazer triagem separada dos oito vizinhos de mesmo usuário e de sites com credenciais reutilizadas, sem presumir invasão por tema compartilhado.

## Incidente de coleta do próprio auditor

A coleta inicial usou um glob amplo de Nginx que trouxe material TLS para evidência local. O resultado da ferramenta exibiu a chave privada mascarada; não se afirma expurgo do histórico. Esses campos foram retirados das cópias de evidência e o coletor limitado a `.conf`.

Posteriormente, uma denylist incompleta de `wp-config.php` deixou um valor de `WP2FA_ENCRYPT_KEY` aparecer no retorno interno de ferramenta, além de um salt de cache. A chave WP2FA deve ser tratada como exposta no contexto técnico. Não há evidência de envio ao atacante, mas isso não elimina a exposição. O valor não é reproduzido neste relatório.

Contenção local validada: snapshots de banco substituídos por nova coleta que retorna somente os nomes das constantes, sem o conteúdo de wp-config; evidência em diretório privado e arquivos com acesso restrito. O coletor corrigido foi reexecutado contra o alvo e passou no readback; configurações Nginx locais contêm somente `.conf`, sem material TLS. Procedimento durável atualizado com a coleta por metadados permitidos. Nenhuma chave de produção foi alterada. A rotação WP2FA exige plano de recriptografia ou recadastro controlado dos autenticadores para evitar bloqueio de acesso, com confirmação crítica de Rodolfo. Rotação TLS deve ser avaliada conforme exposição efetiva do histórico de ferramenta, sem declarar que não houve risco.

## Fontes e artefatos

- Evidência privada local: `/root/.hermes/profiles/zeus/workspace/carcreditad-audit/`.
- Histórico institucional: `/root/mgs-agent/reports/wordpress-spam-audit/20260817-irrelevant-posts.json`.
- Checksums: `https://api.wordpress.org/core/checksums/1.0/?version=7.1.1&locale=en_US`; `https://downloads.wordpress.org/plugin-checksums/SLUG/VERSAO.json`.
- Changelogs oficiais: `https://api.wordpress.org/plugins/info/1.2/` com plugin_information por slug.
- Ad Inserter: https://www.wordfence.com/threat-intel/vulnerabilities/wordpress-plugins/ad-inserter/ad-inserter-2816-missing-authorization-to-unauthenticated-headerfooter-code-disclosure-via-ai-debug-code-parameter
- Ad Inserter IDOR: https://www.wordfence.com/threat-intel/vulnerabilities/wordpress-plugins/ad-inserter/ad-inserter-2816-insecure-direct-object-reference-to-authenticated-contributor-arbitrary-post-content-disclosure-via-data-shortcode-attribute
- PHP: https://www.php.net/supported-versions.php

Resultado: auditoria read-only executada; comprometimento de conteúdo confirmado; remediação e incidente de chave aguardam decisão. Não declarar site limpo ou seguro.
