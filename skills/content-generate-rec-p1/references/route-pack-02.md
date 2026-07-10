## Política contra cache editorial

Produção REC+P1 não deve usar cache editorial como fonte de conteúdo.

Não usar `data/card-cache.db` ou scripts `card-cache-*` como fonte de verdade para:

- benefícios;
- rewards;
- APR;
- annual fee;
- elegibilidade;
- descriptor/tag/headline;
- body copy;
- table copy;
- opening angle;
- URL oficial;
- imagem do card, salvo validação explícita no run atual.

Caches técnicos permitidos:

```text
data/sites.json             Configuração técnica de sites.
data/wp-term-cache.json     IDs de taxonomia WordPress.
data/rec-fingerprints.db    Histórico de similaridade/QA.
logs/audit                  Evidência operacional.
```

Se o runner/orchestrator indicar `card-cache`, `cache_hit` ou fallback sem URL oficial atual, reportar como blocker/migração. Não declarar produção limpa.

---

## Idioma de produção

O idioma do conteúdo publicado vem da configuração do site/vertical, especialmente `site.language` em `data/sites.json`.

Não usar `--lang` em produção normal.

`--lang` é somente para debug/dry-run quando Rodolfo pedir explicitamente teste de idioma. Para publicação, se o idioma solicitado conflitar com `site.language`, o runner/orchestrator deve abortar em vez de publicar conteúdo no idioma errado.

---

## Contracts ativos

Usar os contracts ativos como especificação editorial:

```text
cc-rec.md -> como o REC deve ser.
cc-p1.md  -> como a P1 deve ser.
```

O REC precisa ter ângulo próprio de atração e pré-conversão.

A P1 precisa aprofundar sem copiar o REC.

Se houver conflito entre reference antiga e contract ativo, o contract ativo vence.

As decisões e lições de cada incidente (reestruturação v2, tags por benefício, taxonomia WordPress, correções do teste Tesco, latência, formato de relatório e os quality gates do feedback da Raquel) ficam registradas em `references/`. Consulte a pasta quando precisar do detalhe histórico de uma decisão; nenhuma dessas notas é regra ativa por si — a regra ativa vive nos contracts, nos runners e nos validators.

---

## Fluxo operacional REC+P1

Ordem padrão:

```text
1. Ler pedido e confirmar que entrada mínima está completa.
2. Validar site/vertical/status/REC de referência.
3. Validar ou buscar imagem real do card.
4. Executar REC+P1 pelo orchestrator aprovado.
5. Validar links REC -> P1 e P1 -> oferta final extraída da referência.
6. Validar imagens, LazyBlocks e featured images.
7. Validar Yoast/readability/metadados.
8. Validar anti-repetição e qualidade editorial.
9. Renderizar relatório final auditável.
10. Responder com resumo final único.
```

O fluxo deve entregar os dois artigos juntos.

Não reportar sucesso parcial como sucesso total.

Se REC falhar, P1 não deve iniciar. Isso é segurança correta, não falha de planejamento.

---

## Entrypoint técnico padrão — REC+P1

Para REC+P1, usar o orchestrator aprovado como caminho normal:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-p1-orchestrator.py \
  --site <site_key_resolvido_em_sites_json> \
  --card "<exact card/product name>" \
  --status <draft|publish> \
  --reference-rec-url "<reference REC URL>" \
  [--card-image-url "<direct card image URL when supplied>"]
