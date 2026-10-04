# MGS Router — migração dos onze sites Keitaro

## Autoridade e estado

- Thread: `1555381168894115912`.
- Rodolfo pediu migração integral dos onze sites em `1556013403586306080`, seguida de Cloudflare e testes em `1556013519823175741`.
- Rodolfo informou renovação da licença e pediu novo login em `1556017623978999884`.
- Novo login protegido validado. A licença observada é Starter: a edição está bloqueada pelo limite Domains 29/1 e Users 2/1, mas a leitura de toda a configuração funcionou. Não há necessidade técnica de upgrade para concluir a extração feita.

## Snapshot salvo e reconciliado

- Fonte completa: `data/mgs-router-complete-keitaro-source-20261003.json` — **599 campanhas** reconciliadas por ID com a listagem integral e **1274 Landing Pages**. Streams, aliases, hosts, estados, ações, URLs e shares sanitizados; sem token de campanha, cookies, senha ou logs de clique.
- Fonte do escopo: `data/mgs-router-eleven-domains-keitaro-source.json` — **428 campanhas ativas**, **18 hosts de tráfego**, **1247 entradas de destino**.
- Cloudflare: todas as onze zonas visíveis; SSL Full, proxy ativo; DNS de tráfego ainda na origem anterior. Preflight/rollback sanitizado: `data/mgs-router-11-domains-dns-preflight.json`.
- Fontes completas fora do cache efêmero e registradas no inventário. Snapshot não depende de manter a licença ativa; nova alteração na origem exige reconciliação antes de importar.

## Fidelidade antes de importação — diagnóstico histórico

O importador `scripts/mgs-router-import-eleven-domains.py` foi exercitado em modo sem alterações. A validação recusou corretamente uma importação parcial. **Zero rotas importadas e zero DNS alterado nesta iniciativa.**

1. Distribuições relativas fracionárias nas campanhas 118, 119, 127 e 185. Shares originais preservados. O Router atual exige percentuais inteiros somando 100; arredondar modificaria a distribuição. Precisa suportar a razão original sem arredondamento.
2. Campanha 133, `card.topfeed.fun/lpsfinance`: URL de destino contém `utm_campaign=pg_#PAGE_ID#&utm_content=drip_m0-1`. O primeiro `#` transforma o restante em fragmento; isso foi confirmado por HTTP302 real na origem. Não corrigir silenciosamente nem presumir o valor pretendido do Page ID.
3. Campanha 304, `card.cliquet.com/6TQYS31C`, nome `CLIQUET EN LOAN CAR - funil 11 03`: zero landings e HTTP500 real na origem. É defeito anterior à migração. Não inventar destino nem descartar sem decisão de Rodolfo.

Os seis casos foram testados na origem: cinco HTTP302, um HTTP500 (campanha304). Evidência: `data/mgs-router-eleven-domains-fidelity-validation.json`; plano bloqueado: `data/mgs-router-eleven-domains-import-plan.json`.

## Próxima decisão e execução

Esta seção descreve o bloqueio histórico anterior à decisão1556086016140509195; foi supersedida pela seção ativa abaixo.

- Obter destino ou tratamento explicitamente autorizado para a rota vazia, e tratamento da URL com `#PAGE_ID#`.
- Preservar as razões dos quatro conjuntos de pesos sem arredondar.
- Só então importar a configuração integral, preservando as 41 rotas Wantabrand/catalog/grupos existentes e suas revisões concorrentes.
- Mostrar/confirmar o diff exato de Cloudflare conforme política vigente, aplicar canário por host com rollback e exigir varredura limpa GET+HEAD de todas as rotas, além de TLS/challenge assinado e cadeias de destino.
- Nenhuma escrita no Keitaro, DTR ou Smart Bidding faz parte desta migração.

## Falhas recuperadas

- Sessão do navegador foi reinicializada durante a extração; os 490 IDs já persistidos foram preservados e somente os 109 ausentes foram recuperados, fechando 599/599 sem duplicação.
- Campo de tipo de Landing Page é `landing_type`, não `type`; listagem completa reconsultada e reconciliada com todos os IDs/nomes/ações/URLs referenciados. Importador repetido com diagnóstico correto e sem escrita produtiva.
- Todos os relays criptografados temporários do login foram removidos e a contagem restante foi validada como zero.

