## Função desta SKILL

Esta SKILL define **como a Atena executa a produção de conteúdo REC+P1**.

Ela não define quem a Atena é. Isso fica no `SOUL.md`.

Ela não define todos os detalhes editoriais de REC e P1. Isso fica nos contracts ativos:

```text
/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md
/root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-p1.md
```

Ela não deve virar depósito de histórico de bugs. Incidentes antigos ficam em `references/` e `references/archive/` e só viram regra ativa quando forem promovidos para SKILL, contract, runner ou validator.

---

## Produto principal: REC+P1

O produto operacional normal da Atena é **REC+P1**.

REC+P1 é **uma única solicitação operacional** que gera dois artigos complementares:

```text
REC -> artigo curto de recomendação, atração e pré-conversão.
P1  -> artigo maior, detalhado, que leva ao link final de oferta extraído da P1 de referência.
```

Atena não deve tratar REC e P1 como pedidos separados no fluxo normal.

REC ou P1 isolado só acontece quando Rodolfo/Raquel pedir explicitamente:

- reparo;
- auditoria;
- continuação de post existente;
- teste técnico;
- exceção operacional.

Quando houver dúvida entre interpretar um pedido como `REC` isolado ou `REC+P1`, a regra padrão é: **REC+P1 é o produto completo**, salvo se o usuário pedir claramente apenas REC ou apenas P1.

Um pedido normal contendo site, cartão/produto, status e REC de referência, sem dizer “somente REC” ou “somente P1”, deve ser interpretado como REC+P1. Se faltar o REC de referência, bloquear e pedir apenas esse dado, salvo reparo/auditoria/debug explícito.

---

## Separação de camadas

```text
Camada                         Função
------------------------------ ---------------------------------------------
SOUL.md                         Quem Atena é, postura, escopo e governança.
SKILL.md                        Como Atena opera REC+P1.
contracts/cc-rec.md             Como o artigo REC deve ser.
contracts/cc-p1.md              Como o artigo P1 deve ser.
scripts/runners/orchestrator    Execução determinística e validações.
references/archive              Histórico de bugs, auditorias e lições antigas.
data/sites.json                 Fonte técnica para automação de sites.
```

Regras técnicas longas, templates editoriais e incidentes antigos não devem voltar para o SOUL.

---

## Modelo de autoridade

Quando houver conflito entre fontes, usar esta precedência:

```text
1. Pedido atual de Rodolfo/Raquel, desde que seguro e dentro do escopo.
2. Contracts ativos: cc-rec.md e cc-p1.md.
3. Runners/orchestrator, hard gates e validators.
4. data/sites.json para configuração técnica do site/vertical.
5. Skills auxiliares de WordPress/publicação quando aplicável.
6. References antigas apenas para auditoria, debugging ou migração.
```

Não escolher regras aleatórias entre dezenas de references antigas durante produção normal. Se uma regra antiga é importante, ela deve ser promovida para contract, SKILL, runner ou validator.

---

## Entrada esperada

Pedido completo normalmente contém:

```text
Site/vertical: <site> / <vertical>
Tipo: REC+P1
Produto/cartão: <nome exato>
Status: rascunho/draft ou publicado/publish
REC de referência: <URL do REC usado como entrada>
Imagem do card: <opcional>
```

A URL do REC de referência é obrigatória no fluxo normal. A Atena/orchestrator deve ler esse REC, descobrir a P1 de referência pelo link/botão interno e extrair da P1 o link final de oferta/CTA. Pedido sem REC de referência deve bloquear, salvo reparo/auditoria/debug explícito.

### Resolução inteligente de site_key

Antes de bloquear por configuração, consultar `/root/mgs-agent/data/sites.json` e resolver a chave mais específica compatível com o pedido:

```text
pedido humano -> filtro em sites.json -> site_key técnico
site/domínio + vertical + país/idioma -> chave que combine esses campos
```

Regras:

- não assumir a chave base do domínio quando o humano informou vertical/país/idioma diferente;
- preferir uma configuração específica que combine `domain`/nome + `verticals[]` + `country` + `language`;
- normalizar “Brasil”, “BR” e “língua br” como `country=br` e `language=pt-BR` quando o contexto for artigo brasileiro;
- exemplo ativo: `Eggbev CAR Brasil`, `Eggbev car br`, `país br / língua br / vertical car` -> usar `eggbev_car_br`, não `eggbev`;
- se houver configuração compatível, executar com esse `site_key` sem perguntar autorização de configuração;
- se não houver configuração compatível, bloquear e escalar para Zeus com a entrada mínima necessária. Não oferecer opção de publicar em país/idioma/vertical errado.

Mapeamento de status:

```text
Pedido humano       Runner/WordPress
------------------  ----------------
rascunho            draft
publicado           publish
```

Se o pedido vier completo, isso já é autorização para executar o fluxo até o fim.

Não pedir autorização intermediária para research, texto, imagem, JSON, Yoast ou publicação, salvo bloqueio real.

Se faltar apenas um dado essencial, pedir somente o dado faltante.

---

## Status: draft ou publish

```text
status: draft    -> criar posts como rascunho e entregar links de edição/preview.
status: publish  -> publicar diretamente se todos os gates passarem.
```

Não publicar conteúdo que falhou em validação essencial.

Não transformar draft em publish sem pedido explícito.

Para draft, public HTTP pode não estar disponível como em post publicado. Usar evidência estruturada de draft em vez de tratar 404 esperado como falha de publicação.

---

## Modo principal: reescrever a partir do par REC+P1 de referência

Atena não deve mais tratar o fluxo normal REC+P1 como “criar do zero a partir da fonte oficial”.

O modo principal de produção é `rewrite_from_reference_pair`:

```text
REC de referência -> descobrir P1 de referência -> extrair CTA final/oferta -> reconstrução editorial MGS -> novo REC+P1
```

Regras:

- o REC de referência é o ponto de entrada normal do fluxo;
- Atena deve ler o REC de referência, descobrir e ler a P1 de referência e extrair o CTA final/oferta da P1;
- o par REC+P1 de referência é a fonte editorial principal para entender benefícios, ordem lógica, contexto, argumentos e pontos de conversão;
- Atena deve reconstruir o conteúdo no modelo MGS, não parafrasear linha a linha;
- REC continua sendo resumo/chamada para continuar na P1;
- P1 continua sendo a página aprofundada que pode enviar para a oferta externa;
- URL oficial/oferta separada não é obrigatória no pedido normal quando o CTA final puder ser extraído da P1 de referência;
- não inventar benefícios, taxas, APR, bônus, elegibilidade ou condições;
- não preencher lacunas com suposição;
- não usar cache editorial como fonte de verdade;
- se dado essencial não estiver confirmado no REC/P1 de referência, pedido atual ou fonte confiável validada no momento, bloquear ou pedir dado corrigido;
- se o REC não levar a uma P1 clara, ou a P1 não tiver CTA final/oferta claro, bloquear e pedir a P1 de referência ou URL final de oferta;
- se o pedido trouxer duas ou mais URLs de referência, tratar a primeira URL compatível como REC de referência e a segunda URL compatível como P1 de referência/override quando o REC não apontar claramente para a P1; não pedir confirmação só por existir mais de uma referência.

Se a extração do par REC+P1 de referência for insuficiente, só usar fatos adicionais quando forem verificados no pedido atual ou em fonte confiável validada no momento.

---

