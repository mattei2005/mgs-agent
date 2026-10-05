# CarCreditAd — remediação autorizada e validação

## Autoridade e escopo

Rodolfo Mattei, mensagem Discord `1556493106868649996`, thread `1551768281688580096`. Decisões: `docs/carcreditad-remediation-owner-scope-1556493106868649996.md` e registry `carcreditad-owner-scope-1556493106868649996`.

Alvo live: MatteiInc02 `162.55.28.179`, webroot `/home/runcloud2/webapps/carcreditad`, owner `runcloud2`, home `https://carcreditad.com`.

## Resultado por ponto

1. **Resolvido.** A home real `/es/` permaneceu intacta. `/es/home-espanol/` foi recuperada pela proteção da declaração duplicada de `companybrs_lang_query_args()` no template; nenhuma rota, redirect, permalink ou indexação foi alterada. HTTP 500 → 200. As páginas de home-template EN/PT também passaram no browser.
2. **Resolvido.** Backup integral filesystem e banco criado e restaurado em isolamento. Arquivo filesystem 1.798.026.704 bytes; banco comprimido 1.723.228 bytes. Backup, restore e roundtrip privados em `/home/runcloud2/backups/mgs-carcreditad-1556493106868649996`; schema isolado `mgs_cc_restore_1556493106868649996`; 25 tabelas, 16.795 linhas, 9.412 arquivos estáticos. Gzip, SHA-256, tar compare, SQL roundtrip, ausência de grants e 12 checks independentes PASS. Preservado, sem exclusões.
3. **Não executado; pergunta esclarecida.** Atualização dos seis plugins vulneráveis é a correção recomendada, com backup/canário/rollback. Rodolfo perguntou se basta atualizar, sem um comando independente de atualização; versões ficaram preservadas. Ad Inserter, Spectra, WPCode, Yoast, Polylang e WP Fastest Cache seguem nas versões anteriores.
4. **Preservado por decisão do dono.** Nenhum banner, política de consentimento, bloqueio de tracking, slot ou script de monetização foi acrescentado/alterado. A declaração sobre CMP automática SB/GAM permanece como declaração do dono, não nova certificação jurídica/técnica.
5. **Resolvido.** Seis theme mods do disclaimer e descrição institucional EN/ES/PT passaram a descrever CarCreditAd e financiamento de veículos. GamingAdx ausente de 214/214 páginas do sitemap; disclaimer próprio presente em 214/214.
6. **Resolvido no escopo visual autorizado.** Removidas as reservas intrínsecas/editorial paint-skipping no grid/categoria/related/author/footer e garantida visibilidade dos cards da categoria. Slots/ads permanecem intocados. Screenshots mobile/desktop e geometria aprovados.
7. **Resolvido no escopo técnico autorizado.** URL do SVG corrigida; contraste das categorias/cards/CTAs e rodapé; overflow de políticas; nome acessível do link do autor; controles de menu sem href tornados operáveis por teclado; campos/botão do formulário localizados e dimensionados. Não foi inserido CAPTCHA/consentimento e não houve envio de lead. Matriz 33 visões, 11 rotas × 3 larguras (320/390/1440): zero axe WCAG A/AA, overflow, pageerror, primeira parte >=400 ou imagem quebrada. Menu teclado, pesquisa Escape, tabs AJAX e validação de tipo email passaram em duas larguras.
8. **Conferido; nenhuma otimização disparada.** Imagify 2.2.7 ativo, auto_optimize=1, backup=1, nível 2; WebP/AVIF e delivery nextgen desativados. 487 imagens atuais: 156 success, 10 already_optimized e 321 error registrados. Todos os 321 erros registrados têm a mensagem histórica de quota esgotada, mas a API atual responde e informa plano `infinite`, quota `-1`; não há comprovação de quota atualmente esgotada. Os arquivos recentes com sucesso têm bytes reais iguais ao registro. Reprocessamento das falhas históricas continua fora do pedido de inspeção.
9. **Preservado por decisão do dono.** Nenhum título, meta description, destino editorial ou conteúdo de post foi alterado; será tratado pela redatora.
10. **Preservado por decisão do dono.** Usuários/2FA/credenciais/editores/wp-config não foram modificados. Sete administradores permanecem.
11. **Bloqueio Critical Subset.** Reboot remoto ainda requerido: kernel atual `5.15.0-187-generic`; `5.15.0-194-generic` presente. Nove webapps em `runcloud2` e oito em `runcloud`: 17 aplicações no servidor atingidas por um reboot. Serviços fundamentais 7/7 ativos. Não foi reiniciado/atualizado host, PHP, serviço compartilhado ou sistema. Recomendação: uma confirmação específica para reboot de MatteiInc02 e validação pós-boot; não fazer vários restarts parciais que não efetivam kernel.
12. **Preservado e conferido.** API Cloudflare SSL retorna `full`, HTTP 200. Nenhuma configuração Cloudflare/DNS/origem/firewall foi alterada.
13. **Resolvido acesso/inspeção.** Service Account canônica retorna propriedade `https://carcreditad.com/`, `siteFullUser`, HTTP 200. Sitemap sem erros/avisos e sem pending. `/es/` consta Submitted and indexed, canonicals Google/user iguais, crawl histórico 19/09. Nenhuma submissão manual.
14. **Explicado; intocado.** `readme.html` e `license.txt` existem na raiz do WordPress e seguem públicos HTTP 200. São documentação/readme e licença GPL, não wp-config ou credenciais. Nenhum arquivo/serviço residual foi excluído ou restringido.

