# Fase 2 migration package ops — Pacotes 2/4 (2026-06-14)

Contexto: Rodolfo conduz refactors da Atena por pacotes pequenos, com hashes esperados e scripts enviados no chat. O agente deve tratar isso como mudança operacional auditável de REC+P1, não como edição ad hoc.

## Padrão validado

1. Antes de rodar script enviado por Rodolfo, materializar em `/root/<nome>.sh`, `chmod 700` e revisar o conteúdo rapidamente.
2. Verificar estado inicial do repo e hashes esperados dos alvos antes da mutação:
   - `git status --short`
   - `git rev-parse HEAD`
   - `git rev-parse origin/main`
   - `sha256sum <arquivos-alvo>`
3. Rodar o script exatamente como enviado quando as travas baterem.
4. Capturar saída completa do script para reportar ao Rodolfo.
5. Fazer validações independentes pós-script, especialmente quando o script edita JSON ou move arquivos:
   - JSON parseável.
   - Campo removido realmente ausente.
   - Chaves e valores preservados, especialmente `credentials_ref`.
   - Arquivos movidos existem no destino e não existem na origem.
   - Smoke tests reportados pelo script (`SMOKE_REC_OK cc-universal`, `SMOKE_P1_OK`, etc.).
6. Se o script deixou somente mudanças esperadas em staging, commitar com mensagem curta. Não misturar dirty state preexistente.
7. Confirmar pós-commit:
   - `git rev-parse HEAD`
   - `git rev-parse origin/main`
   - `git rev-list --left-right --count HEAD...origin/main`
   - `git status --short`
8. No report, separar claramente:
   - mudanças do pacote;
   - dirty state preexistente/não relacionado;
   - evidência de `HEAD == origin/main`;
   - saída completa quando solicitada.

## Detalhes do Pacote 2

- `data/sites.json` tinha SHA esperado `bfec8f8a...` antes da remoção de `template_key`.
- Templates legados foram movidos com `git mv` para:
  - `skills/content-generate-rec-p1/references/archive/rec-gb-cc-en-2026-06-12.md`
  - `skills/content-generate-rec-p1/references/archive/p1-gb-cc-en-2026-06-12.md`
- Hashes dos arquivos arquivados permaneceram iguais aos templates originais.
- `eggbev` permaneceu com 13 chaves: `credentials_ref` + 12 outras, sem `template_key`.

## Pitfalls

- `git status` pode conter sujeira não relacionada antes do pacote. Registrar isso antes da execução e não incluir no commit.
- O grep por `template_key` pode continuar achando telemetria/contract (`cc-universal`) e references antigas. Diferenciar uso ativo de `sites.json[template_key]` de menções documentais ou output JSON.
- Quando Rodolfo pedir arquivo para outro agente editar, anexar o tar nativo no Discord (`MEDIA:/abs/path`) e colar sha + grep relevante.