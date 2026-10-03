# Painéis privados MGS — SEO e indexação desligados

## Decisão ativa

Rodolfo, mensagem `1555940444473655388`, thread `1555381168894115912`, determinou desligar SEO e indexação no MGS Router e na dash financeira. Pedido de favicon Router: `1555940342707257524`.

- Alvos: somente `route.mgsdigitalcorp.com` e `dash.mgsdigitalcorp.com`.
- Manter `X-Robots-Tag: noindex, nofollow, noarchive, nosnippet, noimageindex` nas respostas dos painéis, inclusive login e respostas de erro/API.
- HTML de login e shells autenticados: mesma diretiva em `meta[name=robots]`.
- `robots.txt` público: `User-agent: *` e `Disallow: /`; sem sitemap. Não oferecer sitemap, metadados promocionais/SEO, canonical ou dados estruturados de descoberta.
- Títulos de identificação, favicon oficial, acessibilidade, autenticação e cabeçalhos de segurança são funcionais; preservar.
- Não estender essas restrições aos sites de destino nem aos hosts de tráfego do Router. Preservar URLs, UTMs, distribuição, privacidade de redirects e configuração financeira.
- Estas diretivas orientam crawlers; não substituem autenticação e não provam remoção imediata de resultados previamente indexados.

## Publicação verificada deste turno

Router publicado e validado: favicon oficial existente da MGS (mesmo da dash), HTML/meta, cabeçalhos do painel, robots público e ausência de sitemap. Testes Go completos/race/vet, browser local e público, duas contas e 41 redirects reais sem seguir o destino. Backup privado `/root/.local/share/mgs-router-rollbacks/1555940342707257524/` exercitado com binário antigo e candidato. Unidade, rotas, usuários, TLS e PIDs dos gateways preservados.

Dash financeira: a inspeção inicial confirmou favicon existente, login sem noindex e `/robots.txt` autenticado (401). A escrita ficou bloqueada no turno anterior pela rota obrigatória Astra900k. **Supersessão de estado:** Rodolfo `1555943137128751176` autorizou uma exceção de modelo exclusivamente para este bloqueio de SEO/indexação; a regra financeira geral de modelo permanece intacta. Release `noindex-1555943137128751176` foi publicada pelo controlador canônico e validada: cabeçalhos em GET/HEAD/API/erros, cinco HTML shells com robots meta, robots público integralmente fechado e sitemap inexistente. 249 testes Node/193 Python passaram; stage isolado autenticado de sete perfis, 34 verificações de metadados desktop/mobile; produção owner com MFA e dez vistas, zero erros JS/POST financeiro. Fingerprints de cenários/revisões, source cells, ledger, histórico, auditoria financeira e usuários iguais antes/depois da publicação e do navegador. Relatório: `reports/finance-noindex-1555943137128751176.md`.

Evidências: `data/mgs-router-favicon-private-indexing-receipt.json`, `data/mgs-router-favicon-private-indexing-validation.json`, `data/mgs-router-public-validation.json`. Checkpoint: `MGS-PRIVATE-PANELS-1555940444473655388`.

## Ocorrência recuperada

QA adicional falhou inicialmente por ausência de `requests` no venv isolado Router. Dependência instalada somente nesse venv com uv; mesma verificação repetida e aprovada. Nenhuma dependência instalada no runtime dos agentes. Teste RED de noindex antes da alteração falhou como esperado.
