# Meta Business — criação de contas de anúncios via sessão autenticada

Use quando Rodolfo pedir para reproduzir no Business Settings a criação de uma ou várias contas de anúncios usando um usuário do Facebook que já está logado.

## Identidade e alvo

- Respeite a identidade pedida. Se o pedido diz “com o usuário logado”, não substitua silenciosamente por outro user token/API token.
- Confirme por readback o nome do perfil Facebook, o Business Portfolio e o `business_id` antes de qualquer write.
- Use a rota exata `https://business.facebook.com/latest/settings/ad_accounts?business_id=<BUSINESS_ID>` (`ad_accounts` com underscore).
- Uma URL aproximada ou um `business_id` herdado de outra tarefa pode abrir a BM errada. Se o usuário corrigir a BM, abandone o modal atual e reinicie pela URL canônica corrigida.
- Correção observada: `BM Contingencia` usa `business_id=549832605570065`; `Steamp` (`1287360049252313`) não é o alvo do fluxo de criação de contas `001`.

## Reautenticação segura

1. Abra Chromium headed com o perfil persistente e lock exclusivo.
2. Exponha noVNC somente em localhost; Rodolfo acessa por túnel SSH local.
3. Rodolfo completa passkey/2FA diretamente na tela remota. Nunca peça senha ou código no Discord.
4. Mantenha janela e túnel abertos até o readback final.
5. Se Playwright já estiver rodando sem CDP acessível, abra a URL no mesmo processo via Chromium ProcessSingleton, usando o mesmo executável e `--user-data-dir`. O marcador esperado é `Opening in existing browser session.`; confirme por screenshot.
6. Ao encerrar, feche o contexto limpo, libere o lock e valide processos do profile e portas localhost/noVNC.

## Pré-write obrigatório

- Confirmar novamente Business Portfolio, seção `Ad accounts` e lista atual.
- Verificar se já existe conta com o nome pretendido. Nomes repetidos podem ser permitidos; não usar o nome como identificador único.
- Abrir `Add` → `Create a new ad account` e ler controles desabilitados, tooltips e gates.
- Se aparecer `You've reached the maximum number of ad accounts allowed for a new business portfolio`, parar e reportar que nenhuma conta foi criada. Não tentar contornar via outra BM/identidade.
- Se o usuário declarar um limite alto, ainda assim respeitar qualquer gate real da Meta mostrado durante a execução.
- Não usar intervalos aleatórios para simular comportamento humano ou evitar detecção. Para lote autorizado, use cadência fixa e transparente e pare em qualquer checkpoint, restrição ou verificação.

## Parâmetros e confirmação

1. Preencher nome, timezone e moeda exatamente.
2. Confirmar os valores na etapa `Details` antes de `Next`.
3. Confirmar `My business` ou o uso explicitamente autorizado.
4. Na etapa final, revisar a BM correta antes de aceitar os termos e criar.
5. Tratar aceitação de termos e alteração de pessoas/permissões como escopos distintos; não transformar criação de conta em mudança de permissão implícita.

Valores usados no fluxo observado:

```text
name      001
timezone  America/Los_Angeles
currency  USD
usage     My business
```

## Lote seguro: checkpoint por conta

Para lote explicitamente autorizado:

1. Criar uma conta por iteração.
2. Persistir imediatamente sequência, Ad Account ID real, resultado visual e timestamp.
3. Verificar unicidade do ID antes de avançar.
4. Usar cadência fixa entre contas.
5. Em erro ambíguo, reconciliar o estado antes de qualquer retry.
6. Parar em mudança de alvo, auth gate, security check, restrição ou divergência de mais de um ativo.

Nunca considerar o clique em `Create ad account` como sucesso. O sucesso exige modal ou asset-state readback.

## Armadilha: erro visual pode ter side effect

Foram observados estes retornos após `Create ad account`:

```text
Ad account created
Ad account created successfully
Unable to add ad account — Network request timed out
Unable to add ad account — Error performing query
```

Os dois últimos são ambíguos: um timeout não criou conta; outro `Error performing query` criou a conta apesar do erro visual. Regra obrigatória:

