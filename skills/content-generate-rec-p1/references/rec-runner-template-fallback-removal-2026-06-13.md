# REC runner template fallback removal — Fase 2 / Pacote 3 (2026-06-13)

## Contexto

O `scripts/mgs-rec-runner.py` tinha um caminho legado em `load_rec_template_contract`: se `skills/content-generate-rec-p1/contracts/cc-rec.md` não existisse, o runner caía para `skills/content-generate-rec-p1/templates/rec-{template_key}.md`.

Esse fallback estava dormente porque `cc-rec.md` existe, mas mantinha os templates antigos como autoridade paralela potencial e impedia arquivamento seguro no Pacote 2.

## Decisão aplicada

`cc-rec.md` virou hard requirement do REC runner.

Comportamento correto agora:

- `load_rec_template_contract` deve carregar sempre `REC_UNIVERSAL_CONTRACT` (`contracts/cc-rec.md`).
- Se `cc-rec.md` faltar, levantar `RunnerError` explícito e auditável.
- Não reativar fallback para `templates/rec-{template_key}.md`.
- `template_key` esperado no smoke test: `cc-universal`.

Mensagem de erro desejada deve apontar claramente o contract ausente, por exemplo:

```text
REC universal contract not found: /root/mgs-agent/skills/content-generate-rec-p1/contracts/cc-rec.md. This file is required for REC generation; the legacy template fallback was removed.
```

## Validação segura usada

Ao aplicar mudanças semelhantes no runner:

1. Conferir SHA atual antes de tocar no arquivo.
2. Salvar versão nova em staging fora do caminho ativo.
3. Rodar `python3 -m py_compile` na versão nova antes de instalar.
4. Fazer backup datado do runner atual.
5. Instalar a versão nova.
6. Rodar `python3 -m py_compile` no instalado.
7. Smoke test funcional:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("mgs_rec_runner", "mgs-rec-runner.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
site = m.load_site("eggbev")
res = m.load_rec_template_contract(site)
assert res.get("contract_loaded") is True
assert res.get("template_key") == "cc-universal"
assert "cc-rec.md" in res.get("path", "")
print("SMOKE_OK", res.get("template_key"), res.get("path"))
```

8. Rodar dry-run real do REC runner que alcance `content_validated_final` e `dry_run_skip_publish`, confirmando no JSON:

```text
template_contract.template_key == cc-universal
template_contract.path contains contracts/cc-rec.md
template_contract.contract_loaded == True
success == True
dry_run == True
```

9. Verificar `git status`, `HEAD`, `origin/main`.

## Pitfall observado

O script de aplicação fez `git add` do runner. Como havia staging dentro do repo (`/root/mgs-agent/pacote3-staging`), o auto-push/auto-commit chegou a versionar o staging artifact.

Regra prática para próximas aplicações:

- Preferir staging fora do repo quando possível (`/root/...`) ou garantir que o diretório de staging seja removido/ignorado antes do auto-push.
- Antes de finalizar, conferir `git show --name-only HEAD` para garantir que só os arquivos pretendidos foram versionados.
- Se staging artifact entrar no Git, remover com `git rm -r <staging>` e sincronizar novamente antes de reportar repo limpo.
