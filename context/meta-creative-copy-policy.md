# Meta Ads — política de recursos nas cópias

Status: ativa. Dono executivo: Rodolfo Mattei. Executor: Ares / Campaign Ops. Governança: Zeus.

## Regra permanente: geração de fundo de imagem desativada

Decisão de Rodolfo, mensagem `1568722979569930414`, thread `1568669160798683260`, em 2026-11-07: em qualquer campanha Meta cuja duplicação autorizada herdaria **Geração de plano de fundo da imagem** (`degrees_of_freedom_spec.creative_features_spec.image_background_gen`) habilitada, criar a cópia com **somente esse recurso desativado** (`enroll_status=OPT_OUT`). Não pedir uma nova autorização por ocorrência e não aguardar uma rejeição de catálogo para aplicar a regra.

A regra vale para as duplicações autorizadas operadas pelo Ares, independentemente de conta, vertical, gestor, presença de catálogo ou rota de cópia. Não concede acesso a novos ativos e não autoriza duplicação sem o pedido humano correspondente.

## Invariantes

- Não alterar a campanha, os anúncios ou os creatives de origem; a mudança existe apenas na cópia.
- Preservar mídia, copy, headline, CTA, identidade, conjunto de assets e todos os demais recursos/enrollments. A exceção é exclusivamente `image_background_gen`; não desligar conjuntos de aprimoramentos, substituir por defaults ou omitir outros recursos.
- Se o recurso já estiver desativado, mantê-lo; não inventar configuração quando ausente.
- Preservar a localização aprovada do tracking: para os pedidos Kelly em recuperação, UTMs novas ficam diretamente na Website URL, nunca como substituição em `url_tags` / Parâmetros de URL.
- Preservar IDs, quantidade, numeração/idempotência, orçamento, lance, início, estratégia e demais condições do pedido original. Reaproveitar estruturas incompletas; criar apenas o saldo ainda não materializado do mesmo pedido.
- Fazer pre-read, jornal durável e QA/readback antes de ativar; depois da ativação, confirmar o estado real. Provar que a cópia tem o recurso desativado e mantém os demais parâmetros e recursos.
- Na reconstrução ou cópia nativa, aplicar a mesma transformação explícita ao payload efetivo e à expectativa de QA. Uma referência imutável a um creative ainda habilitado não cumpre a regra. Preservar os manifests selados anteriores como evidência, vinculando a resolução efetiva à decisão e ao checkpoint; não falsificar seals.
- A política não autoriza catálogo novo, remoção de outros recursos, mudanças de credenciais/permissões/billing ou exclusão de objetos.

## Supersessão e recuperação imediata

Esta decisão substitui a exigência anterior de preservar `image_background_gen=OPT_IN` e as esperas por autorização individual **somente para esse recurso nas cópias**. As regras de preservação dos demais recursos e de autorização dos pedidos continuam vigentes. Os controles manuais e as tentativas API anteriores permanecem evidência histórica, não pré-requisitos para continuar os pedidos.

Rodolfo também determinou concluir os mesmos pedidos Kelly:

- Mavroa: `shein-1568649228383686737`, conta `1829406761389732`, cinco cópias da C031, US$100/dia por campanha, COST_CAP US$0,78, início imediato original. C033/C034 existentes devem ser reaproveitadas.
- Yolo: `shein-1568649923107225623`, conta `2429758060563333`, cinco cópias da C242, US$150/dia por campanha, COST_CAP US$0,68, início imediato original. C243/C244 existentes devem ser reaproveitadas.

As sessões Ares de cada thread de origem já retomaram com autorização direta de Rodolfo. Não abrir outra execução nem transportar ownership de uma conta para a outra. Alterações em código compartilhado exigem um único escritor coordenado; os writes de campanha continuam isolados por conta e pelos locks canônicos.

## Implementação e evidência

A política aprovada não equivale a implantação: o executor precisa aplicar a resolução nos caminhos centrais de construção, retomada, materialização e QA e exercitar testes negativos/de preservação. Cada pedido só está concluído após readback da quantidade integral, URLs, recursos e estado final aprovado e entrega na origem. O checkpoint Zeus `zeus-shein-background-1568656839132971009` acompanha a conclusão, sem writer Meta paralelo.
