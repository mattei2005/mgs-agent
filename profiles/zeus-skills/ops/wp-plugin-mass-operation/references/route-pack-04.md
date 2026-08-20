## SEÇÃO D — SFTP para sites fora do RunCloud

Para os 4 sites AWS/Bitnami onde SFTP é o canal de acesso (read-only para verificação), ver:

**`references/sftp-sites.md`** — IPs, credenciais 1Password, arquitetura Bitnami, verificação de conectividade e pitfalls críticos.

### Sites cobertos

| Domínio | IP |
|---|---|
| openzed.com | 44.208.155.39 |
| finanzas.openzed.com | 3.19.138.131 |
| cliquet.com | 35.175.97.196 |
| finanzas.cliquet.com | 18.116.18.34 |

> **fincgriffin.com** — WordPress externo agora com acesso programático validado via WP Admin e REST. Credenciais no 1Password, item `Fincgriffin Wordpress`: `username` + `password` para login e `app user` + `app password` para REST. Não há SSH/SFTP conhecido; operações de plugin devem usar REST autenticado e configuração pelo formulário real `options.php`, com readback autenticado.
>
> **Sessão WordPress persistente do Zeus:** usar exclusivamente o perfil cleanup-protected `/root/.hermes/profiles/zeus/browser-profiles/fincgriffin-wordpress-chromium`, o runtime `/root/mgs-agent/tools/fincgriffin-wordpress-browser/` e os wrappers `scripts/zeus-fincgriffin-wordpress-login-browser.sh` / `scripts/zeus-fincgriffin-wordpress-session-probe.sh`. A sessão visual usa lock exclusivo e noVNC `127.0.0.1:6084` (VNC `127.0.0.1:5904`) por túnel SSH; nunca expor as portas publicamente nem serializar cookies. O login humano deve ser feito diretamente no browser remoto. Fechar o visual graciosamente antes do probe para o Chromium persistir cookies e liberar `SingletonLock`. Nunca apagar o profile, cookies ou lock state durante limpeza; primeiro provar que nenhum browser usa o perfil.

**CRÍTICO:** `wpfiles` é 100% read-only em todos os diretórios. Para escrita, usar elFinder (ver Seção B) ou SSH bitnami + .pem.

### MGS Chat Funnels — wrapper de anúncios

Para testes/instalações do plugin `MGS Chat Funnels`, ver **`references/mgs-chat-funnels-ad-wrapper-validation.md`**: rota virtual vs pasta física `index.html`, campos `company/domain`, wrapper JBF (`{company}_{domain}.builder.js`), e validação real de anúncios via `gpt.js`, `window.jbftag` e browser canário.

Para instalação em massa do `MGS Chat Funnels` junto com o plugin de quiz `activecampaign-quiz-lazy-blocks`, incluindo extração de pacote existente, RunCloud com `sudo -n`, WP Admin `/rodloguda/`, backups e validação por rota, ver **`references/mgs-chat-and-quiz-bulk-install-2026-07-03.md`**.

**Regra crítica de rollout MGS Chat Funnels:** código/plugin pode ser empacotado em comum, mas `configs/*.json` nunca são neutros. Em rollout “todos os sites”, validar e/ou ajustar individualmente por domínio antes de concluir: `ad_domain`, `route`, wrapper gerado (`{company}_{ad_domain}.builder.js`) e rota pública. Não propagar config de canário como Eggbev/OpenZed para outros sites. Se um campo admin não tiver efeito operacional real (caso confirmado: `brand`/`Site`), remover o campo e só limpar essa chave dos JSONs, sem reescrever configs inteiros.

Se uma rota carregar `gpt.js` ou wrapper JBF duas vezes, tratar como bug de implementação, não como variação aceitável. Ver `references/mgs-chat-funnels-duplicate-wrapper-hotfix.md`: a correção validada é sanitizar o `wp_head()` capturado em rotas standalone para remover GPT/JBF injetado por tema/WPCode/head, deixando `{{ADS_HEAD}}` do plugin como fonte única do ad stack.

Para mudanças na UI humana do admin do `MGS Chat Funnels`, ver `references/mgs-chat-funnels-admin-ui-taxonomy-and-rollout.md`: `Modelo de oferta` deve vir antes da identidade do chat; campos com taxonomia conhecida devem ser selects em ordem alfabética (Idioma, Vertical, País); e canário pedido pelo Rodolfo deve parar no site solicitado antes de rollout amplo.

Para rollout standalone de tracking nos chats já instalados, com campos GTM/GA4 no passo 3 e preservação dos provedores JBF, Zuout/ActView e Wantabrand/M2, ver `references/mgs-chat-funnels-standalone-tracking-rollout-2026-07-10.md`. O fluxo exige um canário por provedor, JSON por chat e validação de `page_view` real.

**`references/mgs-chat-funnels-ciro-runtime-fixes-2026-07-01.md`**: correções runtime validadas com Ciro para `MGS Chat Funnels`: preload rewarded deve chamar `requestRewardAds()` 1 vez (não loop 5x), top ad precisa manter o chat no fundo via auto-scroll/observers, e deploy OpenZed via WP Admin pode exigir cookie `wordpress_test_cookie` + fluxo upload/replace quando REST plugin retorna `401 rest_cannot_view_plugin`.