## Gates e limites

- Sitemap completo: 214/214 HTTP 200, sem GamingAdx, com disclaimer e estilo próprio.
- Público canonical + cache-buster + origem: 15/15 checks aprovados. Query preserva UTM/fbclid/gclid na página reparada.
- Core e 20/20 plugins verificáveis íntegros. Contra o restore, as únicas alterações estáticas são cinco arquivos do tema e um novo MU-plugin. Nenhuma versão de plugin mudou.
- MU-plugin `mgs-carcreditad-scoped-fixes.php`, versão `2026.10.05.2`, hash em `menu-repair.json` e `candidate.json`.
- Dois caches iniciais e um cache da primeira candidata foram movidos para backup privado, não apagados; backup/restore retidos.
- Falhas auxiliares recuperadas: ajuda CLI checkpoint corrigida para checkpoint-upsert; read_file programático não preservou payload longo e foi substituído por leitura direta em execução privada; canários ajustaram seletor real de conteúdo e contraste do novo footer. Cache/CDN de JS manteve o menu antigo apesar do source hash correto; reparo idempotente próprio foi validado com variante antiga e sem duplo toggle de teclado. Dois pressupostos de teste foram corrigidos: alias editorial legitimamente 301 → /en/ e CF7 usa aria-required/validação própria, não native required para campo vazio. Todas as camadas afetadas foram reexecutadas. Na planilha, os 13 valores já haviam sido gravados quando um gate comparou indevidamente toda a formatação efetiva; fiz readback exato sem repetir a escrita, conferi regras/estilos atuais e corrigi o validador para separar formato autoral de apresentação computada.
- Erro intermitente `int64` nos canários atribuído a `pagead2.googlesyndication.com/pagead/js/rum.js`; ads não foram alterados. Último browser de produção e interação: zero pageerrors.
- Não se declara o domínio inteiramente fechado: plugins e reboot seguem gates, SEO/2FA/consentimento/Cloudflare tiveram decisões explícitas de preservação; baseline de desempenho não foi refeito como nova auditoria Lighthouse.

## Evidência

Workspace `/root/.hermes/profiles/zeus/workspace/carcreditad-remediation-1556493106868649996/`: backup.json, backup-independent.json, candidate.json, apply.json, menu-repair.json, production-browser.json, public-final.json, interactions-final.json, edge-origin-final.json, final-source.json, control-final.json, imagify-current-quota.json. As imagens locais não foram anexadas ao Discord.
