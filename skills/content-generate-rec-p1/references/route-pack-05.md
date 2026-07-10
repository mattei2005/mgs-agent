## Estado de refactor

Esta SKILL assume a arquitetura limpa da Atena:

```text
Produto normal                  REC+P1 como uma única solicitação.
SOUL                            Identidade, postura, governança e escopo.
SKILL                           Operação REC+P1.
Contracts                       Estrutura editorial de REC e P1.
Runners/orchestrator            Execução e validações determinísticas.
References/archive              Histórico, não regra ativa por padrão.
```

Se o estado real dos runners/scripts ainda não cumprir algum ponto desta SKILL, reportar como pendência técnica de migração. Não inventar que o sistema faz algo que ainda não faz.

### REC runner: `cc-rec.md` como hard requirement

No `scripts/mgs-rec-runner.py`, `load_rec_template_contract` deve usar `skills/content-generate-rec-p1/contracts/cc-rec.md` como contract universal obrigatório (`template_key=cc-universal`). Não reintroduzir fallback para `templates/rec-{template_key}.md`: se `cc-rec.md` faltar, o runner deve falhar com `RunnerError` claro e auditável. Detalhe e checklist de validação: `references/rec-runner-template-fallback-removal-2026-06-13.md`.

### Aplicação e revisão de pacotes de migração REC+P1

Quando Rodolfo enviar pacote/script de refactor da Atena para REC+P1 — especialmente quando vier de outro LLM/Claude — tratar como mudança auditável e **revisar o mérito**, não só executar as travas.

Fluxo obrigatório:

1. Revisar o script e o arquivo editado/staging antes de rodar.
2. Registrar `git status`, HEAD/origin/remote e hashes dos alvos antes.
3. Confirmar que o pacote faz sentido contra a arquitetura atual: contracts universais `cc-rec.md`/`cc-p1.md`, sem `sites.json.template_key`, sem templates legados ativos e sem cache editorial como fonte.
4. Para pacotes Fase 3 que alteram REC LLM no `mgs-rec-runner.py`, revisar também `references/fase3-rec-llm-runner-lessons-2026-06-14.md` antes de aplicar: telemetria precisa chegar ao JSON final, falhas devem manter `body_generation` plano, prompts devem respeitar `validate-article.sh`, e default-path change deve ser revertido se smoke real falhar.
5. Rodar exatamente com as travas quando estiver coerente.
5. Validar independentemente depois: hashes, grep pós-mudança, smoke tests, presença/ausência de arquivos, JSON parseável e diff esperado.
6. Usar grep **amplo e semântico** para resíduos documentais, não só os padrões do script. Exemplo para AGENT.md/routing: `template_key|templates/rec|templates/p1|rec-gb-cc-en|gb-cc-en|4 mandatory pauses|verified cache|rec_create|list_templates`.
7. Quando o pacote vier de Claude/outro LLM com arquivos copiados fora da VPS, tratar a cópia externa como potencialmente stale: gerar/usar tar + SHA do estado real, validar contra a SKILL ativa e references reais, e não aceitar “grep zero” externo sem confirmação local. Se surgir design/reference paralelo, marcar como `superseded` ou consolidar antes de codar.
8. Committar somente o diff esperado; se auto-commit capturar staging/artefato temporário, remover em commit corretivo sem reescrever histórico remoto.
9. Separar dirty state preexistente no report final.
10. Se sobrar resíduo documental que possa confundir Atena/Claude, pausar e recomendar micro-pacote corretivo antes de declarar a fase “100% fechada”.

Para o padrão completo validado na Fase 2 e as lições dos Pacotes 4/4.1/3.0.1, ver `references/fase2-migration-package-ops-2026-06-14.md` e `references/fase3-hermes-cli-llm-design-2026-06-14.md`.

### Fase 3: geração editorial via GPT-5.5/Codex OAuth

A Fase 3 deve tratar a geração do corpo dos artigos como mudança arquitetural auditável: REC e P1 ainda têm geradores Python determinísticos (`generate_article_local` e `generate_p1_body`) que causam baixa variação entre cartões da mesma categoria. O caminho preferido inicialmente é Hermes CLI one-shot com perfil `atena` (`openai-codex`/`gpt-5.5`), não cliente Codex OAuth novo, desde que o pacote implemente parser rígido, timeout, telemetria e gates pós-geração.

Regras para revisar/aplicar pacote de Fase 3:

