# REC architecture cleanup and runner contract

Session pattern: Rodolfo found the REC stack confusing because the same rules existed across `AGENT.md`, Atena `SOUL.md`, Atena `config.yaml`, `content-generate-rec/SKILL.md`, `templates/rec-gb-cc-en.md`, `mgs-rec-runner.py`, `generate_article_local()`, and `validate-article.sh`. The durable fix is not another manual instruction; it is a clean layer contract.

## Target architecture

```text
Layer                         Responsibility
-----------------------------|------------------------------------------------
AGENT.md                     Global authorization, safety, reporting standards only
Atena SOUL.md                Short behavior rules; REC direct = runner first
Atena config/channel_prompt  Minimal Discord/thread instructions, no long scripts
content-generate-rec/SKILL.md Runner usage and implementation references
templates/rec-{template_key}.md Editorial/visual prompt contract per vertical
mgs-rec-runner.py            Single deterministic REC executor
validate-article.sh          Mechanical gates: word count, paragraphs, H2 density, sentences
image scripts                Card orientation, 16:9 featured, composition quality
```

## Key workflow rule

For a complete REC request with site + exact card + status + official source URL:

```text
Atena should not pre-read AGENT.md, full SKILL.md, templates, runner source, or browser pages.
Atena calls mgs-rec-runner.py once and summarizes the JSON.
```

Read the larger files only when:
- the runner fails with a specific error;
- the user asks for an audit/explanation;
- a template/validator/runner change is being made;
- the request is incomplete and needs clarification.

## Template contract

`sites.json[site_key].template_key` is the selector. For eggbev this is `gb-cc-en`, so the template file is `skills/content-generate-rec-p1/templates/rec-gb-cc-en.md`.

The template is not a routine Atena reading dependency. It is the editorial/visual contract that the runner/API/validator must enforce. The runner should validate that the template exists and expose a compact `template_contract` in its JSON rather than forcing Atena to load the full prompt.

Expected compact runner fields:

```json
{
  "template_contract": {
    "template_key": "gb-cc-en",
    "contract_loaded": true,
    "has_word_count_gate": true,
    "has_paragraph_gate": true,
    "has_horizontal_card_gate": true,
    "has_featured_three_layer_gate": true
  }
}
```

## Anti-loop prompt/config cleanup

Durable fixes that reduce reading/tool loops:

1. In `AGENT.md`, use `template_key`, not legacy `vertical`, for REC template routing.
2. Mark legacy 4-pause REC manual flow as deprecated for routine runner REC.
3. In Atena `SOUL.md`, remove any unconditional “read AGENT.md now” instruction. Use: follow AGENT.md as policy; read it only for authorization/security/critical-subset/conflict questions.
4. Replace long mandatory Discord thread rename/mention scripts in SOUL/channel_prompt with a short “first response without overhead” rule.
5. Keep Atena’s channel_prompt small. It should not embed long Python snippets or workflow checklists.
6. Keep high-detail implementation notes in `references/`, not in the top-level fast path.

## Validation pattern

After changes, validate without publishing:

```bash
python3 -m py_compile /root/mgs-agent/scripts/mgs-rec-runner.py
python3 - <<'PY'
import yaml, json
yaml.safe_load(open('/root/.hermes/profiles/atena/config.yaml'))
json.load(open('/root/mgs-agent/data/sites.json'))
print('config_ok')
PY
/root/mgs-agent/scripts/mgs-rec-runner.py \
  --site eggbev \
  --card "Barclaycard Avios Credit Card" \
  --status draft \
  --source-url "https://www.barclaycard.co.uk/personal/credit-cards/avios" \
  --dry-run
```

Dry-run should show `success: true`, `validation.status: PASS`, and `template_contract.template_key: gb-cc-en`.

## Pitfall

Do not solve confusion by telling Atena to read more. That is the failure mode. The fix is to put rules into deterministic scripts/validators and expose compact JSON evidence for Zeus/Rodolfo.