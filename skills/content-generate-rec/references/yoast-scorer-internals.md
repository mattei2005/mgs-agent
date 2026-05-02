# Yoast scorer - internal quirks (debug reference)

Reference loaded ON DEMAND quando precisar DEBUGAR o script `yoast-score-post.sh`
ou modificar o engine `scripts/yoast-scorer/yoast-scorer.js`.

**Atena normalmente NAO precisa carregar isso** - ela so executa o script e
le o JSON output. Esta reference eh pra manutencao do script em si.

---

## Scores nao expostos via REST

`_yoast_wpseo_linkdex` e `_yoast_wpseo_content_score` NAO estao em
`register_post_meta` no mu-plugin v4 (por design). Sao gravados em postmeta
e `wp_yoast_indexable` mas nao expostos via REST API. Verificacao eh feita
via SSH/DB. Os valores `indexable_seo` / `indexable_read` no JSON output do
scorer confirmam o estado no banco.

---

## yoastseo v3.6 API quirks (descobertos por trial & error)

- `require('yoastseo')` exporta `{ Paper, assessors, ... }` - os assessors
  ficam dentro do namespace `assessors`:
  `const { SEOAssessor, ContentAssessor } = assessors`
- Assessor constructor: `new SEOAssessor(researcher)` - researcher eh o
  **primeiro** argumento (nao segundo)
- `Researcher` do `_default` nao tem `getHelper()` e retorna scores errados
  -> usar sempre o especifico do idioma:
  `require('./node_modules/yoastseo/build/languageProcessing/languages/en/Researcher').default`
- O modulo Researcher exporta `.default` (ES module wrapped em CJS): sempre
  acessar `.default`
- O scorer DEVE ser executado com `cd "$SCORER_DIR" && node yoast-scorer.js ...`
  (nao `node "$SCORER_DIR/yoast-scorer.js"`) - o segundo nao resolve
  `node_modules` relativo ao script

---

## RunCloud ASCII art interfere com grep em output SQL (CRITICAL)

O banner de boas-vindas do RunCloud contem a string `8888888b...888` (arte
ASCII). Qualquer grep com padrao `^[0-9]+` ou `^\s*[0-9]+\s+[0-9]+` vai
CASAR com essas linhas e retornar os digitos do banner (ex: `888` em vez do
valor real `84`).

**Solucao**: sempre fazer grep pelo `POST_ID` exato na linha, ou usar Python
com `PARSE_ID` env var e um arquivo temp (NAO heredoc dentro de `$(...)` -
falha silenciosamente). Exemplo correto:

```bash
cat > /tmp/_parse.py << 'PYEOF'
import sys, re, os
pid = os.environ.get("PARSE_ID","")
data = sys.stdin.read()
for line in data.replace('\r','').split('\n'):
    m = re.match(r'\|\s*' + re.escape(pid) + r'\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|', line.strip())
    if m:
        print(m.group(1), m.group(2)); sys.exit(0)
print("? ?")
PYEOF
_IDX=$(echo "$SSH_OUT" | PARSE_ID="$POST_ID" python3 /tmp/_parse.py)
rm -f /tmp/_parse.py
```

---

## `wp yoast index` nao aceita `--object-id` (CRITICAL)

O WP-CLI do Yoast v27.x nao suporta reindex de post individual via
`--object-id`. Usar `wp yoast index --reindex` reindexaria o site inteiro
(lento, perigoso).

**Solucao**: SQL UPDATE direto no `wp_yoast_indexable`:

```sql
UPDATE wp_yoast_indexable
  SET primary_focus_keyword_score=84, readability_score=90
  WHERE object_id=62008 AND object_type='post'
```

Seguido de `post meta update` para manter postmeta em sincronia.

---

## yoastseo v3.6 API e `node_modules` path

A lib `yoastseo` deve ser `require`d do diretorio que contem `node_modules/`.
Sempre executar o scorer com `cd "$SCORER_DIR" && node yoast-scorer.js ...`
em vez de `node "$SCORER_DIR/yoast-scorer.js"` (o segundo nao resolve
`node_modules` relativo ao script). API usada:
`{ Paper, SeoAssessor, ContentAssessor, Researcher }`. `Researcher` recebe
`(paper, i18n)` e eh passado para os assessors como segundo arg.
