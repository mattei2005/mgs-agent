## Prioridade operacional: separar “replacement Ares” de “clone fiel”

Correção explícita do Rodolfo em 2026-06-19: não misturar a lógica de gestão/performance com a mecânica de construção da campanha. A palavra “clone” foi usada em dois sentidos e isso causou erro operacional.

```text
Caminho                         | Significado
--------------------------------|------------------------------------------------------------
Replacement Ares 1x3             | campanha nova padronizada: 1 adset, 3 ads, budget USD 25
Clone fiel / source mirror       | espelhar a estrutura real da campanha source: adsets/ads/campos
```

Se a conta estiver sob gestão 100% Ares, o padrão oficial deve ser **Replacement Ares 1x3**; campanhas manuais existentes servem como fonte de performance/assets/aprendizado, não como estrutura obrigatória. Se Rodolfo pedir clone fiel de uma campanha manual, então a source decide quantidade de adsets, attribution, DSA, regional compliance, targeting e demais campos graváveis.

Referência detalhada: `references/ares-standard-vs-source-mirror-2026-06-19.md`.

Referência Elena UI→API/source mirror: `references/elena-ui-api-source-mirror-2026-06-19.md`.

Referência do probe pragmático que destravou campaign + primeiro adset da Elena e isolou o bloqueio final em `POST /ads`: `references/elena-pragmatic-resolution-2026-06-19.md`.

Referência BM/Page vs bloqueio API em `POST /ads` mesmo com Marcos tendo Manage campaigns na ad account e controle absoluto da Página Elena: `references/bm-permissions-vs-api-ad-auth-block-2026-06-19.md`.

Referência final do token novo + clone full Elena funcional: `references/elena-full-clone-token2-success-2026-06-19.md`.

Referência da correção crítica de Rodolfo sobre clone perfeito e attribution 7/1: `references/perfect-clone-attribution-7-1-investigation-2026-06-19.md`.

Referência do teste da hipótese Zeus `attribution_setting=7d_click_1d_view` / `use_unified_attribution_setting`: `references/attribution-setting-probe-2026-06-19.md`.

Referência da descoberta do caminho API de draft/copy (`addraft_id` + `asyncadcopies`) e bloqueio de capability do app: `references/addraft-asyncadcopies-probe-2026-06-19.md`.

Referência dos probes posteriores de native/async copy, `standard_enhancements` obsoleto e formatos CTM/`creative_parameters` que falharam: `references/elena-native-copy-ctm-standard-enhancements-2026-06-19.md`.

Referência da correção posterior: `addrafts` não é o único caminho; `asyncbatch` com `/copies` inicia jobs sem API avançada, mas o clone perfeito Elena segue bloqueado em CTM creative copy (`standard_enhancements`, `messenger_doc`, `destination_spec`/template): `references/asyncbatch-copy-and-ctm-creative-parameters-2026-06-19.md`.

Referência dos probes que corrigiram a leitura sobre API avançada: asyncbatch público inicia sem addrafts, mas o clone Elena bloqueia em creative legado `standard_enhancements`/`messenger_doc`; próximos testes devem focar `/ad_id/copies` com `creative_parameters` plural e formato Click-to-Messenger correto: `references/asyncbatch-copy-and-creative-parameters-2026-06-19.md`.

### Status validado em 2026-06-19 — clone funcional e ativação funcionam

O bloqueio `code=31/subcode=3858385` em `POST /ads` foi resolvido após Rodolfo gerar novo token incluindo escopos de Página/Messenger:

```text
pages_manage_ads
pages_messaging
pages_manage_metadata
pages_manage_posts
```

Com o token novo, Ares validou:

```text
Operação                              | Status
--------------------------------------|------------------------------------------------
Criar campaign                        | OK
Criar adset                           | OK
Criar 3 ads                           | OK
Ativar campaign/adset/ads             | OK
Pausar campaign                       | OK
Clone full Elena 2 adsets / 6 ads     | OK
```

Objetos principais criados:

