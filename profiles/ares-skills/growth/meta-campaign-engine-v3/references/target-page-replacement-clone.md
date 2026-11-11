# Duplicação com Page, mídia e copy substituídas

## Admissão e separação de responsabilidades

- Resolver a capability e sua autoridade no contrato exato da operação e no config da conta. `clone_target_prestaged` é um modo próprio; nunca habilitar o legado copied-adset Page switch, converter silenciosamente para from-zero, mudar outra conta ou supor que uma regra de naming habilita o executor.
- Manter manutenção estrutural separada da transação de campanha, com integrador único, backup/inventário, testes isolados e REPORT-INFRA. Uma aprovação para esta modalidade e futuros equivalentes não publica automaticamente pedidos futuros nem libera credenciais, ACL, billing, estratégias ou exclusões.
- Conservar fonte e OK comercial; cada pedido traz Page/mídia/copy/budget/início exatos, sua reserva atômica, manifest selado e resumo final. A modalidade preserva sementes técnicas PAUSED: informar explicitamente sua quantidade, separada dos anúncios finais ativos, antes do OK do manifest.

## Arquitetura executável

- Materializar a configuração de campanha/conjunto a partir de GETs da fonte, preservando público, lance, atribuição, placements e recursos individuais, exceto deltas expressos e a política vigente de background. Não usar o modelo de criação default no lugar da fonte.
- Criar shell novo derivado da fonte e um conjunto já com `promoted_object.page_id` alvo. Não alterar o conjunto-fonte ou tentar trocar a Page de um AdG copiado.
- Rematerializar creatives/mídia/copy na Page alvo e criar sementes PAUSED. Os anúncios finais são cópias dessas sementes na **mesma Page e mesmo conjunto**, nunca cópias de anúncios da outra Page. Preservar sementes e seus IDs, sem DELETE.
- O adaptador central `target_page_clone` usa exclusivamente os batches/journal/checkpoints do Engine. Após interrupção, reconciliar IDs confirmados por slot; POST incerto sem recibo exige inventário exato/paginado e match único antes de adoção, nunca replay cego. Falha de QA semântico contém o pai em PAUSED e confirma isso por GET.
- Readback exige conta/nome/budget/lance/início, Page/evento/público/conjunto, cardinalidade final+sementes, sementes PAUSED, `source_ad_id` local, copy literal, CTA, tracking, JSON-AGT e mídia. IDs de vídeo rematerializados exigem reconciliação de linhagem; não enfraquecer o comparador para obter sucesso. ACTIVE não comprova serving.

## Identidade da Page

- Usar somente o pg inteiro, publisher corporativo exato e a identidade anunciante da conta. O resolvedor `eggbev_page_identity` confere mapping SB vivo único e o GET Meta da própria Page; o contexto efêmero não grava provenance artificial nem concede write genérico à Page.
- Remover Page Access Token do objeto antes de state/audit. PBIA é a identidade shadow da própria Page, não uma credencial ou conta externa. Resolver GET primeiro; apenas preparação explícita de request persistido permite inicializá-la se o GET vier vazio, seguida de GET e receipt. Não cadastrar permissões, importar Pages à BM, trocar token ou fazer outro write de Page.

## Runner operacional

Resolver o runner pelo contrato; a operação Eggbev01 usa `scripts/ares-eggbev-target-clone.py`:

```text
prepare --input <request.json> --confirm-prepare
execute --input <request.json> --confirm-execute --approved-digest <digest integral> --approval-message-id <OK posterior ao resumo>
finalize --input <request.json>
```

- Prepare nunca publica campanha: valida source/Page, pasta exata de gestor e linhagem, reconcilia, reserva, baixa/verifica clean, prepara vertical+square, faz pre-stage, sela e planeja. Repetir prepare após resumo preserva o mesmo selo/digest; horário vencido é resolvido com o operador.
- Variante quadrada preserva quadro completo com padding quando o crop removeria texto/rostos; conferir visualmente os quadros reais.
- Se o upload ocorreu e o wait-ready parou por provenance local, varrer uma vez `act_<conta>/advideos` pelos títulos determinísticos. A resposta account-scoped comprova os IDs; retomar o preparador e adotar as variantes já existentes, sem POST duplicado nem alteração do guard.
- Finalize usa anúncios finais/creatives reais para gravar assignments e invocar `ares_manager_storage_standard.confirm_usage`; AFS pode representar o vídeo em `asset_feed_spec.videos`. Exigir ID de mídia exato e receipt do mesmo stock ID em Usados. Falha preserva pós-processamento pendente, sem repetir Engine.

## Reconciliação de leitura e variantes derivadas

- Separar drift comercial de URLs temporárias: `thumbnail_url` assinada pode mudar entre dois GETs consecutivos da mesma fonte. Preservar snapshots e comparar todos os demais campos antes de atualizar evidência; não alterar mídia/copy/estrutura nem tratar URL rotativa como autorização para repetir criação. Se o wrapper bloquear por igualdade bruta, registrar a limitação e as provas sem editar o runner na transação.
- Quando o vídeo derivado retornar `source` ausente com o User Access Token, tentar somente o Page Access Token efêmero da própria Page já validada, obtido com a mesma identidade anunciante. Ausência desse campo não prova ausência de vídeo ou de permissão. Manter escopo/provenance ativos; o GET de dependência de vídeo aceita `id,title,length,status,source`, não `format`. Obter dimensões do arquivo baixado com ffprobe.
- Antes de aceitar IDs derivados, exigir bijeção completa por slot e labels, marker do asset/checksum no título, duração, dimensões, ready/fases completas, igualdade SHA-256 dos bytes baixados e quadros decodificados. Falta ou diferença mantém PAUSED. Não substituir os IDs originais no registry nem reeditar manifests selados; guardar as duas identidades e a prova separadamente.
- Uma equivalência byte a byte comprovada pode resolver apenas a expectativa de mídia em memória para QA: executar o comparador original inalterado contra GETs reais e todos os demais campos aprovados. Nunca modificar uma resposta API para produzir PASS. Sob o mesmo request/locks e OK de ativação, recuperar somente o status do pai existente após pre-QA integral; confirmar novamente a hierarquia e o comparador. Preservar erro inicial, IDs e selos; diferenciar retorno original do Engine de recuperação verificada independente no audit.
- Na finalização de variantes derivadas comprovadas, gravar no inventário o vídeo efetivamente instalado no anúncio, preservando o vínculo aos IDs prestageados na prova, e chamar o controlador `confirm_usage`. Exigir receipt real de Usados e ledger comprometido antes de liberar a lease; jamais reexecutar criação para satisfazer igualdade literal de IDs.

## Verificação de manutenção

- Testar shape/capability fail-closed, Page divergente, source preservada, plano/stages, Engine real com transporte em memória, retomada após resposta de seed perdida, idempotência e contenção PAUSED.
- Testar dependência de Page apenas durante mapping fresco, ausência/ambiguidade, outra conta, writes proibidos, PBIA pre-read/POST/GET e remoção do contexto em finally.
- Executar suites existentes de naming, asset-scope e manager-storage. Se suites antigas falharem por contratos já supersedidos, reproduzir contra o runtime anterior isolado e comparar os IDs dos testes; não afrouxar produção nem declarar a suíte inteira verde.
