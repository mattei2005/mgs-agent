# Smart Routing — criação segura de routing pool

## Quando usar

Use quando Rodolfo pedir a criação de um pool em **Smart Routing** para um site e fornecer/confirmar a planilha operacional que contém `route`, `utm_content` e URL.

## Fontes e pré-condições

1. Reconsultar a planilha indicada pelo Rodolfo via Google Sheets API com a Service Account canônica MGS.
2. Ler exatamente o bloco do pool solicitado; não inferir linhas vizinhas.
3. Exigir por rota:
   - `route` não vazio e único;
   - `utm_content` não vazio e único;
   - URL não vazia e **sem barra final**;
   - operação JBF resolvida pela URL selecionada na SB.
4. Consultar a SB ao vivo em `https://app.smartbiddingdigital.com/company/{company}/{publisher}/routing` usando Playwright headed/Xvfb e o storage state canônico.
5. Fazer backup da resposta live anterior e abortar se o nome-alvo já existir.

## Padrão Infinitynexx — MX-CC-ES ensinado por Rodolfo

Fonte piloto: planilha `Joe - Controle de Broadcast - Infinitynexx`, aba `FLUXO MX-CC-ES-JBF`.

Configuração dos pools Drip:

- `COMPANY=digital-trust`
- `DOMAIN=infinitynexx`
- `SOURCE=FACEBOOK`
- `COUNTRY=MX`
- `VERTICAL=CC`
- `LANGUAGE=ES`
- Medium selecionado na UI: `SLOT_D`; readback API: `MEDIUM=.*-d$`
- `APPEND_PARAMS=false`
- Nome: `in-mx-cc-en-drip NNN`
- Cinco rotas por pool

Divisão confirmada:

- `001`: `m0`, `nm`, `m1–m3`
- `002`: `m4–m8`
- `003`: `m9–m13`
- `004`: `m14–m18`
- `005`: `m19–m23`
- `006`: `m24–m28`

### Invariante de ordem e URLs por slot

Ao criar, dividir, revisar ou redistribuir pools Drip de cinco rotas, preservar simultaneamente a ordem semântica `m0`, `nm`, `m1`–`m28` e a sequência canônica de cinco destinos por **slot do pool**. Em cada pool, os slots `1–5` devem manter, na mesma ordem, seus pares `URL + jbf_operation` do baseline live; a correção redistribui somente as identidades `route + utm_content` para os grupos semânticos corretos.

`m0` e `nm` são invariantes prioritárias: devem permanecer, respectivamente, nos slots 1 e 2 do pool `001`, mantendo as URLs/operations desses dois slots. Não carregar para a nova posição a URL que uma rota M possuía enquanto estava embaralhada em outro pool, pois isso destruiria a ordem canônica dos cinco destinos.

Antes do write, comparar `pool → slot → URL + jbf_operation` e validar a cobertura única `m0`, `nm`, `m1`–`m28`; depois do write, exigir readback da mesma sequência de destinos por slot e dos grupos `001–006`. Abortar/rollback se qualquer URL/operation mudar de slot, se M0/NM mudarem de destino ou se houver perda/duplicação de identidade.

Na planilha, usar a coluna de URL calculada por `REGEXREPLACE(...;"/$";"")`, não a URL com barra final.

## Padrão Infinitynexx — Broadcast MCT MX-CC-ES

Fonte confirmada: mesma planilha/aba, linhas `110–132`. Campos operacionais: coluna A = pool, D = `route`, E = `utm_content`, G = URL calculada sem barra final.

Configuração:

- Nome: `in-mx-cc-en-mct broadcast NNN`
- `SOURCE=MCT`
- `COUNTRY=MX`
- `VERTICAL=CC`
- `LANGUAGE=ES`
- `MEDIUM=""` (vazio; não usar `SLOT_D`)
- `APPEND_PARAMS=false`

Redistribuição confirmada de 23 rotas:

- editar o `001` existente para manter `001–005`;
- criar `002` com `006–010`;
- criar `003` com `011–015`;
- criar `004` com `016–020`;
- criar `005` com `021–023`.

