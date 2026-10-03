# MGS Router — domínios e importação Wantabrand

## Autoridade e estado

Rodolfo pediu cadastro/listagem de domínios e subdomínios, instruções DNS e cópia das rotas Wantabrand do Keitaro na mensagem `1555694651707625534`, thread `1555381168894115912`.

Esta fonte estende `docs/mgs-router-public-deployment.md` para gestão de domínios. **Estado ativo atualizado em 2026-10-02:** a aprovação `1555703152307740803` autorizou distribuição ponderada; o pedido `1555704420451352606` acrescentou verificação real e menu lateral. Todos foram publicados e validados, com 41 rotas importadas integralmente. O bloqueio registrado abaixo é histórico e foi supersedido por essa aprovação.

## Organização atual do painel

A aprovação `1555778254592417816` substituiu o menu lateral por navegação horizontal e tabelas **Rotas/Destinos/Grupos/Cadastro domínios**, com catálogo reutilizável. Fonte vigente: `docs/mgs-router-catalog-layout.md`. Links, destinos, pesos e verificação de domínios abaixo permanecem preservados. A descrição do menu lateral na entrega anterior é histórica, não a UI ativa.

## Entrega anterior — pesos, botão e menu lateral (UI supersedida)

- Menu lateral: **Cadastro domínios** e **Rotas**; cada domínio possui **Verificar** junto às instruções DNS.
- POST `/api/domains/check` exige sessão, origem e CSRF; aceita somente hosts cadastrados (com controle administrativo interno separado). Verifica DNS e HTTPS sem redirects, com timeout e limite de resposta, rejeitando endereços privados e reservados. GET `/__mgs-router-check` responde a um challenge com HMAC aleatório do processo. Verde somente com host, challenge e assinatura correspondentes.
- O controle positivo real via HTTPS no próprio host do painel confirmou o mecanismo. `card.wantabrand.com` e `tarjeta.wantabrand.com` permanecem **Pendente**: ainda não chegam ao MGS Router. O estado é uma verificação pontual, não monitoramento contínuo; DNS não foi alterado.
- A fonte Keitaro foi reextraída e comparada integralmente: 41 configurações inalteradas. Relay temporário removido e zero escritas no Keitaro.
- Importação autenticada via API: **41 rotas, 117 entradas de destino**, 36 simples e 5 ponderadas. Nomes, hosts, aliases, URLs e percentuais relidos exatamente. Soma de pesos obrigatória em 100%; query original preservada e macros UTM resolvidas sem duplicação.
- Validação local: 28 testes aprovados, incluindo Chromium, todas as 41 rotas e todos os 117 destinos, seleção determinística por 100 buckets, race detector, vet, build e sintaxe JavaScript. Verde de frontend foi exercitado com fixture sintética local, separado da prova real do backend.
- Validação pública nas contas Rodolfo e Geizian: menu, botão real com estado pendente, 41 rotas, 2 domínios, mobile sem overflow, zero erros JavaScript, autenticação/API/logout. Nenhuma rota sintética foi gravada em produção.
- Binário ativo SHA-256: `f4885df3e9f14544daaf766bbf39bc016f3856f8a78ea2164db6e637e69a5e58`. Apenas `mgs-router.service` reiniciado; gateways, unidade, TLS e credenciais preservados. Rollback pré-pesos: `/root/.local/share/mgs-router-rollbacks/1555703152307740803/` (binário e configuração de rotas pré-importação; restaurar ambos juntos, sob autorização aplicável).
- Evidência ativa: `data/mgs-router-wantabrand-import-validation.json`, `data/mgs-router-domain-check-validation.json`, `data/mgs-router-public-validation.json`, `data/mgs-router-weighted-sidebar-receipt.json`.
- Falhas intermediárias recuperadas: contrato de promise da listagem Angular e asserção antiga de destino fixo em teste ponderado; corrigidos e aceitação integral repetida com sucesso.
- **Sem cutover:** DNS, Keitaro, DTR e Smart Bidding intocados. As rotas estão prontas no painel, mas os hosts públicos continuam na origem anterior.

