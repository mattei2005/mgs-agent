# Cost Monitoring — GPT OAuth (Sem Admin API)

## Contexto

Após migrar Zeus/Atena para GPT via OAuth ChatGPT:
- **Custo real:** $0 por token (incluído na assinatura $100/mês)
- **OpenAI não tem Admin API de usage** para OAuth/ChatGPT (só para API key regular)
- **Anthropic Admin API** (`api.anthropic.com/v1/usage`) não é mais relevante e não deve ser chamada sem autorização explícita de Rodolfo
- O Hermes não expõe tokens totais no `agent.log` — só `api_calls` e `response_chars`

## Abordagem de estimativa (implementada em 2026-05-15)

### Fonte de dados: `agent.log`

Formato relevante no log:
```
response ready: platform=discord chat=XXXX time=Xs api_calls=N response=Nchars
```

O campo `api_calls` é o proxy mais confiável disponível.

### Médias empíricas iniciais (a calibrar)

| Parâmetro | Valor inicial |
|---|---|
| Tokens de input por call | ~2.000 |
| Tokens de output por call | ~500 |
| Pricing input GPT-5.5 (hipotético) | $7,00/1M tokens |
| Pricing output GPT-5.5 (hipotético) | $21,00/1M tokens |

**⚠️ Pricing hipotético** — GPT-5.5 não tem preço oficial listado (acesso via OAuth). Os valores são referência interna de consumo, não custo real.

### Fórmula de estimativa

```bash
api_calls=$(grep "response ready:" /path/to/agent.log | grep -c ".")
tokens_input=$((api_calls * 2000))
tokens_output=$((api_calls * 500))
cost_input=$(echo "scale=4; $tokens_input / 1000000 * 7.00" | bc)
cost_output=$(echo "scale=4; $tokens_output / 1000000 * 21.00" | bc)
cost_total=$(echo "scale=4; $cost_input + $cost_output" | bc)
echo "api_calls=$api_calls | custo estimado=\$${cost_total} (hipotético) | custo real=\$0.00 (OAuth)"
```

## Scripts de monitoramento em produção

- `/root/mgs-agent/scripts/monitor-gpt55-oauth-cost.sh` — conta api_calls 24h Zeus + Atena e reporta custo real $0.00 / custo hipotético
- `/root/mgs-agent/scripts/track-article-cost.sh` — estima tokens por artigo, grava em article-tracker.db

## Calibração recomendada

Após ~10 artigos publicados com GPT:
1. Verificar `api_calls` real por artigo via agent.log
2. Comparar com tokens mostrados no resumo de sessão do Discord (se disponível)
3. Ajustar médias 2000/500 em `track-article-cost.sh` se necessário

## Campo `cost_calc_method` em article-tracker.db

Valores possíveis:
- `api_calls_estimated` — proxy via api_calls (método atual pós-migração)
- `anthropic_api` — chamada real à Anthropic Admin API (método pré-migração, obsoleto)
