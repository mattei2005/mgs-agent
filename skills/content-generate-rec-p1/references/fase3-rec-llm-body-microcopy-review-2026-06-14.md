# Fase 3 — revisão de pacotes LLM REC: corpo, microcopy e telemetria

Contexto: durante o desenho/aplicação planejada da Fase 3, Rodolfo decidiu que o problema estrutural da Atena era texto determinístico em Python. A direção final é GPT-5.5 escrever textos; Python vira guarda-corpo de fatos/schema/validação.

## Direção final

- GPT escreve texto criativo/editorial: corpo REC/P1 e, em subfase própria, microcopy textual do LazyBlock (`tag10`, `tag2`, `descriptor`).
- Python continua dono de fatos e operação: URL, imagem, IDs WordPress, schema LazyBlock, nomes de campos, status, APR/fee/prazos/benefícios confirmados.
- Sem fallback automático para determinístico em nenhum status. Falha LLM → 1 regeneração → bloqueia. Determinístico só por flag explícita de debug/reversão.

## Faseamento recomendado

- 3.2A: corpo editorial REC via GPT dentro de `mgs-rec-runner.py`; microcopy do LazyBlock ainda temporariamente derivada em Python.
- 3.2B: microcopy LazyBlock via GPT, com validador strict novo.
- Separar 3.2A/3.2B porque a microcopy exige validator próprio; não misturar risco de integração do corpo com risco de validação de claims curtos.

## Guardrail negativo, não catálogo de permitidos

Não criar catálogo de tags permitidas por categoria. Isso recria templates/repetição.

Validação da microcopy deve ser negativa e objetiva:

- schema correto e campos não vazios;
- `tag10`/`tag2` <= 25 chars; `descriptor` <= 70 chars;
- números, fees, APR, prazos e percentuais precisam existir no facts pack;
- benefício comercial ausente nos fatos confirmados → rejeitar;
- lista pequena de claims proibidas/compliance (ex.: `best`, `top`, `#1`, `guaranteed`, `approved`, `instant approval`, `debt relief`, `rebuild your finances`, `bad with money`, `impulsive spender`);
- sem fallback silencioso e sem truncamento silencioso.

Facts pack atual do REC deve vir de `card_data`: `card_name`, `annual_fee`, `apr`, `benefits`, `card_official_url`. O runner ainda não tem campo estruturado separado para números/prazos/taxas.

## `card_ui_tag` não é validator strict

`card_ui_tag` atual é útil como referência, mas não pode validar microcopy GPT sozinho porque:

- faz fallback silencioso (`if bad: value = fallback`);
- corta silenciosamente (`value[:25]`).

Para GPT, `bad` ou `len > limite` deve virar rejeição com reason, não fallback/corte. Reutilizar apenas normalização, `is_generic_visible_value`, regex de número solto e lista de genéricos, sem os comportamentos de fallback/truncamento.

## Revisão de pacote 3.2A — pitfall crítico

Ao revisar pacote que insere `generate_rec_body_llm`, confirmar que o retorno `api` propaga telemetria para o JSON final do runner.

Pitfall encontrado em proposta de script: a função nova retornava `body_generation` e `generator`, mas o `main` só fazia:

```python
costs["article_api"] = float(api.get("cost_usd") or 0)
card_data.update(api.get("card_data") or {})
```

Sem alteração do `result` final, `body_generation` morre dentro de `api` e a auditoria obrigatória desaparece. Antes de aplicar, exigir no JSON final:

```python
"generator": api.get("generator"),
"body_generation": api.get("body_generation") or { ... deterministic/debug object ... },
```

Opcional recomendado para validação dos dois corpos: em dry-run, salvar o `article_html` puro em `/tmp/rec-body-<card_slug>.html` ou expor `article_body_preview`/`article_body_chars`, para comparar corpo GPT sem misturar LazyBlock/botão.

## Testes esperados para 3.2A

- `py_compile` do runner alterado.
- grep/contagem: uma definição de cada helper/função nova e uma chamada LLM + uma deterministic.
- dry-run modo LLM com cartão real.
- dry-run modo deterministic para garantir reversão explícita.
- dois cartões da mesma categoria em modo LLM: comparar **corpos** diferentes. Microcopy diferente só é teste do 3.2B.

## Estilo de revisão com Claude

Quando Claude enviar pacote/desenho, revisar contra VPS real, não contra cópia externa. Separar hits históricos de contradição ativa. Se o design/script não propagar telemetria ou criar autoridade paralela, bloquear antes de aplicar.