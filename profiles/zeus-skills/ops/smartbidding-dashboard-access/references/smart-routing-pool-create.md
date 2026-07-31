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

Na planilha, usar a coluna de URL calculada por `REGEXREPLACE(...;"/$";"")`, não a URL com barra final.

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
- O grid staged pode não renderizar a URL apesar de o modal da rota ter `url` e `jbf_operation` preenchidos. Validar esses valores dentro do modal e no readback final.
- Toast `Successfully saved!` ao salvar uma rota significa apenas que ela entrou na lista local do modal; não prova criação do pool.
- Se o Save global não gerar rede, confirmar ausência do pool antes de qualquer retry ou fallback API.
- Não comparar pools antigos por URL exata para atribuir mudança concorrente; compare metadata e `route + utm_content`, e reconcilie audit/inventory/REPORT/Git/sessão antes de chamar anomalia.
