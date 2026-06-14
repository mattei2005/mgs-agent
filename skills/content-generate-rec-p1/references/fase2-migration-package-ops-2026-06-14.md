# Fase 2 migration package ops — REC+P1

Contexto: Rodolfo estava usando Claude para montar pacotes de migração e encaminhando para Zeus aplicar na VPS. A função do Zeus não é só executar: é revisar se o pacote faz sentido para a operação real da MGS/Atena.

## Padrão validado

Para pacotes de migração REC+P1:

1. Conferir estado real antes:
   - `git status --short`
   - HEAD, `origin/main` e remote main quando aplicável
   - sha256 dos arquivos-alvo
   - dirty state preexistente separado do pacote
2. Ler/revisar o script recebido e os arquivos de staging antes de executar.
3. Confirmar que as travas do script batem com o estado real.
4. Rodar o script exatamente, sem editar durante a aplicação, se a revisão fizer sentido.
5. Validar fora do script:
   - hashes finais
   - grep pós-mudança
   - arquivos movidos/ausentes
   - JSON parseável e chaves preservadas
   - smoke tests dos runners quando houver
   - `git diff`/`git status` limitado ao esperado
6. Commitar somente o diff esperado.
7. Se auto-commit ou hook capturar artefato temporário/staging, remover em commit corretivo normal; evitar force-push/squash salvo pedido explícito.
8. Validar `HEAD == origin/main == remote main`; se `git push` falhar por falta de upstream, verificar `git ls-remote` antes de concluir que não subiu.
9. Reportar saída completa relevante e destacar desvios.

## Lição do Pacote 4

O Pacote 4 atualizou `AGENT.md` para o routing REC+P1 e tinha grep pós-edição para resíduos:

```text
template_key|templates/rec|templates/p1|ABORT|verified cache
```

Isso foi necessário, mas estreito. A revisão posterior encontrou resíduos documentais que não quebravam código, mas podiam confundir Atena/Claude:

```text
skills + templates
4 mandatory pauses
rec-gb-cc-en.md
gb-cc-en
```

Para `AGENT.md`/routing, usar grep amplo:

```text
template_key|templates/rec|templates/p1|rec-gb-cc-en|gb-cc-en|4 mandatory pauses|verified cache|rec_create|list_templates
```

## Regra de julgamento

Se o núcleo técnico passou mas sobrou documentação antiga que contradiz a nova arquitetura, não declarar a fase 100% fechada. Recomendar micro-pacote corretivo antes de prosseguir.

## Arquitetura esperada pós-Fase 2

- REC+P1 é o produto normal.
- REC-only/P1-only são exceções explícitas.
- `data/sites.json` não usa `template_key` como routing editorial.
- `contracts/cc-rec.md` e `contracts/cc-p1.md` são as fontes editoriais ativas.
- Templates legados `rec-gb-cc-en.md` e `p1-gb-cc-en.md` ficam apenas em `references/archive/`.
- Cache editorial não é fonte de research; fatos vêm da URL oficial ou fonte oficial confirmada.
