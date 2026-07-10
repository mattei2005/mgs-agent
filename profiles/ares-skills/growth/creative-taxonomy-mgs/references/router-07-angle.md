## ANGLE

`ANGLE` deve vir de dicionário controlado por operação/idioma.

Regras:

- Não inventar ângulo confiante sem evidência textual/visual.
- Se houver dúvida, usar `UNKNOWN` no plano de renomeação e preencher `notes`.
- Padronizar por idioma quando fizer sentido, mas manter comparabilidade operacional.

Exemplo inicial para CC em espanhol:

```text
ANGLE              | Significado operacional
-------------------|--------------------------------------------------
APROBACION          | Aprovação / pré-aprovação
SIN_VERIFICACION    | Sem verificação / baixa fricção
LIMITE_ALTO         | Limite alto
SIN_CREDITO         | Público sem crédito / histórico limitado
MAL_CREDITO         | Público com crédito ruim / negativado
CASHBACK            | Cashback / recompensas
RECOMPENSAS         | Benefícios, pontos, milhas
COMPARACION         | Escolha/comparativo entre cartões
WALLET              | Uso cotidiano, carteira, pagamento do dia a dia
URGENCIA            | Urgência, aprovação rápida, necessidade imediata
UNKNOWN             | Ângulo incerto; exige note
```

Exemplo inicial para CC em francês:

```text
ANGLE                | Significado operacional
---------------------|--------------------------------------------------
APPROBATION           | Aprovação / pré-aprovação
SANS_VERIFICATION     | Sem verificação / baixa fricção
LIMITE_HAUT           | Limite alto
CHOIX                 | Escolha/comparativo
WALLET                | Carteira / uso cotidiano
UNKNOWN               | Ângulo incerto; exige note
```
