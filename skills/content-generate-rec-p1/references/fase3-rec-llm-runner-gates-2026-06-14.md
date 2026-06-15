# Fase 3 REC LLM runner — gates reais e lições do Pacote 3.2A

Data: 2026-06-14
Escopo: integração do corpo REC via GPT-5.5/Hermes CLI no `scripts/mgs-rec-runner.py`.

## Regra operacional que saiu da sessão

Ao revisar pacote/script vindo de Claude/outro agente, não assumir que o arquivo usado por ele está atual. Fazer sempre:

1. validar SHA do arquivo-alvo na VPS;
2. revisar o patch contra o runtime real;
3. aplicar temporariamente só com backup/trava/py_compile/contagens;
4. rodar smoke real;
5. se o smoke falhar em gate, reverter antes de responder;
6. reportar números do gate, corpo/artefatos gerados e estado final do repo.

## Travas boas para pacote de runner REC

- `sha256sum scripts/mgs-rec-runner.py` antes de tocar.
- Backup datado em `backups/fase3-pacote...`.
- `python3 -m py_compile` antes e depois.
- `grep -c` de funções e chamadas inseridas; py_compile não detecta duplicidade lógica.
- Secret scan no arquivo resultante.
- Auto-revert se compile final falhar.
- Se dry-run falhar, reverter o runner para o backup/SHA original antes de finalizar.

## Telemetria LLM não pode morrer no payload interno

Se `generate_rec_body_llm()` retorna `body_generation`, o `main()` precisa propagar no JSON final:

- `generator`
- `body_generation`
- `article_body_chars`
- `article_body_preview`
- preferencialmente `article_body_file` em dry-run

Para falhas, usar `telemetry_sink` plano:

```python
telemetry_sink.clear()
telemetry_sink.update(body_generation)
```

Evitar `telemetry_sink["body_generation"] = body_generation`, porque cria JSON aninhado (`body_generation.body_generation...`).

## Gates reais do `validate-article.sh`

Arquivo real usado pelo REC runner:

```text
skills/content-generate-rec-p1/scripts/validate-article.sh
```

Não confundir com `skills/content-publish-wordpress/scripts/validate-article.sh` — esse caminho não existia nesta sessão.

SHAs na sessão:

```text
3f9fd136bf598a6dbd8a9127ac63476fe62f1288aee8398ba5892803bfa1b493  skills/content-generate-rec-p1/scripts/validate-article.sh
5726758e056c068ec2398d5b1586c771226bf980e2b426f8116db607a845b575  scripts/qa-content-validator.py
```

Gates exatos:

```text
word count visível: 450–500
subtitle/excerpt: primeiro <p>, <=100 caracteres
avg_paragraph_words: <=30
max_paragraph_words: <=30
max_section_paragraphs: <=4
long_sentence_ratio: <=0.20
```

Detalhes importantes:

- O subtitle é o primeiro `<p>` visível após remover LazyBlocks.
- A seção `intro` antes do primeiro `<h2>` também entra em `max_section_paragraphs`.
- Parágrafos vêm de `<p>` (e listas entram no word count; o style parser da sessão olhava `<h2>` e `<p>`).
- Frases são divididas por `. ! ?`.
- Palavras contam como tokens com letra/número.

Prompt seguro para REC LLM deve dizer:

- primeiro elemento = `<p>` com 85–95 caracteres;
- exatamente 2 parágrafos antes do primeiro `<h2>`;
- cada parágrafo com 18–26 palavras, nunca >30;
- nenhuma seção, incluindo intro, com >4 parágrafos;
- mirar 465–490 palavras para evitar depender de padding;
- manter frases majoritariamente <=18 palavras.

## Gate separado: `review`

Além do `validate-article.sh`, o runner chama:

```python
validate_no_review({"body": content, "subtitle": visible_subtitle(content)})
```

Isso bloqueia a palavra exata `review` em body/subtitle. O prompt LLM deve proibir `review` em qualquer lugar e sugerir alternativas: `check`, `compare`, `look at`, `read`, `consider`.

## Lições dos dry-runs NatWest e Tesco