1. Não repetir imediatamente.
2. Recarregar `Ad accounts` na BM correta.
3. Comparar o conjunto de IDs antes/depois.
4. Se surgiu exatamente um ID novo, registrar como criado e não repetir.
5. Se não surgiu ID novo, uma única repetição controlada pode ser feita após intervalo fixo.
6. Se surgirem vários IDs ou o alvo mudar, parar como divergência concorrente.

## Identificação real do ativo

- `selected_asset_id` da URL é um identificador interno do Business asset e pode ser diferente do Ad Account ID mostrado como `ID:`.
- A lista visual é virtualizada. Contar linhas `001`, confiar na posição da primeira linha ou comparar apenas texto visível pode oscilar conforme o render e produzir falso positivo.
- O payload serializado renderizado contém pares como:

```text
business_object_id      identificador interno do asset
business_object_name    nome visível (`001`)
business_asset_type     `AD_ACCOUNT`
business_object_ui_id   Ad Account ID real
```

- Para lote, capture antes/depois os `business_object_ui_id` dos objetos `AD_ACCOUNT` e use diferença de conjuntos. Um probe prático pode extrair IDs do HTML renderizado com uma regex limitada ao campo, por exemplo `business_object_ui_id.{0,40}?(\d{10,})`, deduplicando o resultado. Filtre/valide tipo e nome quando o payload trouxer outros assets.
- O ID mais novo deve ser confirmado também no painel de detalhes quando possível: `ID: <id>` e `Owned by: <BM correta>`.

## Permissões e lacunas

- BM ownership e pessoa diretamente atribuída são estados diferentes.
- Uma conta pode aparecer como `Owned by: BM Contingencia` e ainda mostrar `0 people are assigned to this ad account`.
- Adicionar Rodolfo ou qualquer pessoa é mudança de permissão separada. Não fazê-la como reparo automático; reportar o ID afetado e pedir a confirmação exigida.
- Em relatório final, separar: criação confirmada, BM owner, pessoa atribuída, pagamento e qualquer falha parcial.

## Readback final

- Validar total solicitado, quantidade de IDs únicos e ausência de duplicatas.
- Confirmar os IDs mais recentes no DOM/payload live e manter evidência por iteração para os IDs que saíram da janela virtualizada.
- Registrar falhas transitórias reconciliadas sem maquiá-las.
- Não inferir acesso por regex no `body` global. A lista virtualizada pode manter vários `0 people`, `1 person`, nomes e até `Full access` de linhas que não são a conta selecionada.
- Para cada conta, navegar diretamente pelo `selected_asset_id`, confirmar `ID:` + `Owned by:`, clicar semanticamente `page.getByRole('tab', {name: 'People', exact: true})` e esperar a frase `N person/people ... assigned to this ad account`.
- Para afirmar acesso de Rodolfo, esperar no conteúdo da aba `People` a combinação `Rodolfo Mattei (You)` + `Full access`; uma leitura imediata pode capturar apenas a contagem enquanto a lista da pessoa ainda carrega.
- Se o readback final corrigir uma observação incompleta feita logo após a criação, preservar a observação original como histórico e promover o estado final validado no checkpoint, sem reexecutar criação nem atribuição.
- Não afirmar pagamento configurado sem readback; criação padrão pode terminar sem payment info.

## Caso observado em 2026-08-06

- Perfil Facebook autenticado: Rodolfo Mattei.
- Alvo corrigido pelo usuário: `BM Contingencia`, `business_id=549832605570065`.
- Uma primeira conta `001` foi criada manualmente e validada.
- Depois, 20 contas adicionais `001` foram criadas com `America/Los_Angeles`, `USD` e cadência fixa.
- Os 20 IDs adicionais eram únicos; cada criação teve confirmação por modal ou diferença real de asset IDs.
- A UI apresentou um timeout sem side effect e um erro de query com side effect; ambos foram reconciliados antes de retry.
- Uma conta (`1520181556034088`) ficou BM-owned, mas com `0 people` diretamente atribuídas. Nenhuma mudança de permissão foi feita sem confirmação.
- O contexto persistente foi fechado e não restaram processos do profile.
