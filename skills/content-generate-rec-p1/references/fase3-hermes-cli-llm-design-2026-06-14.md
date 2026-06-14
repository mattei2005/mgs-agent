# Fase 3 — Hermes CLI one-shot para geração editorial LLM

Contexto: após a Fase 2, REC e P1 ficaram com uma única autoridade editorial (`contracts/cc-rec.md` e `contracts/cc-p1.md`), mas o corpo dos artigos ainda é gerado por Python determinístico (`generate_article_local` no REC e `generate_p1_body` no P1). Isso limita variação e foi identificado como causa raiz dos conteúdos repetidos.

## Estado confirmado

- REC: `scripts/mgs-rec-runner.py::generate_article_local(...)` monta blocos Gutenberg com frases fixas e retorna `generator: local_deterministic_rec_contract_v2`, `cost_usd: 0.0`.
- P1: `scripts/mgs-p1-runner.py::generate_p1_body(...)` usa `p1_static(...)` e policy explícita `article_generation: deterministic_python`, `llm_runtime: disabled`.
- `load_anthropic_key()` é stub intencional e retorna `None`; Anthropic/Claude API pago continua desativado.
- Não existe cliente GPT/Codex dentro dos runners. O caminho disponível no runtime é Hermes CLI one-shot com perfil Atena.

## Probe Hermes CLI validado

Comando testado:

```bash
/root/.local/bin/hermes -p atena -z "Responda apenas: teste ok"
```

Resultado bruto:

```text
RC=0
DURATION_SEC=4.43
---RAW_OUTPUT_START---
teste ok
---RAW_OUTPUT_END---
```

Conclusão: stdout veio limpo, sem banner/log; o perfil `atena` usa `openai-codex` + `gpt-5.5` em `/root/.hermes/profiles/atena/config.yaml`, com auth Codex sincronizado pelo fluxo `sync-codex-oauth.sh`.

## Recomendação de integração — Opção A+

Usar Hermes CLI one-shot primeiro, em vez de construir cliente Codex OAuth novo. Mas não chamar o CLI de forma solta; usar contrato rígido de saída:

1. `subprocess.run(["/root/.local/bin/hermes", "-p", "atena", "-z", prompt], text=True, capture_output=True, timeout=180)`; nunca `shell=True`.
2. Prompt deve exigir marcadores fixos, por exemplo:
   - `<<<MGS_ARTICLE_HTML_START>>>`
   - `<<<MGS_ARTICLE_HTML_END>>>`
3. Parser aceita somente conteúdo entre marcadores. Se não houver marcadores, falha/regenera uma vez.
4. Máximo: 1 geração + 1 regeneração por artigo. Sem loop ReAct, sem patching ao vivo.
5. Registrar telemetria no JSON: `body_generation.mode`, `provider=hermes-cli`, `profile=atena`, `model=gpt-5.5/openai-codex`, `prompt_chars`, `duration_sec`, `rc`, `regeneration_count`, `fallback_reason`.
6. Medir `prompt_chars` e impor hard gate conservador (ex.: <= 90k chars) por limite prático de argumento Linux e controle de contexto.
7. Manter fatos oficiais fora do modelo: fee/APR/benefícios vêm do fluxo atual; o LLM só escreve narrativa a partir de fatos confirmados.
8. Todos os gates atuais continuam depois da geração: word count, LazyBlocks, Yoast, title/meta/focus, no-cache, fingerprint/anti-repetição e renderer.

## Fallback determinístico

Fallback determinístico é aceitável para draft/teste, marcado explicitamente no relatório. Para `publish`, não publicar fallback determinístico por padrão: bloquear salvo flag explícita (`--allow-deterministic-fallback-publish` ou equivalente). Motivo: publicar fallback reintroduz a causa raiz dos repetidos que a Fase 3 busca corrigir.

## Pontos de encaixe prováveis

- REC: encapsular/substituir `generate_article_local(...)` por modo LLM (`--rec-body-mode {llm,deterministic}`), preservando determinístico para fallback/debug.
- P1: encapsular/substituir `generate_p1_body(...)` por modo LLM (`--p1-body-mode {llm,deterministic}`), com contexto do REC para aprofundar sem repetir.
- Orchestrator: repassar flags nos pacotes posteriores; não precisa redesenhar o pipeline inteiro.