Quando Ciro/JBF corrigir a regra de rewarded para “1 só”, não copie loop legado de 5 auctions do `index.html`. O padrão operacional atual é 1 chamada de `requestRewardAds()` no `initQuiz`, sem `for`. Validar em browser com `googletag.pubads().getSlots()` — esperado apenas `..._rewarded/1`, não `/1` a `/5`. Ver `references/mgs-chat-funnels-one-rewarded.md`.

Para troca em massa de textos/URLs das ofertas CAR-BR já instaladas, sem alterar código do plugin, ver `references/mgs-chat-funnels-car-offer-bulk-update.md`: atualizar `configs/car-br-01.json` por site, usar WP-CLI/arquivo em RunCloud e raw JSON no WP Admin para Bitnami, validar HTTP 200 + textos novos + URLs por domínio + textos antigos ausentes + smoke de UTM.

Para converter o CAR-BR do modelo sequencial para cards estilo Ciro/FMYBC, ver `references/mgs-chat-funnels-car-cards-rollout.md`: respostas são engajamento-only e convergem para o mesmo bloco; card mode usa `image`/`name`/`subtitle`/`bank`/`target`; o renderer precisa tratar `questionData.offers`; canário em Eggbev antes de rollout; validar ausência de CTAs sequenciais, UTM nos cards, clique real do quiz/gate até o chat, linha de busca antes dos cards e `ad_domain`/wrapper slug por site.

Admin UX do `MGS Chat Funnels`: o campo `Modelo de oferta` deve aparecer antes de identidade/URL e antes de configurar gate/chat/ofertas, porque `cards` vs `sequential` define a arquitetura do funil. Ao alterar essa tela, validar ordem no admin autenticado (`1. Modelo de oferta` antes de `2. Identidade e URL`) além de `php -l` e pacote ZIP.

### Exceção Wantabrand — MonetizeMore/M2

`wantabrand.com` usa monetização MonetizeMore/M2/PubGuru, não o wrapper padrão JBF/Ciro. Para pedidos futuros nesse site:

- Escopo deve ser somente `/home/runcloud2/webapps/wantabrand/wp-content/plugins/mgs-chat-funnels/`; não aplicar rollout para outros sites.
- Se Rodolfo pedir algo para “todos os sites”, “todos os plugins”, “todos os chats”, “todos os funis”, “rollout geral” ou equivalente que possa mexer em chat/anúncio/plugin, parar e perguntar explicitamente se Wantabrand deve ser incluído ou excluído. Não assumir que “todos” inclui Wantabrand.
- Configs do chat devem usar `ad_provider: "m2"`, `ad_company: "monetizemore"`, `ad_domain: ""`.
- Em modo M2, remover/não carregar `https://assets.jbfdigital.com.br/...builder.js` pelo plugin.
- Wantabrand/M2 deve carregar explicitamente o loader PubGuru no `<head>` das rotas do chat: `<script type="text/javascript" async src="https://c.pubguru.net/pg.wantabrand.js"></script>`.
- Não deixar fallback JBF/JBFTag visível no código-fonte público do wantabrand: remover referências a `jbf`, `jbftag`, `showRewardedAds`, `requestRewardAds` e `assets.jbfdigital` das rotas públicas M2. `gpt.js`/`securepubads` podem aparecer em runtime como dependência carregada pelo próprio PubGuru, não pelo plugin MGS.
- Para o bloco inline “topo” no meio do chat, usar `<pubguru data-pg-ad="wantabrand_mob_top"></pubguru>` em mobile e `<pubguru data-pg-ad="wantabrand_desk_top"></pubguru>` em desktop. Inserir após a resposta da pergunta de valor/amount.
- **Não chamar `window.onInfinitePostLoaded()` no branch M2/PubGuru do bloco topo.** Essa chamada disparou interstitial cedo. Registrar o tag escolhido via `window.pga.adunitManager.defineObserveredNode(adSlot)` quando disponível, de forma assíncrona e protegida por `try/catch`.
- O wrapper do bloco topo precisa reservar/contener layout mobile: `min-height:420px` para `wantabrand_mob_top`, `300px` para desktop, `overflow:hidden`, `isolation:isolate`, `flex-shrink:0`; se PubGuru marcar `pg-disabled`, colapsar altura/margem.
- Preservar estética dos chats legados como Eggbev. Fixes M2/PubGuru não podem alterar layout dos botões/perguntas: comparar cores, tamanhos, posição, `button width:100%`, e evitar `width:fit-content`, `margin-left:auto`, `align-self:flex-end` ou `min-width:220px` no layout de respostas.
- Botões que devem disparar rewarded recebem classe `pg-rewarded`. No fluxo atual, o principal é o CTA do gate `#aq-cta`.
- Não assumir que clique em oferta final é rewarded. Para Wantabrand/M2, só colocar `pg-rewarded` em cards/ofertas finais se Rodolfo/M2 pedir explicitamente esse comportamento.
- Validar com HTML público: PubGuru loader presente, `pg-rewarded > 0`, `jbf == 0`, `jbftag == 0`, `assets.jbfdigital.com.br == false`, sem placeholders `{{...}}`, branch M2 sem `onInfinitePostLoaded`, e browser mostrando o chat avançando após o bloco.
- Detalhe completo: ver `references/wantabrand-m2-monetizemore-chat-ads.md`.

---