O pool `001` original pode conter as 23 identidades com destinos antigos diferentes da nova planilha. A planilha é a fonte para a nova distribuição de URLs. Derivar `jbf_operation` ao vivo a partir das rotas atuais que já usam cada URL-alvo; operações MCT são diferentes das operações Drip/Facebook e não podem ser inferidas pelo padrão Drip.

Fluxo seguro aplicado:

1. backup integral do `001` e da lista de pools;
2. validar as 23 identidades `route + utm_content` contra a planilha;
3. criar e validar `002–005` sequencialmente;
4. atualizar o `001` por `POST /routing/{id}` somente após os quatro novos pools passarem no readback;
5. confirmar união final de 23 identidades únicas, sem perda ou duplicação, e preservar os demais pools.

Se houver falha parcial, reconsultar o estado real antes de repetir. O executor deve ser idempotente: pool existente integralmente correto é preservado; divergência aborta. Não excluir pools para rollback sem a confirmação exigida para deleção.

## Redistribuição customizada com duas URLs

Quando Rodolfo fornecer duas URLs-alvo e pedir dois itens por pool sem uma nova planilha, usar como fonte as identidades `route + utm_content` do readback live atual; não recriar nomes ou conteúdos por inferência.

Ordem semântica confirmada:

- Drip com 30 rotas: `m0`, `nm`, depois `m1–m28`;
- Broadcast/MCT com 23 rotas: numeração `001–023`;
- primeira rota de cada par recebe a primeira URL informada;
- segunda rota recebe a segunda URL;
- se o total for ímpar, a última rota isolada recebe a primeira URL.

Fluxo seguro:

1. unir todas as identidades dos pools atuais da família e exigir sequência completa, unicidade e campos não vazios;
2. derivar as duas `jbf_operation` ao vivo separadamente por source (`FACEBOOK` e `MCT`);
3. criar primeiro os pools de sufixos ainda ausentes;
4. atualizar os pools existentes preservando IDs e nomes;
5. validar a união final sem duplicatas, somente as duas URLs, operações não vazias e preservação de pools não relacionados.

Caso validado Fincgriffin US-CAR-EN:

- nomes Drip `fincg-us-car-en-drip-NNN`, 15 pools de duas rotas;
- nomes MCT `fincg-us-car-en-mct-NNN`, 12 pools com distribuição `2×11 + 1`;
- URLs-alvo Lightstream primeiro e PenFed Auto Loan segundo;
- seis pools Drip e três MCT existentes atualizados; dezoito pools novos criados, sem deleção.

## Redistribuição ordenada com cinco URLs explícitas

Quando Rodolfo fornecer cinco URLs em uma ordem exata para refazer Drip e Broadcast, essa lista é a fonte autoritativa; não substituir a sequência por um snapshot de outro publisher.

1. Drip: ordenar as identidades como `m0`, `nm`, `m1`–`m28` e aplicar as cinco URLs ciclicamente. Resultado: 30 rotas, seis ocorrências de cada URL.
2. Broadcast: ordenar naturalmente as 23 identidades live (`001`, `001-2`, `002`, `002-2` etc.) e aplicar as cinco URLs ciclicamente. Resultado por URL: `5,5,5,4,4`.
3. Se o pedido for apenas troca de destinos, preservar IDs, nomes e topologia live. Porém, quando Rodolfo pedir a “mesma ideologia de sempre” com Drip 30 e Broadcast 23, a topologia canônica é obrigatória mesmo se o publisher ainda tiver pools únicos:
   - Drip `001–006`: seis pools de cinco rotas;
   - Broadcast `001–005`: `5,5,5,5,3` rotas;
   - renomear o pool-base legado para `001` e preservar seu ID;
   - criar e validar primeiro todos os sufixos `002+`; somente depois reduzir/renomear o base para `001`.
