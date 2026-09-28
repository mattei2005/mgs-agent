# F031 — Auditoria pré-SSH do spaziokitchensandbaths.com

**Estado:** PARCIAL — BLOQUEIO CRÍTICO PARA COBERTURA INTERNA  
**Data:** 2026-09-23 UTC  
**Domínio:** `spaziokitchensandbaths.com`  
**Servidor:** SpazioVPS / RunCloud server ID `266820`  
**Webapp:** `spaziokitchensandbaths` / app ID `1376648`  
**Origem:** `157.230.212.128`  
**Pedido:** Discord `1552334493476589662`

## Resultado executivo

A auditoria avançou sem alterar produção usando:

- RunCloud API somente leitura;
- WordPress REST API autenticada com a conta Zeus já aprovada;
- Site Health REST;
- WordPress.org para versões públicas;
- testes HTTP público/origem;
- DNS e portas TCP.

A cobertura interna completa ainda depende de uma credencial SSH temporária. A API RunCloud confirma que o servidor possui **zero credenciais SSH registradas**, e tentativas keyless para `root` e `runcloud` foram negadas. Criar uma chave temporária altera credencial de produção e pertence ao Critical Subset.

## Estado do servidor e aplicação

- SpazioVPS online e conectado ao RunCloud;
- Ubuntu Jammy;
- RunCloud sinaliza `securityUpdate=true`;
- somente portas 22, 80 e 443 abertas entre 17 portas comuns testadas;
- 3306, 5432, 6379, 11211 e portas comuns de e-mail não responderam externamente;
- PHP da webapp: 8.0, fora de suporte upstream;
- WordPress exposto pelo frontend: 7.1.2;
- banco registrado no RunCloud, mas conteúdo/estrutura não auditados sem SSH;
- origem HTTPS responde com certificado de origem não confiável pela cadeia pública, compatível com Cloudflare Origin Certificate;
- a origem responde diretamente quando IP + Host são conhecidos, permitindo contornar a camada Cloudflare para HTTP(S). Restringir origem exige mudança separada de firewall e confirmação crítica.

## WordPress autenticado

- Conta Zeus: administrador;
- quatro usuários:
  - três administradores: Raquel Oliveira, RM Master e Zeus;
  - uma editora: Atena MGS;
- TOTP, sessões e application passwords não foram certificados pelo REST disponível;
- autenticação REST por application password funciona;
- login web comum foi corretamente bloqueado sem CAPTCHA válido.

## Plugins e temas

Plugins:

- 47 instalados;
- 25 ativos;
- 22 inativos;
- 18 plugins públicos ativos abaixo da versão atual do WordPress.org;
- 17 plugins públicos inativos abaixo da versão atual;
- cinco plugins ativos sem pacote público verificável:
  - Elementor Pro;
  - Slider Revolution;
  - SpeedyCache Pro;
  - ThemeREX Addons;
  - ThemeREX Updater.

Plugins públicos ativos abaixo da versão atual:

- Advanced Popups `1.2.2 → 1.2.4`;
- Backuply `1.4.7 → 1.5.8`;
- Check & Log Email `2.0.8 → 2.0.16`;
- CMB2 `2.11.0 → 2.13.0`;
- Contact Form 7 `6.1.1 → 6.1.7`;
- Country Code for Elementor `1.4.3 → 1.7.4`;
- Duplicate Page `4.5.5 → 4.5.9`;
- Elementor `3.31.2 → 4.3.1`;
- GTM4WP `1.22 → 2.0.2`;
- Input Mask Elementor `4.2.1 → 4.4.5`;
- License for Envato `1.1.0 → 1.4.1`;
- Make Column Clickable Elementor `1.4.0 → 1.6.2`;
- Really Simple Security `9.4.3 → 9.8.3`;
- SpeedyCache `1.3.5 → 1.4.2`;
- Tawk.to `0.9.2 → 0.9.3`;
- Ultimate Addons for Elementor Lite `2.4.3 → 2.9.4`;
- WPCode Lite `2.2.9 → 2.3.9`;
- Yoast SEO `25.7 → 28.5`.