## Estado ativo — fidelidade literal autorizada e importada

Rodolfo decidiu em `1556086016140509195`: montar exatamente como está no Keitaro, após a divulgação dos defeitos da fonte. Isso resolve o tratamento sem inventar correções e supersede a antiga dependência de obter novas URLs para133/304.

- **Publicado e importado:**428 rotas em18 hosts dos11 sites; painel agora tem469 rotas (incluindo41 Wantabrand preservadas),943 destinos de catálogo e30 grupos. API `/api/routes` foi escrita uma vez, revisão3, com readback exato; domínios já cadastrados foram preservados. Receipt:`data/mgs-router-eleven-domains-import-validation.json`.
- Shares relativos originais permanecem inteiros, sem normalização/arredondamento, selecionados pela soma real. UI mostra peso/soma e preserva modo/valores em save/reload.
- Campanha304 foi importada como rota explícita sem destino comHTTP500; campanha133 mantém URL e fragmento `#PAGE_ID#`. Não foram reparadas nem descartadas. Demais chaves UTM repetidas/incorretas na fonte também foram preservadas literalmente.
- As novas rotas têm `keitaro_query=true`: somente macros UTM recebidas são substituídas, com encodingPHP/último valor duplicado; ausentes permanecem literais, URL fixa/fragmento não muda, extras não são repassados. HTTP da origem confirmou isso. O contrato raw-passthrough anterior das41 rotas Wantabrand permanece intacto.
- Paridade live da fonte:428/428 respostas correspondem aos destinos/configurações salvos, inclusive500 esperado. Artifact:`data/mgs-router-eleven-source-live-parity.json`. Isso confirma comportamentoHTTP observado, não todas as escolhas aleatórias da origem; a razão é validada deterministicamente em todos os buckets do Router.
- SuiteGo, race, vet, JavaScript e build aprovados. Teste integral exerce cada aliasGET+HEAD com/sem query, todos os buckets,1247 entradas de destino, persistência469 rotas. Chromium local salvou/recarregou pesos/macro/rota vazia. Chromium público nas duas contas confirmou469/943/30, navegação, formulários e zero erroJS/overflow; login/logout/API/edge guard aprovados.
- Regressão pública Wantabrand:41 rotas,82 requisiçõesGET+HEAD,zero falhas. Release:`data/mgs-router-eleven-literal-release-receipt.json`; backup protegido:`/root/.local/share/mgs-router-rollbacks/1556086016140509195/`.
- ApenasRouter foi reiniciado. Unidade, credenciais, TLS e PIDs dos gateways foram preservados na publicação. Nenhuma escritaKeitaro/DTR/SB.

## Próximo gate — DNS ainda não alterado

Fonte live:`data/mgs-router-eleven-literal-dns-plan.json`:35 registros existentes,18A+17AAAA, em18 hosts. Todos proxytrue/TTL1/SSLFull. `card.openzed.com` não temAAAA neste plano; não criar um registro extra incidentalmente.

- A:`167.235.247.79` → `2.25.165.171`.
- AAAA:`2a01:4f8:c013:55b2::1` → `2a02:4780:75:4061::1`.
- Preservar IDs/tipos/TTL/proxy/SSL e DNS de todos os outros hosts/apex. Zero exclusão.
- **Zero DNS writes:** confirmar comRodolfo o diff exato antes de aplicar, conforme skillCloudflare. Depois reconciliar plano live, aplicar porhost com canárioHTTPS assinado/rollback e varredura completaGET+HEAD na semântica de cada rota, contando oHTTP500 esperado separadamente. Ainda não declarar os18 hosts ativados noRouter.

## DNS ativo — confirmação1556329456463908905

Rodolfo confirmou o diff de35registros com a restrição de alterar **somente IPs**. Esta seção supersede o gate histórico de DNS pendente acima, sem alterar a decisão de fidelidade literal.

