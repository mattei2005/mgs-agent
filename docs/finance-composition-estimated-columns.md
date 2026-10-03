# Composição financeira — colunas de estimativa

Autoridade: Rodolfo `1555934054132486275`, após confirmação de entendimento em `1555929386564460567`, thread `1545426987756298340`.

## Contrato aprovado

Na tabela **Composição financeira** do Dashboard, acrescentar, à direita das colunas atuais, **Valor $ Estimado** e **Valor R$ Estimado**. Vigência: competências válidas de outubro/2026 em diante, sem teto de ano. Setembro/2026 e anteriores preservam seu layout. Novas competências herdam o padrão quando cadastradas; não criar meses por essa autorização.

- Preservar os componentes e todos os valores atuais. As duas novas colunas detalham por componente a estimativa que já existe no motor, sem gravação financeira, recálculo de folha ou alteração de pagamento.
- Receita bruta, inválidos, rev share, impostos, mídia e SMS usam apenas o acumulado dos dias completos do `domain.realized`, multiplicado por `dias do mês / dias completos`. A coluna Receita preserva a semântica da linha existente; inválidos permanecem uma dedução separada e nunca entram duas vezes no resultado.
- Despesas Gerais e funcionários usam os valores mensais de `domain.cash` uma única vez; não extrapolar novamente os totais mensais.
- Resultado total estimado é duas vezes `domain.projection.half_usd`; participação estimada usa exatamente esse campo. Conversão BRL pela cotação ativa da competência.
- Sem dias completos ou em mês futuro, estimativa indisponível (`—`), não zero fabricado. Mês totalmente realizado usa fator1.
- Preservar a linha final existente Estimativa do mês ·50%; sua nova coluna repete a própria estimativa, nunca a extrapola novamente.
- Desktop deve mostrar todas as cinco colunas sem esconder a última na metade estreita do Dashboard. Mobile mantém rolagem dentro da tabela, sem overflow global.

## Verificação e estado

Checkpoint `ZEUS-FINANCE-COMPOSITION-1555934054132486275`. Evidência isolada em `apps/finance-system/private/composition-1555934054132486275/`. A aprovação deste contrato não constitui prova de publicação; consultar relatório final, journal e runtime.

Testar fronteiras de vigência, mês cheio, zero dias, futuro, sinais negativos, SMS apenas realizado, despesas mensais descontadas uma vez, projeção igual ao motor, soma dos componentes, preservação das colunas originais, desktop/mobile, ausência de escritas financeiras e hashes/revisões do banco.
