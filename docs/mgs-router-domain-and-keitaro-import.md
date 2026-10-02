# MGS Router — domínios e importação Wantabrand

## Autoridade e estado

Rodolfo pediu cadastro/listagem de domínios e subdomínios, instruções DNS e cópia das rotas Wantabrand do Keitaro na mensagem `1555694651707625534`, thread `1555381168894115912`.

Esta fonte estende `docs/mgs-router-public-deployment.md` para gestão de domínios. O estado atual de rotas continua vazio; a importação integral está bloqueada pela decisão descrita abaixo, não concluída.

## Publicado e validado

- https://route.mgsdigitalcorp.com/admin apresenta cadastro de domínio/subdomínio, inclusão de vários hosts separados por vírgula, lista persistente e botão de instruções DNS por domínio.
- Domínios reais cadastrados e lidos de volta: `card.wantabrand.com` e `tarjeta.wantabrand.com`.
- `/api/domains` tem autenticação, CSRF/origem estrita, validação de hostname, revisão própria e gravação atômica. É aditivo; não remove domínios existentes nem modifica rotas.
- Estado operacional de domínios: `/var/lib/mgs-router/domains.json`, fora de Git. Não guarda credenciais.
- Instrução vigente: A para `2.25.165.171`, proxy Cloudflare ligado, TTL Auto, origem SSL Full. O aplicativo aceita exclusivamente peers Cloudflare. Outro provedor sem proxy compatível não pode usar DNS direto; o painel informa a necessidade de delegação ao Cloudflare. Cadastro não altera DNS e não autoriza mudar SSL global de zona existente.
- Teste local em Chromium realmente cadastrou hosts sintéticos, recarregou a página, confirmou persistência/lista/instrução, editou rota sintética e verificou layout mobile e logout. Nenhum host sintético foi cadastrado em produção.
- Validação pública das duas contas confirmou os dois domínios, formulário, instruções, layout mobile, ausência de erro JavaScript, API, logout, origem direta negada e transporte nativo de login preservado.
- Binário substituído atomicamente; somente `mgs-router.service` reiniciado. Unidade, TLS, senhas, rotas e gateways preservados. Rollback: `/root/.local/share/mgs-router-rollbacks/1555694651707625534/mgs-router`.

## Keitaro: consulta concluída, sem alterações

- Login protegido na origem exata `https://mattei-keitaro.xyz`, com item 1Password `mattei-keitaro.xyz`, usuário `rodmaster`. Relay local criptografado temporário removido; zero cópias temporárias restantes.
- Filtro exato solicitado `wantabr`: 41 campanhas, IDs únicos e contagem reconciliada com a listagem.
- Fonte sanitizada integral: `data/mgs-router-wantabrand-keitaro-source.json`. Contém campanhas, aliases, domínio, streams, landings, URLs, estados e pesos; nenhum token/cookie/senha ou dado de clique.
- Todas estão ativas, com um fluxo de landings sem filtros. 36 têm um destino; 5 têm múltiplos destinos: 331 (22), 589 (23), 529 (12), 355 (2) e 335 (22), com percentuais explícitos.
- 33 das 36 rotas de destino único também usam macros UTM. A importação deve resolver as macros a partir da query recebida, não gravar `{utm_source}` literalmente nem duplicar parâmetros indevidamente.
- A configuração atual do roteador só suporta um destino fixo por host/caminho. Não escolher um dos destinos nem reduzir a importação a 36 silenciosamente: isso mudaria o pedido de cópia integral.

## Decisão pendente

Recomendação: autorizar extensão mínima para múltiplos destinos com os mesmos pesos do Keitaro, sem tracking/estatísticas, e então importar todas as 41 com aliases e comportamento UTM preservados. A alternativa de fixar um destino muda a distribuição e exige definição de Rodolfo.

Não houve importação de rotas, mudança DNS/cutover de tráfego, edição Keitaro ou alteração DTR/Smart Bidding. Os hosts continuam atendidos pela infraestrutura anterior até uma troca DNS separadamente autorizada.

## Evidência

- Código: `apps/mgs-router/domains.go`, `domains_test.go`, `main.go`, `web/admin.html`, `web/app.js`.
- Verificador público atualizado para ler rotas/domínios reais, sem exigir estado vazio ou comparar PIDs com o deploy histórico.
- Estado validado: `data/mgs-router-public-validation.json` e `data/mgs-router-domains-and-import-receipt.json`.
