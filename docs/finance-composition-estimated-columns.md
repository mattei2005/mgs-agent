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

## Confirmação posterior — manter implementação atual

Rodolfo `1556011979565572157` esclareceu que havia se confundido e confirmou como correto o funcionamento atual: o estimado de Despesas Gerais e Despesas dos funcionários utiliza o total mensal da respectiva seção de despesas. Manter a implementação existente, inclusive a apropriação proporcional no realizado. Não aplicar a sugestão do Zeus de recalcular comissões por resultado projetado nem trocar o realizado pelo total mensal com base no áudio anterior.

Esta confirmação resolve e supersede a dúvida registrada no candidato `KCI-0de4201aa3b85bea` (áudio `1556000424006520942`); o candidato permanece apenas como histórico, não como pendência ou regra ativa. Não houve alteração de código, dados financeiros, folha, pagamento ou fórmulas nesta confirmação.

## Divisão visual dos blocos — Rodolfo1556369322782232598

Na composição com cinco colunas (outubro/2026 em diante), separar visualmente os blocos Componente, valores realizados e valores estimados com divisórias verticais neutras após as colunas1 e3. Exibir os cabeçalhos e valores de `Valor $ Estimado` e `Valor R$ Estimado` em negrito. Mudança exclusivamente CSS: preservar componentes, valores, fórmulas, cores de sinal e layout histórico. Verificar estilo computado em todas as linhas, cinco colunas visíveis no desktop e rolagem interna no celular. Evidência desta entrega: `reports/finance-composition-style-1556369322782232598.md`.

## Verificação e estado

Publicação concluída pelo controlador canônico; relatório `reports/finance-composition-1555934054132486275.md`, journal committed e readback financeiro/navegador aprovados. Checkpoint `ZEUS-FINANCE-COMPOSITION-1555934054132486275`. Evidência isolada em `apps/finance-system/private/composition-1555934054132486275/`.

Testar fronteiras de vigência, mês cheio, zero dias, futuro, sinais negativos, SMS apenas realizado, despesas mensais descontadas uma vez, projeção igual ao motor, soma dos componentes, preservação das colunas originais, desktop/mobile, ausência de escritas financeiras e hashes/revisões do banco.
