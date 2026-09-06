# Contratos de pedidos naturais de campanha

## Princípio

O operador pode pedir campanhas em linguagem natural e omitir dados já resolvidos inequivocamente pelo canal/thread e pelo contrato ativo da operação. Não transformar o pedido em formulário obrigatório nem perguntar o que pode ser lido da rota canônica e do runtime.

## Resolução por contexto

- Dentro de um canal dedicado a uma única operação, um alias curto de conta pode bastar para resolver site, país, vertical, idioma, gestor e estratégia.
- Fora do canal operacional, ou quando duas operações compartilham o mesmo alias, exigir o identificador que elimine a ambiguidade.
- O contexto nunca autoriza inferir Page, `pg_XXXXX`, modo, budget ou outra variável que o contrato marque como obrigatória por request.
- Fazer readback do contrato e da conta antes de materializar o manifest; nome de canal é pista de roteamento, não prova de estado Meta.

## Campos mínimos do pedido

```text
Conta
Quantidade de campanhas
Tipo/vertical dos criativos
Origem dos criativos
Liberdade de seleção/ângulo
Modo de criação
Budget exato por campanha
Início com timezone
Status desejado
```

Rotular sempre `Quantidade de campanhas`; `Quantidade: N` é ambíguo com quantidade de criativos. Informar também criativos por campanha quando a operação aceitar mais de uma estrutura.

## Modo humano versus rota técnica

Preservar a intenção comercial sem falsificar a implementação:

- `campanhas novas com criativos novos` significa novos objetos e mídia nova para o operador;
- uma conta pode exigir linhagem técnica de anúncio ou shell copiado para servir corretamente;
- nesse caso, explicar uma vez que a lineage é implementação obrigatória, não duplicação de mídia/copy;
- se o pedido proibir literalmente qualquer clone e o contrato só suportar lineage/clone, isso é conflito real e requer decisão/arquitetura, não tradução silenciosa.

## Tráfego direto

Normalmente o pedido fecha com conta, quantidade, veículo/vertical, Drive, ângulos, modo, budget, horário no timezone da operação e status programado. Estrutura, evento, URL, Page/pixel, copy e UTM podem vir do contrato quando ele os declarar defaults vivos.

## ChatPion/Messenger

Além dos campos gerais, exigir:

- Facebook Page exata e `pg_XXXXX` quando a operação possui várias Pages;
- quantidade de criativos/anúncios por campanha quando o contrato aceita alternativas;
- pasta/vertical do Drive;
- `copy: padrão aprovado` ou os quatro campos Meta fornecidos;
- Messenger JSON/template padrão ou override explícito;
- horário no timezone da operação, que pode ser diferente do tráfego direto.

A criação literal do zero só é usada quando `supported_modes` e `ad_serving_route` da conta permitirem.

## Budget global

Sempre ler a política global de limites internos. Enquanto estiver inativa, o pedido não precisa declarar exceção de cap/pool: quantidade e budget explicitamente autorizados não são reduzidos. Ainda exigir budget exato, autoridade, pre-read/readback; billing, `account_spend_limit`, credenciais e automatic scaling mantêm gates próprios.

## Pitfalls

- Pedir site/país/idioma que a rota já resolve sem ambiguidade.
- Aceitar `Quantidade: N` sem determinar se são campanhas ou criativos.
- Confundir `copy` com imagem/vídeo.
- Omitir Page/`pg_XXXXX` em Messenger multi-Page.
- Reutilizar criativos quando o pedido diz novos e o saldo elegível é insuficiente.
- Aplicar o horário do tráfego direto a uma operação ChatPion.
- Tratar lineage técnica como autorização para duplicar mídia ou copy.