1. Usar CLI como lista de argumentos, nunca `shell=True`: `/root/.local/bin/hermes -p atena -z <prompt>`.
2. Exigir marcadores fixos de saída e aceitar somente HTML dentro dos marcadores; sem marcador = falha/regeneração única.
3. Máximo de 1 geração + 1 regeneração por artigo; sem loop ReAct ou patching ao vivo.
4. Registrar no JSON: modo, provider/profile/model, `prompt_chars`, duração, rc, regenerações e fallback.
5. Fatos oficiais continuam vindo do fluxo determinístico atual; o modelo só transforma fatos confirmados em narrativa.
6. Manter todos os gates atuais depois do LLM: word count, LazyBlocks, Yoast, title/meta/focus, no-cache, fingerprint/anti-repetição e renderer.
7. **Sem fallback automático em nenhum status.** Draft e publish usam a mesma lógica. Default = LLM. Se o LLM falhar (rc!=0, timeout, sem marcador, gate reprovado): 1 regeneração; se falhar de novo, **bloqueia** (não publica, não cai em determinístico). O gerador determinístico só roda com flag explícita de debug/reversão (`--rec-body-mode deterministic` / `--p1-body-mode deterministic`), nunca como fallback automático.
8. **Gates reais antes de aplicar runner LLM:** validar prompt e smoke contra `skills/content-generate-rec-p1/scripts/validate-article.sh` (não `content-publish-wordpress`) e `scripts/qa-content-validator.py`. Subtitle/excerpt é o primeiro `<p>`; a intro antes do primeiro `<h2>` conta como seção; `validate_no_review` bloqueia a palavra `review`. Para balance transfer, o prompt deve ser **benefit-led**: identificar o benefício primário e explicá-lo com termos financeiros exatos (`balance transfer`, `0% interest`/`interest-free`, `months`, `existing card debt`/`repayments`/`interest pressure`) em vez de keyword stuffing. Ao revisar pacote externo, aplicar temporariamente com SHA/backup/py_compile/contagens, rodar dry-run real e reverter se qualquer gate falhar. Detalhes/checklist: `references/fase3-rec-llm-runner-gates-2026-06-14.md`.
9. Em smoke temporário de pacote, cuidado com scripts que fazem `git add`: o repo MGS pode auto-commitar/auto-pushar. Preferir simulação fora do repo ou neutralizar staging até Rodolfo aprovar deixar aplicado; se a automação já comitou um diff tecnicamente aprovado, reportar o commit e não reescrever histórico remoto sem ordem explícita.
10. Controlar tamanho do prompt (hard gate conservador, ex.: <= 90k chars) porque o CLI recebe `-z` como argumento e há limite prático de argv.

Detalhes do probe validado, riscos e pontos de encaixe: `references/fase3-hermes-cli-llm-design-2026-06-14.md`.

Lições operacionais adicionais da revisão Rodolfo/Claude/Zeus para Fase 3 (3.0.1, 3.1 e desenho 3.2): `references/fase3-rec-llm-integration-lessons-2026-06-14.md`. Use essa referência ao revisar pacotes que introduzem GPT-5.5 no REC runner, especialmente para: validação contra VPS real, regra final sem fallback automático, parser/telemetria do Hermes CLI, decisão de não paralelizar inicialmente, preservação temporária de `tag10`/`tag2`/`descriptor` no 3.2A, e cuidado com retry de gates pós-geração.

Complemento obrigatório para pacotes REC LLM 3.2A/3.2B: `references/fase3-rec-llm-body-microcopy-review-2026-06-14.md`. Ao revisar scripts de Claude/outro LLM, verificar especialmente: (1) GPT escreve textos e Python atua como guarda-corpo negativo, sem catálogo de termos permitidos; (2) 3.2A e 3.2B ficam separados — corpo primeiro, microcopy depois; (3) `card_ui_tag` não é validator strict para microcopy GPT porque faz fallback/truncamento silencioso; (4) `body_generation` e `generator` retornados por `api` precisam ser propagados para o JSON final do runner antes de aplicar; (5) no teste 3.2A, comparar corpos diferentes, não microcopy; (6) no 3.2B, `lazy_credit_card` em modo LLM deve usar microcopy validada direto, sem wrappers/re-derivação, e o validator strict deve bloquear benefício comercial ausente dos facts (travel/cashback/rewards/points etc.).