```text
Teste 1x3 TOKEN2 campaign             | 120248959079740604
Clone full Elena campaign             | 120248959247790604
```

O clone funcional da source `120248940367540604` criou 2 adsets e 6 ads, PAUSED, com budget source USD 100/dia. Porém Rodolfo corrigiu: isso **não** deve ser chamado de clone perfeito se a attribution divergir. Source Elena usa `7-day click + 1-day view`; rebuild manual retornou `1885501` e só criou com `1-day click`. Regra: para pedido de clone perfeito/“do jeitinho que é”, não aceitar essa divergência; continuar via native/async copy ou Ads Manager UI duplicate até preservar 7/1, ou reportar impossibilidade objetiva. `CLICK_THROUGH 1` é apenas workaround de clone funcional/teste, não clone perfeito.

Correção anterior do Rodolfo: quando o pedido for clone fiel, priorizar **clone/source mirror** como os buyers/Ads Manager fazem, não criação from-zero genérica. Criação from-zero pode falhar para este usuário/token e só ser viável em outro contexto de System User; **não usar criação do zero genérica como prova, teste principal ou resposta operacional quando Rodolfo pedir clone fiel**.

Regra de interpretação do escopo:
- Campanhas `ACTIVE` e `PAUSED/OFF` são fontes válidas de clone. `PAUSED` não é deletada.
- Ares deve conseguir listar e analisar todas as campanhas visíveis da conta, ligadas ou desligadas, e escolher a melhor base conforme as regras de performance quando o fluxo estiver estabilizado.
- Para testes iniciais de clone, se Rodolfo disser "qualquer uma da conta", tentar qualquer campanha viável; basta uma funcionar para desbloquear o método e depois voltar ao ranking/regras.
- Só considerar sucesso se o clone/copy trouxer estrutura utilizável com adsets/ads. Uma cópia rasa de campaign sem adsets/ads é artefato parcial e deve ser deletada/verificada.

Fluxo preferido para nova tentativa:

```text
Ordem | Caminho
------|------------------------------------------------------------
1     | Validar token e listar campanhas/adsets/ads incluindo OFF/PAUSED
2     | Tentar Meta native copy endpoints (`/copies`) preservando PAUSED
3     | Se campaign `deep_copy` regular falhar por limite de objetos, testar o mesmo `/copies` dentro de `asyncbatch` antes de concluir capability/addraft
4     | Se campaign rasa copiar só shell, não chamar de sucesso; testar adset/ad copy nativo
5     | Se copy falhar por `standard_enhancements`, aplicar `creative_parameters` no nível `ad_id/copies`; em adset/campaign deep copy isso não sobrescreveu o blocker
6     | Para CTM/Messenger, não usar `messenger_doc` como website externo nem `destination_spec.message_destination.page_id`; testar `object_story_spec.link_data.page_welcome_message` ou obter payload/HAR sanitizado do clone que funciona
7     | Só usar rebuild manual de creative/ad como diagnóstico separado, nunca como substituto do clone pedido
8     | Validar GET e deletar qualquer cópia rasa/parcial sem adsets/ads esperados
```

Pitfalls validados:
- `/<campaign_id>/copies` sem `deep_copy` cria só uma campanha vazia. Não considerar isso clone bem-sucedido; verificar contagem de adsets/ads antes de manter.
- Em 2026-06-18, `/<campaign_id>/copies deep_copy=true` falhou nas 20 campaigns visíveis com `code=100/subcode=1885194`; adset copy raso/deep também falhou em Elena com `1885501`/`1885194`. Isso não significa que campanhas estão invisíveis; significa que o payload público simples ainda não reproduz o clone do Ads Manager/buyers.
- Se o usuário corrigir "não é para criar do zero", parar de misturar fallback from-zero no relatório e responder apenas sobre clone/copy nativo.

Detalhes de sessão e erros Meta de copy nativo:
- `references/native-copy-standard-enhancements-2026-06-18.md`
- `references/native-copy-all-campaigns-probe-2026-06-18.md`