4. Se o pedido exigir exatamente 30 rotas Drip e houver uma identidade extra conhecida, como `m0-2`, removê-la somente do payload do pool, registrar a identidade e validar cobertura única de `m0`, `nm`, `m1`–`m28`.
5. Resolver `jbf_operation` ao vivo por `URL + SOURCE + MEDIUM`. Nunca transportar operação de outro publisher nem inventar por padrão nominal.
6. Se a URL publicada responder HTTP 200, Rodolfo tiver ordenado explicitamente o write e a operação ainda não existir no catálogo, a rota pode ser gravada com `jbf_operation` vazia somente como `success_with_adops_pending`. Reportar contagem exata por publisher/família e nunca declarar prontidão AdOps completa.
7. Preservar metadata legada mesmo quando incomum; por exemplo, um Broadcast existente com `SOURCE=FACEBOOK` e `MEDIUM` vazio não deve receber operação MCT por inferência.
8. Fazer backup integral, dry-run, writes reversíveis apenas sobre IDs existentes quando a topologia for preservada, readback imediato e nova sessão independente. Validar contagens, ordem das URLs, saúde, pools não relacionados e operações vazias.
9. Manter `freeze=false` em todas as rotas por padrão para que o Smart Routing continue otimizando. Ordem exata é configuração inicial, não autorização para congelar destinos. `freeze=true` só pode ser aplicado quando Rodolfo pedir explicitamente o congelamento e definir a duração/sessões; nunca inferir freeze como solução para um readback que mudou depois do write.

Caso corrigido em 2026-08-24: quatro publishers Finanzas US-CC-ES terminaram com 44 pools e 212 rotas — cada publisher com seis Drips e cinco Broadcasts. Lyzmo/Topfeed já estavam divididos; Newsoun/Eggbev exigiram 18 criações e quatro atualizações dos bases. A tentativa indevida de congelar a ordem foi revertida: 212/212 rotas ficaram com `freeze=false`, preservando o otimizador do Smart Routing.

## Comparação de cartões entre sites

Quando Rodolfo fornecer URLs de um site e perguntar se os mesmos cartões existem no Smart Routing de outro site, comparar pela **identidade do cartão**, não pela igualdade literal de domínio ou slug.

Distinguir obrigatoriamente três estados, sem tratar um como prova do outro:

1. **Página publicada** — a URL equivalente do site existe e responde HTTP 200 após redirects.
2. **Disponível no catálogo SB** — a página aparece em `/operations/{publisher}` ou no contrato live equivalente, com configuração FACEBOOK/Drip `.*-d$` e `jbf_operation` não vazia.
3. **Já aplicada na pool** — a URL está nas rotas do readback `/routing/{id}` da família solicitada.

Interpretação operacional:

- “Tem esse cartão nesse site / para usar?” → procurar primeiro a página equivalente por identidade e, para afirmar que pode ser selecionada imediatamente no Smart Routing, validar também o catálogo SB.
- “Está nessa pool?” → validar o readback da pool, mas não concluir que o cartão não existe no site ou catálogo apenas porque não está aplicado.
- Se a formulação puder abranger mais de um estado, reportar os três em vez de responder somente pela pool atual.

Procedimento:

1. Extrair o nome comercial do cartão da URL ou da referência fornecida.
2. Normalizar somente termos estruturais do slug (`rec`, país, vertical, `tarjeta`, `tarjeta-de-credito`, separadores e domínio).
3. Exigir os tokens distintivos do produto e emissor — por exemplo, `BBVA + Mastercard + Black`; não considerar apenas `Mastercard Black`, pois isso pode confundir BBVA com Itaú.
4. Diferenciar variantes próximas: `San Juan Internacional` não é `Banco San Juan Gold`; `BBVA Visa Gold` não é qualquer `Visa Gold`.
5. Para pool membership, consultar ao vivo todos os pools da família, incluindo nome-base legado e sufixos `001–NNN`.
6. Reportar por cartão: página publicada, catálogo SB, pool/rota atual e URL live encontrada. Se houver duplicatas, listar todas as rotas ou resumir a quantidade com os identificadores.
7. Igualdade de slug é evidência auxiliar, nunca pré-condição. Em caso de identidade ambígua, abrir a página ou catálogo live antes de concluir.

