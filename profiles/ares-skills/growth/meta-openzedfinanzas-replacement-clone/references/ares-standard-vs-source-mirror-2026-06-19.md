# Ares Meta replacement — padrão oficial vs source mirror (2026-06-19)

## Contexto da correção do Rodolfo

Durante o troubleshooting de clone/replacement da conta `OpenzedFinanzas-CC-ES`, Rodolfo corrigiu a abordagem do Ares várias vezes:

- Não aplicar payload/padrão anotado quando o pedido é clonar uma campanha real.
- Não trocar campos da source por valores sugeridos por erro genérico da Meta quando a UI/API da source mostra outro valor.
- Não tratar campanhas manuais com 2 adsets/6 ads como se fossem o padrão Ares 1 adset/3 ads e chamar isso de clone.
- Separar a lógica de gestão/performance da mecânica de construção da campanha.

A raiz da confusão foi a palavra “clone” sendo usada para duas coisas diferentes.

## Dois conceitos que não podem ser misturados

```text
Conceito                         | Significado
---------------------------------|------------------------------------------------------------
Campanha Ares replacement         | nova campanha no padrão Ares, usando vencedores/insumos
Clone fiel / source mirror        | espelho estrutural da campanha source manual existente
```

### Campanha Ares replacement

Uso recomendado quando a conta está sob gestão 100% Ares ou está sendo migrada para padronização.

```text
Objeto      | Regra
------------|------------------------------------------------------------
Campaign    | nova, padrão Ares
Adset       | 1 adset
Ads         | 3 ads/criativos, nem mais nem menos
Budget      | máximo USD 25/dia inicialmente
Status      | PAUSED até validação/confirmação
Start       | D+1 01:00 no timezone da conta, convertido para UTC Z
Criativos   | vencedores por menor CPMO ou novos via Drive/agente legado
Loser       | arquivar/deletar só depois do replacement validado
```

### Clone fiel / source mirror

Uso recomendado para diagnóstico, migração, transição de conta legada/manual ou quando Rodolfo pedir explicitamente espelhar uma campanha existente.

```text
Objeto      | Regra
------------|------------------------------------------------------------
Campaign    | espelhar campos graváveis da source
Adsets      | preservar quantidade/estrutura real da source
Ads         | todos ou subset explicitamente definido
Campos      | copiar campos graváveis; descartar só read-only/ID/legado comprovado
Uso         | diagnóstico/migração/conta ainda tocada por gestor humano
```

## Regra operacional principal

```text
Ares decide                        | Source decide
-----------------------------------|-----------------------------------------------
por que testar/clonar               | estrutura técnica da campanha source
qual campanha é loser               | quantidade de adsets se clone fiel
quais criativos são vencedores       | targeting, attribution, DSA, promoted_object
quanto gastar                        | campos EU/compliance graváveis
quando arquivar/deletar loser        | detalhes de ads/creative se clone fiel
```

Se a conta será gerida 100% pelo Ares, o padrão oficial deve ser o **Ares replacement 1x3**. Campanhas manuais existentes entram como fonte de performance/assets/aprendizado, não como estrutura obrigatória permanente.

## Pitfalls aprendidos

1. **Não mudar attribution por causa do erro genérico da Meta.**  
   Se a source Elena mostra `7-day click, 1-day view` na UI/API, não substituir por `1-day click / 0 view` só porque uma criação incompleta retornou subcode sugerindo `(1,0)`. Isso indica que o contexto da campanha/adset novo ainda não está equivalente.

2. **Não chamar campanha Ares 1x3 de clone fiel.**  
   Se a source tem 2 adsets e 6 ads, criar 1 adset/3 ads é replacement padronizado, não clone estrutural.

3. **Não aplicar payload mínimo/padrão a campanha EU/financeiro.**  
   Antes de qualquer POST, puxar fields explícitos e compliance: `dsa_beneficiary`, `dsa_payor`, `regional_regulated_categories`, `special_ad_categories`, `special_ad_category_country`.

4. **Permissão de página é blocker real.**  
   Em Patricia, o raw error revelou: `El permiso de la página es insuficiente para publicar anuncios`. Nesse caso, não resolver mudando payload.

5. **Se campaign criada volta com `start_time=1970`, não ignorar.**  
   A campaign mãe pode estar malformada para validação posterior de adsets. Corrigir formato/campo antes de concluir que o adset está errado.

## Decisão pendente para OpenzedFinanzas

Antes de avançar com novos writes, Rodolfo precisa decidir o modo da conta:

```text
Decisão                                | Caminho
---------------------------------------|------------------------------------------------------------
Ares controla 100% a conta              | padronizar campanhas Ares 1 adset / 3 ads
Conta segue com gestor criando livre     | source mirror vira necessário para diagnóstico caso a caso
Transição de manual para Ares            | usar source mirror para aprender, recriar no padrão Ares
```

Enquanto essa decisão estiver pendente, o agente deve nomear claramente o caminho usado: **replacement Ares 1x3** ou **clone fiel/source mirror**.