- **35registros existentes**,18A+17AAAA, dos18hosts dos11sites foram atualizados porPATCH **somente `content`**. IDs/tipos/proxy/TTL/comments/tags/settings preservados; zero exclusão/criação e zero alteraçãoSSL. `card.openzed.com` permanece semAAAA.
- Preflight online confirmou11zonas ativas,SSLFull, ausência de overridesPageRules/Workers/LB/regras ativas relevantes; TLS+edgeguard403 nos doisIPsRouter. Rollback exato pré-mudança e digest semântico dos registros não-alvo em `data/mgs-router-eleven-dns-cutover-validation.json`.
- CanaryHTTPS assinado e varredura completa limpa porhost; readback final de35registros e invariânciaSSL/digest dos demaisDNS das11zonas. Hashes de rotas/domínios/usuários/binário/unidadeRouter intactos. Nenhum restart ou escritaKeitaro/DTR/SB.
- Varredura global limpa: **469rotas**,GET+HEAD com/semquery, mais80checks de caminhos reservados em20hosts = **1956checks**,zero divergência. Dentro disso,428rotas novas e41Wantabrand. Quatro checksHTTP500 da rota304 são o defeito esperado/preservado, não falha nova;468rotas302 e1rota500.
- Chromium real nas contasRodolfo/Geizian:469rotas/943destinos/30grupos,20domínios verificados/verde persistente apósreload,JS/mobile/formulários/API/logout aprovados. Artifact: `data/mgs-router-eleven-cutover-browser-destinations.json`.

### Recuperação e limites do teste fim a fim

- PropagaçãoCloudflare misturou respostas da origemKeitaro antiga eRouter. `card.wavesbee.com` não convergiu no primeiro limite; os dois registros foram restaurados/readback e o mesmohost foi retomado com backoff maior até varredura limpa.35registros finais;37PATCHes de ida e2PATCHes de rollback durante recuperação.
- Um executor de lote foi encerrado pelo timeout efetivo420s enquanto verificava `job.seuprimeiroempregoam.com`; processo ausente/readback reconciliado, retomada apenas da verificação pendente sem duplicarPATCH. Lotes posteriores ficaram menores.
- OracleQA de passthroughWantabrand esperava percent-encoding que `requests` normalizava antes do envio. Corrigido somente o validador para comparar a query efetivamente transmitida; rotas/Router intactos. Varredura global integral reexecutada e aprovada.
- **12/18hosts** tiveram pelo menos uma cadeiaRouter→página finalHTTP200. Nas amostras dos outros6hosts, oRouter redireciona corretamente, mas destinos históricos têm404 ou525: `car.cliquet.com`, `car.openzed.com`, `job.conectageral.com`, `tarjeta.conectageral.com`, `tarjeta.eggbev.com`, `tarjeta.portalrelevante.com`.
- Dez checks diretos emURLs literais do snapshotKeitaro reproduziram8HTTP404 e2HTTP525; os destinos estão fora dos registrosDNS alterados. Artifact: `data/mgs-router-eleven-destination-health-diagnostic.json`. Isso identifica indisponibilidade atual do destino configurado; não prova que todas as páginas desseshosts estejam quebradas nem o início histórico da falha.
- **MigraçãoDNS/fidelidade validada; saúde fim a fim parcial.** Não substituirURLs, repararWordPress ou mudarSSL sob esta autorizaçãoIP-only. Próximo escopo depende de decisãoRodolfo: diagnóstico/correção separada de destinos, preservando aconfiguração doRouter até nova autorização.

## Falhas de validação recuperadas nesta etapa

- Teste de configuração integral identificou macros reconhecidas colocadas sob outra chaveUTM; validador adaptado sem corrigir aURL da fonte. Fixture local ajustou somente sua revisão inicial, mantendo proteção contra conflito em produção.
- QA público tinha corrida: comparava estadoPending já presente antes da resposta do novoVerificar. Passou a aguardar a resposta exata e compará-la comstore/reload.
- QA de busca assumiaID único por substring; `ktr-10` também retorna`ktr-100`. Agora calcula o total esperado e confere a linha porID exato. Fluxo completo reexecutado/aprovado nas duas contas. Nenhum defeito de persistência real foi encontrado nesta etapa.