## Contrato live da SB

O bundle da tela define:

- listar pools: `POST /routing` com `{"publishers":["{company}_{publisher}"]}`;
- obter pool: `GET /routing/{id}`;
- criar pool: `POST /routing/0`;
- atualizar pool: `POST /routing/{id}`;
- excluir pool: `DELETE /routing/{id}` — continua sujeito ao Critical Subset de deleção.

Payload de criação usado pela própria UI:

- `ID`, `COMPANY`, `DOMAIN`, `NAME`, `SOURCE`, `COUNTRY`, `VERTICAL`, `MEDIUM`, `LANGUAGE`, `APPEND_PARAMS`;
- `ROUTES` como JSON string;
- cada rota contém, no mínimo, `route`, `utm_content`, `url`, `jbf_operation` e `healthy=true`; métricas novas ficam nulas.

Nunca imprimir ou persistir o header `Authorization`. Capturá-lo somente em memória a partir da requisição autenticada do browser quando a rota API direta for necessária.

## Fluxo de execução

1. Ler e validar as cinco linhas exatas da planilha.
2. Abrir a página live e confirmar `Zeus - Agent`, company e publisher.
3. Fazer backup da lista anterior e confirmar ausência do nome-alvo.
4. Preferir a UI:
   - `New routing pool`;
   - preencher nome e os cinco dropdowns;
   - manter `Auto url params` desligado;
   - para cada rota, preencher `Route` e `UTM_Content`;
   - digitar a URL sem barra, selecionar a sugestão exata e validar o campo `Operation` preenchido;
   - manter `Freeze` desligado;
   - salvar a rota local e, ao final, salvar o pool.
5. Se o botão final da UI não emitir requisição, não repetir cegamente. Confirmar ao vivo que o alvo ainda não existe, inspecionar o contrato do bundle e usar `POST /routing/0` com o mesmo payload da UI dentro do contexto autenticado.
6. Reconsultar `POST /routing` em uma sessão live nova.

## Validação obrigatória

- HTTP de criação `200/201`.
- Exatamente um pool com o nome solicitado.
- Metadata exata: source, country, vertical, language, medium e append params.
- Exatamente cinco rotas no pool.
- Readback exato de `route`, `utm_content`, URL e `jbf_operation` para cada rota.
- Contagem de pools aumenta em um.
- Pools preexistentes preservam metadata e identidades `route + utm_content`.
- Guardas de concorrência não devem exigir igualdade de URL/operação em pools antigos: o Smart Routing pode rearranjar destinos dinamicamente entre leituras. Para o pool recém-criado, validar URLs/operações imediatamente.
- Salvar evidências before/after e screenshot sem credenciais.

## Pitfalls observados

- `POST /routing` com status `201` é consulta, não criação; diferenciar pelo path (`/routing` versus `/routing/0`).
- A coluna operacional de URL pode apenas replicar a URL-base com `=CONCATENATE(B...)` e manter uma `/` final. Se todas as linhas estiverem consistentes e a operação live existir para a forma sem barra, normalizar somente o payload com remoção da barra final; não alterar a planilha.
- O pool legado pode existir sem o sufixo `001`. Nesse caso, fazer backup e atualizar o mesmo ID para o nome `... 001` com apenas o primeiro bloco; nunca criar um `001` duplicado.
- O grid staged pode não renderizar a URL apesar de o modal da rota ter `url` e `jbf_operation` preenchidos. Validar esses valores dentro do modal e no readback final.
- Toast `Successfully saved!` ao salvar uma rota significa apenas que ela entrou na lista local do modal; não prova criação do pool.
- Se o Save global não gerar rede, confirmar ausência do pool antes de qualquer retry ou fallback API.
- Não comparar pools antigos por URL exata para atribuir mudança concorrente; compare metadata e `route + utm_content`, e reconcilie audit/inventory/REPORT/Git/sessão antes de chamar anomalia.
