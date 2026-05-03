# Anthropic Pricing — Single Source of Truth

**IMPORTANTE:** Esses valores estão duplicados em 3 lugares por necessidade técnica
(Python script, bash script, SKILL.md). Se Anthropic mudar pricing, atualizar nos 3.

## Pricing oficial (USD por milhão de tokens)

### Claude Sonnet 4.6 (modelo principal Atena)
| Tipo | Preço (USD/MTok) |
|---|---|
| Input (no cache) | $3.00 |
| Output | $15.00 |
| Cache write 5min | $3.75 |
| Cache write 1h | $6.00 |
| Cache read | $0.30 |

### Claude Haiku 4.5 (auxiliary tasks)
| Tipo | Preço (USD/MTok) |
|---|---|
| Input | $1.00 |
| Output | $5.00 |
| Cache write 5min | $1.25 |
| Cache read | $0.10 |

## Onde os valores estão definidos (3 lugares)

### Local 1: api/generate-rec-api.py (linhas 93-96)
```python
PRICE_INPUT = 3.00
PRICE_OUTPUT = 15.00
PRICE_CACHE_READ = 0.30
PRICE_CACHE_WRITE = 3.75
```

### Local 2: scripts/track-article-cost.sh (linhas 30-33)
```bash
PRICE_UNCACHED=3.00
PRICE_CACHE_5M=3.75
PRICE_CACHE_READ=0.30
PRICE_OUTPUT=15.00
```

### Local 3: skills/content-generate-rec/SKILL.md (Step 14, linha ~720)
```python
atena_cost = (i*3.00 + o*15.00 + cr*0.30 + cw*3.75) / 1_000_000
```

## Procedure: como atualizar quando Anthropic mudar pricing

1. Atualizar este arquivo primeiro
2. Atualizar os 3 lugares listados acima
3. Commit com mensagem: `update(pricing): Sonnet 4.X new prices`
4. Validar: rodar 1 REC, checar Step 14 cost reporting

## Histórico

- 2026-05-02: arquivo criado durante P1-5 fix
- Pricing Sonnet 4.6 confirmado válido em 02/05/2026