Também existem diretórios inativos duplicados com sufixo `.DISABLED`, incluindo Captcha Code e Loginizer. Nenhum foi removido.

Temas:

- sete instalados;
- `pantry-child` ativo;
- tema ativo e pai são comerciais/locais e não possuem pacote público para checksum;
- três temas padrão inativos estão abaixo das versões atuais.

A listagem de versão não substitui checksum do filesystem. Nenhum plugin ou tema foi atualizado nesta etapa.

## Conteúdo e comentários

Foram examinados via REST autenticado 197 registros em posts, páginas, layouts, portfólio, serviços, equipe, templates, menus e popups.

- nenhum termo de cassino, apostas, pharma ou pornografia no conteúdo publicado examinado;
- nenhuma assinatura `eval`, `base64_decode` ou JavaScript codificado detectada;
- 24 hosts externos encontrados, todos compatíveis com tema, redes sociais, vídeo, mapas, mensageria, Cloudflare, Zoho, Envato ou infraestrutura conhecida;
- 65 registros acionaram heurística de markup oculto, mas a triagem mostrou 324 atributos `hidden` e um `display:none`, sem links externos próximos do markup oculto; padrão compatível com widgets/responsividade do tema;
- nenhum nó foi apagado ou alterado.

Comentários:

- 300 comentários;
- quatro aprovados, sem URLs externas;
- 296 aguardando moderação;
- o backlog pendente contém 96 hosts externos e pelo menos 13 comentários com palavras explícitas de spam/apostas/pornografia;
- o spam está retido e não publicado;
- nenhuma limpeza foi executada, pois exclusão pertence ao Critical Subset.

## Site Health e tamanho

Checks positivos:

- HTTPS ativo;
- comunicação com WordPress.org;
- loopback funcional;
- background updates funcionais.

Alertas:

- cache detectado, mas homepage mediana em 646 ms e sem header cliente de cache;
- teste interno marcou `Authorization header` inválido, embora autenticação REST externa por application password tenha funcionado; provável diferença de loopback/proxy a validar por SSH;
- tamanho total reportado pelo WordPress: 4,68 GB;
- WordPress: 2,99 GB;
- plugins: 379,21 MB;
- uploads: 1,13 GB;
- banco: 136,98 MB.

## HTTP, DNS e superfície externa

- DNS público passa pelo Cloudflare;
- homepage, REST, login, robots e sitemaps responderam HTTP 200;
- WordPress REST, robots e sitemap produziram resultado equivalente no público e na origem;
- homepage/login variam por conteúdo dinâmico/nonces e cache, sem erro funcional;
- headers observados incluem HSTS, `X-Frame-Options: SAMEORIGIN` e `X-Content-Type-Options: nosniff`;
- homepage pública permanece `CF-Cache-Status: DYNAMIC` e `Cache-Control: no-store, no-cache`.

## Lacuna real

Sem SSH não é possível certificar:

- checksums do WordPress core e dos plugins no filesystem;
- arquivos extras, webshells, permissões e ownership;
- `wp-config.php`, salts e debug;
- banco completo, opções, cron e tabelas customizadas;
- snippets do WPCode;
- logs Nginx/PHP e tarefas de sistema;
- estado real dos updates de segurança do Ubuntu;
- backup/restauração e processos ativos.

## Recomendação

Criar **uma chave Ed25519 temporária** no RunCloud, vinculada ao usuário `runcloud`, exclusivamente para auditoria somente leitura. O fluxo já foi validado anteriormente nesse servidor:

1. gerar chave local temporária;
2. registrar como credencial temporária no RunCloud;
3. validar por GET/readback;
4. executar auditoria interna sem alteração do site;
5. excluir a credencial em `finally`;
6. validar GET 404 e zero credenciais remanescentes.

Nenhuma atualização, limpeza, correção de firewall ou alteração de conteúdo faz parte dessa autorização.

## Evidências

Workspace:

`/root/.hermes/profiles/zeus/workspace/spazio-f031-internal-audit-20260923/`

Artefatos:

- `rest-audit.json`;
- `public-version-audit.json`;
- `health-content-audit.json`;
- `hidden-markup-triage.json`;
- `comments-audit.json`;
- `network-http-audit.json`.
