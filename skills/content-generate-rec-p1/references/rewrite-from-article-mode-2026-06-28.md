# REC+P1 rewrite_from_reference_pair mode — 2026-06-28

Contexto: Rodolfo decidiu que a Atena não deve mais operar o fluxo normal REC+P1 como criação do zero a partir da fonte oficial. Após refinamento, o modo principal passa a usar o REC de referência como entrada: Atena/orchestrator lê o REC, descobre a P1 de referência, extrai dela o link final de oferta e reconstrói o novo REC+P1 no modelo MGS.

## Decisão operacional

Fluxo normal:

```text
reference REC URL -> descobrir reference P1 URL -> extrair final offer URL -> extrair fatos/estrutura/ângulo -> reconstruir no modelo MGS -> validar similaridade -> REC+P1
```

A URL oficial/oferta separada não é obrigatória no pedido normal quando o CTA final puder ser extraído da P1 de referência. Ela continua existindo apenas como override ou apoio quando necessário para:

- CTA externo da P1 quando a extração automática falhar/for ambígua;
- validação de claims sensíveis quando disponível;
- bloqueio de URL/produto inconsistente.

A fonte editorial principal é o par REC+P1 de referência, não a página oficial.

## Regras de rewrite

Atena deve:

- preservar fatos, benefícios e contexto útil do REC/P1 de referência;
- reescrever no modelo dos contracts `cc-rec.md` e `cc-p1.md`;
- mudar abertura, ordem de argumentos quando fizer sentido, exemplos, transições e fraseado;
- evitar a mesma sequência de parágrafos;
- nunca fazer spin/paráfrase linha a linha;
- bloquear se houver cópia longa de texto das referências.

## Implementação atualizada

Arquivos alterados:

- `profiles/atena-soul.md`
- `skills/content-generate-rec-p1/SKILL.md`
- `skills/content-generate-rec-p1/contracts/cc-rec.md`
- `skills/content-generate-rec-p1/contracts/cc-p1.md`
- `scripts/mgs-rec-p1-orchestrator.py`
- `scripts/mgs-rec-runner.py`
- `scripts/mgs-p1-runner.py`

Mudanças técnicas:

- `mgs-rec-p1-orchestrator.py` agora aceita `--reference-rec-url` como entrada normal.
- O orchestrator descobre a P1 de referência a partir dos links internos do REC.
- O orchestrator extrai o link final de oferta/CTA externo da P1 de referência.
- `--official-url`/`--offer-url` fica como override quando a extração automática falhar ou for ambígua.
- O REC runner recebe o REC de referência como `--article-url` interno para reescrita.
- O P1 runner recebe a P1 de referência como `--article-url` interno para extração de facts.
- REC/P1 runners tratam a URL final de oferta como CTA, não como fonte oficial obrigatória de conteúdo.
- Gate simples de anti-plágio do REC bloqueia longos trechos contíguos copiados (`longest_common_word_run >= 18`).

## Pendências técnicas assumidas

- P1 já consome facts da P1 de referência, mas o corpo ainda é montado pelo gerador Python determinístico; precisa de fase seguinte para `p1_body_mode=llm/rewrite_from_reference_pair` equivalente ao REC.
- O gate de similaridade atual é contíguo/fraseológico; ainda não mede similaridade semântica nem estrutura global.
- A descoberta automática de P1/CTA é heurística; se não houver link claro, o fluxo deve bloquear e pedir P1 de referência ou URL final de oferta.

## Validação mínima esperada

- `python3 -m py_compile` nos scripts alterados.
- `--help` do orchestrator confirmando `--reference-rec-url` e `--offer-url`.
- chamada normal sem `--reference-rec-url` deve bloquear antes de execução.
- teste ad-hoc de descoberta com HTML local deve confirmar: REC referência -> P1 referência -> CTA final.