## Histórico — primeira publicação (supersedida pela entrega ativa)

- https://route.mgsdigitalcorp.com/admin apresenta cadastro de domínio/subdomínio, inclusão de vários hosts separados por vírgula, lista persistente e botão de instruções DNS por domínio.
- Domínios reais cadastrados e lidos de volta: `card.wantabrand.com` e `tarjeta.wantabrand.com`.
- `/api/domains` tem autenticação, CSRF/origem estrita, validação de hostname, revisão própria e gravação atômica. É aditivo; não remove domínios existentes nem modifica rotas.
- Estado operacional de domínios: `/var/lib/mgs-router/domains.json`, fora de Git. Não guarda credenciais.
- Instrução vigente: A para `2.25.165.171`, proxy Cloudflare ligado, TTL Auto, origem SSL Full. O aplicativo aceita exclusivamente peers Cloudflare. Outro provedor sem proxy compatível não pode usar DNS direto; o painel informa a necessidade de delegação ao Cloudflare. Cadastro não altera DNS e não autoriza mudar SSL global de zona existente.
- Teste local em Chromium realmente cadastrou hosts sintéticos, recarregou a página, confirmou persistência/lista/instrução, editou rota sintética e verificou layout mobile e logout. Nenhum host sintético foi cadastrado em produção.
- Validação pública das duas contas confirmou os dois domínios, formulário, instruções, layout mobile, ausência de erro JavaScript, API, logout, origem direta negada e transporte nativo de login preservado.
- Binário substituído atomicamente; somente `mgs-router.service` reiniciado. Unidade, TLS, senhas, rotas e gateways preservados. Rollback: `/root/.local/share/mgs-router-rollbacks/1555694651707625534/mgs-router`.

## Histórico — consulta inicial Keitaro, sem alterações

- Login protegido na origem exata `https://mattei-keitaro.xyz`, com item 1Password `mattei-keitaro.xyz`, usuário `rodmaster`. Relay local criptografado temporário removido; zero cópias temporárias restantes.
- Filtro exato solicitado `wantabr`: 41 campanhas, IDs únicos e contagem reconciliada com a listagem.
- Fonte sanitizada integral: `data/mgs-router-wantabrand-keitaro-source.json`. Contém campanhas, aliases, domínio, streams, landings, URLs, estados e pesos; nenhum token/cookie/senha ou dado de clique.
- Todas estão ativas, com um fluxo de landings sem filtros. 36 têm um destino; 5 têm múltiplos destinos: 331 (22), 589 (23), 529 (12), 355 (2) e 335 (22), com percentuais explícitos.
- 33 das 36 rotas de destino único também usam macros UTM. A importação deve resolver as macros a partir da query recebida, não gravar `{utm_source}` literalmente nem duplicar parâmetros indevidamente.
- A configuração atual do roteador só suporta um destino fixo por host/caminho. Não escolher um dos destinos nem reduzir a importação a 36 silenciosamente: isso mudaria o pedido de cópia integral.

## Histórico — bloqueio resolvido pela aprovação 1555703152307740803

Recomendação: autorizar extensão mínima para múltiplos destinos com os mesmos pesos do Keitaro, sem tracking/estatísticas, e então importar todas as 41 com aliases e comportamento UTM preservados. A alternativa de fixar um destino muda a distribuição e exige definição de Rodolfo.

Não houve importação de rotas, mudança DNS/cutover de tráfego, edição Keitaro ou alteração DTR/Smart Bidding. Os hosts continuam atendidos pela infraestrutura anterior até uma troca DNS separadamente autorizada.

## Evidência

- Código: `apps/mgs-router/domains.go`, `domains_test.go`, `main.go`, `web/admin.html`, `web/app.js`.
- Verificador público atualizado para ler rotas/domínios reais, sem exigir estado vazio ou comparar PIDs com o deploy histórico.
- Estado validado: `data/mgs-router-public-validation.json` e `data/mgs-router-domains-and-import-receipt.json`.