```

`<site_key_resolvido_em_sites_json>` deve ser a configuração específica do pedido, não necessariamente a chave base do domínio. Exemplo: para Eggbev + CAR + Brasil/PT-BR, usar `eggbev_car_br`.

`--reference-rec-url` é obrigatório no modo normal. O orchestrator deve descobrir a P1 de referência e extrair dela o CTA/oferta final. `--offer-url`/`--official-url` só deve ser usado como override quando a extração automática falhar ou for ambígua.

Não executar manualmente scripts de imagem, WordPress, Yoast ou publicação se o orchestrator ainda não falhou.

Se o orchestrator falhar, investigar o ponto específico da falha e não reinventar o pipeline inteiro.

Se o estado real dos runners/scripts ainda não cumprir algum ponto desta SKILL, reportar como pendência técnica de migração. Não inventar que o sistema faz algo que ainda não faz.

Exemplo: se o runner confirma media IDs/URLs diferentes, mas ainda não valida diferença visual automaticamente, reportar “media IDs/URLs diferentes confirmados; validação visual automática ainda é pendência técnica”.

---

## Exceções: REC isolado ou P1 isolado

REC isolado e P1 isolado são exceções operacionais, não o produto normal.

Usar REC isolado quando Rodolfo/Raquel pedir explicitamente:

- reparar REC existente;
- auditar REC;
- criar somente REC para teste;
- continuar operação onde P1 será feita depois por decisão explícita.

Formato técnico:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status <draft|publish> \
  --source-url "<official issuer URL>" \
  [--card-image-url "<direct card image URL when supplied>"]
```

Usar P1 isolado quando Rodolfo/Raquel pedir explicitamente:

- reparar P1 existente;
- auditar P1;
- criar P1 ligada a um REC já existente;
- continuar operação onde REC já foi publicado/criado antes.

Formato técnico:

```bash
python3 /root/mgs-agent/scripts/mgs-p1-runner.py \
  --site <site_key> \
  --rec-url "<published or draft REC URL when applicable>" \
  --official-url "<official issuer URL>" \
  --status <draft|publish>
```

Se o pedido não disser explicitamente REC isolado ou P1 isolado, voltar ao produto normal: REC+P1.

---

## Imagem do card

Quando Rodolfo/Raquel enviar imagem do card, essa imagem é a fonte principal.

Atena não deve substituir silenciosamente por outra imagem sem motivo claro.

A imagem enviada pode vir:

- vertical;
- com borda;
- com fundo;
- dentro de banner/canvas;
- com desenho/headline ao redor;
- em baixa qualidade.

O fluxo correto é:

```text
1. Identificar o cartão real dentro da imagem.
2. Remover fundo/canvas/borda/headline/desenho que não faça parte do card.
3. Recortar apenas o cartão.
4. Normalizar apresentação.
5. Girar/preparar horizontal quando necessário para LazyBlock.
6. Melhorar qualidade quando possível.
7. Validar identidade, legibilidade e aparência final.
8. Usar o card final no LazyBlock do REC.
9. Reutilizar o mesmo card final no LazyBlock da P1.
```

Bloquear se o resultado final ficar:

- falso;
- ilegível;
- cortado;
- distorcido;
- com branding errado;
- pixelado demais;
- visualmente ruim;
- incompatível com o cartão pedido.

Se o usuário forneceu uma imagem e ela falhou, não usar fallback automático silencioso para publicação. Pedir imagem corrigida ou autorização explícita para usar outra fonte.

Para draft técnico, fallback de imagem pode ser usado somente se o pedido for explicitamente teste/dry-run e o relatório marcar a imagem como fallback não aprovado para publish.

---

## Featured images

REC e P1 não podem terminar com a mesma featured image.

```text
Featured REC -> imagem contextual própria do REC.
Featured P1  -> imagem contextual própria da P1, diferente da REC.
Imagem interna P1 -> pode reutilizar a featured da P1 após a primeira frase inicial/subtítulo.
Card isolado -> ativo separado do LazyBlock REC/P1; pode ser referência/base visual, mas não é a featured final.
```

Antes de reportar sucesso em REC+P1, validar:

- featured REC e P1 têm URLs/media IDs diferentes;
- visualmente não são a mesma imagem, quando houver validator ou inspeção disponível;
- card exibido, quando houver, preserva identidade real;
- imagem interna da P1 está correta.

A composição visual detalhada de featured images deve viver em contract/reference próprio, não dentro desta SKILL principal. Esta SKILL só define o gate operacional: identidade real, qualidade visual, diferença entre REC/P1 e validação antes do sucesso.

---