- v3/v4 provaram que Hermes CLI + parser + telemetria funcionavam, mas o prompt não conhecia todos os gates.
- v4 passou word/subtitle/paragraph/long-ratio, mas falhou porque a intro teve 5 parágrafos; o validador conta intro como seção.
- v5 passou a estrutura no final montado, mas falhou no hard gate `review`.
- v6/v7 passaram `validate-article.sh` e `review`, mas falharam no `qa-content-validator.py` em `weak_rec_top_keywords` quando o prompt tratava a abertura como cobertura de keywords.
- A correção que fechou NatWest foi **benefit-led opening**, não keyword stuffing: instruir o modelo a identificar o benefício primário do cartão e abrir explicando esse benefício com os termos financeiros exatos do produto.
- Quando o LLM passa parser mas falha gate, não deixar o default `llm` aplicado no runner; reverter e reportar.

## Gates relevantes do `qa-content-validator.py` para REC LLM

Além dos gates estruturais e de `review`, o REC passa por QA semântico em `scripts/qa-content-validator.py`. Em balance transfer, o gate `weak_rec_top_keywords` olha as primeiras 4 sentenças visíveis e exige intenção comercial + dor do usuário:

```python
REC_BALANCE_TRANSFER_TOP_KEYWORDS = [
    "balance transfer", "0 interest", "interest free", "months",
    "existing card debt", "repayments", "interest pressure",
]
has_offer = any(k in hits for k in ["balance transfer", "0 interest", "interest free", "months"])
has_pain = any(k in hits for k in ["existing card debt", "repayments", "interest pressure"])
if len(hits) < 4 or not (has_offer and has_pain): BLOCK
```

Prompt robusto não deve dizer apenas “insira keywords”. Deve dizer:

```text
First identify the card's primary benefit from confirmed facts.
Open by explaining that benefit concretely.
For balance transfer, the benefit is helping with existing card debt / repayments during a 0% interest or interest-free period measured in months.
Use material terms exactly: "0% interest" or "interest-free", not vague "0% offer".
Keep rewards/Clubcard secondary when balance transfer is the primary benefit.
```

Essa formulação fez NatWest passar `success:true` e, com facts oficiais explícitos, Tesco também passar. Evitar frases fracas bloqueadas por `WEAK_PERCEIVED_BENEFIT_PHRASES`, especialmente `eligible spend`, `confirmed benefits and costs`, `real practical value`, `functionalities relevant`, `peace of mind`, `make the most of your spending`.

## Resultado validado da abordagem benefit-led

A v8 oficial do Pacote 3.2A passou em dois cartões balance transfer diferentes:

```text
NatWest Longer Balance Transfer Card
- success:true
- validate-article.sh PASS
- qa-content-validator.py OK
- count 450, subtitle 85, max_section_paragraphs 4, long_sentence_ratio 0.1034

Tesco Bank Balance Transfer Credit Card
- success:true com facts oficiais explícitos no request
- validate-article.sh PASS
- qa-content-validator.py OK
- count 472, subtitle 98, max_section_paragraphs 4, long_sentence_ratio 0.08
```

Os corpos ficaram claramente diferentes (5-gram Jaccard ~0.0177), confirmando que o LLM corrigiu a causa raiz de repetição melhor do que o gerador determinístico.

## Cuidado com auto-commit em testes de pacote

O script de pacote fazia `git add "$RUNNER"`; no repo MGS há automação de auto-commit/auto-push. Em teste temporário de pacote, isso pode commitar/pushar antes da aprovação formal.

Para próximos pacotes de runner:

- preferir simular/aplicar em cópia temporária fora do repo antes;
- ou remover/neutralizar `git add` do script durante smoke temporário;
- ou pausar a automação de auto-commit se Rodolfo aprovar;
- se a automação já comitou o diff aprovado tecnicamente, não reescrever histórico remoto sem ordem explícita; reportar o commit e estado real.

## Nota sobre facts/extractor

No teste source-only da NatWest, o extractor pegou um benefício fraco de página (“Money guidance adds practical context”). Isso é tema futuro de extração/facts pack, não deve ser misturado com o pacote de prompt/runner 3.2A.

No teste Tesco source-only, o extractor retornou `annual_fee: N/A` e bloqueou antes do LLM; usando facts oficiais explícitos da página, o LLM passou. Isso reforça que 3.2A é integração/prompt do corpo, enquanto robustez de extração/facts pack é melhoria separada.
