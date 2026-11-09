# SHEIN — contrato de intake e emendas

Use ao converter pedidos naturais em input do runner comum. Para mídia, autoridade, lease, execução e recuperação detalhadas, seguir `general-campaign-fast-route.md`; esta referência resolve a escolha inicial de campos e comandos, não substitui os gates.

## 1. Resolver a intenção e suas correções

1. Vincule conta e origem ao catálogo positivo e ao canal real. Se a campanha-fonte estiver ausente ou indicada apenas por placeholder, pergunte somente pelo número ou ID; não escolha a campanha de um pedido anterior.
2. Trate esclarecimentos e reenvios explicitamente corretivos como emendas ao mesmo pedido, não como autorização de outro lote. Preserve request, relógio original, parâmetros não alterados e efeitos existentes; registre separadamente mensagens de esclarecimento e correção.
3. Reúna todas as partes de uma correção dividida em mensagens antes de executar. Antes de selar o manifest, incorpore somente os campos corrigidos ao input e registre a supersessão. Depois de selado ou de qualquer write, preserve documentos e IDs imutáveis e use a recuperação central aplicável; não sobrescreva manifests históricos.
4. Aplique a correção ao campo explicitamente indicado. Texto fornecido em `headline` continua sendo headline, mesmo que o operador o chame informalmente de botão. Preserve-o literalmente e mantenha a CTA nativa e os demais textos quando não houver outra alteração expressa.

## 2. Traduzir o lance para o contrato do intake

- Use em `bid_strategy` somente os aliases exatos `MAXVOL`, `COCAP` ou `BIDCAP` aceitos pelo intake.
- Para Cost per result goal, informe `COCAP` e o `bid_usd` exato solicitado. O compiler resolve o enum Meta `COST_CAP`; não envie esse enum no lugar do alias de intake.
- Sem alteração de lance pedida, preserve a herança da fonte real; a tradução de aliases não autoriza inventar um cap.

## 3. Escolher o preflight correto

- **Referência explícita entre contas:** use `reference-preflight --input <request.json> --dry-run`, com `source_account`, antes da preparação. Esse subcomando verifica o contrato de referência entre contas; não é o preflight genérico de clones na mesma conta.
- **Clone na mesma conta com grupos de arquivos do gestor:** confira admissão/lease e resolva a pasta canônica; execute `prepare-media --input <request.json> --confirm-execute`. Depois use `campaign --input <request-ready.json> --dry-run`; somente com plano aprovado execute o mesmo `campaign --confirm-execute`.
- **Clone sem mídia nova:** use diretamente `campaign --input <request.json> --dry-run` e, após validação, o mesmo comando com `--confirm-execute`.

A ausência de `asset_refs` antes de preparar mídia nova não exige referências artificiais nem mudança de modo: o preparador canônico produz o request-ready. Antes de retomar uma preparação interrompida, reconcilie uploads e reservas já existentes conforme a referência de recuperação; não interprete uma rejeição posterior ao upload como prova de ausência de mídia.

## 4. Validar o input antes do writer

Exija quantidade de grupos igual à quantidade solicitada, arquivos únicos por linhagem e contagem exata de assets. Compare fonte, budget, lance, início, idioma, arquivos, textos e headlines com a intenção corrigida, não com exemplos ou pedidos anteriores. Confirme no dry-run que criação PAUSED e barreira global de QA preservam o status final aprovado. Preparação bem-sucedida e dry-run não comprovam campanha criada, ativação ou serving.
