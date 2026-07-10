## Campos do nome

```text
Campo      | Regra
-----------|----------------------------------------------------------
VERTICAL   | Código da vertical: CC, CAR, EMP, JOB, APP, GAME etc.
COUNTRY    | País alvo: US, CA, MX, BR etc.
LANG       | Idioma do criativo: EN, ES, FR, DE, PT etc.
FORMAT     | IMG ou VID
ANGLE      | Ângulo controlado por operação/idioma
P_ORIENT   | Código compacto de pessoa + orientação
VARIANT    | Sequência 3 dígitos: 001, 002, 003... até 999
ext        | Extensão real do arquivo: jpg, png, mp4 etc.
```

Regra operacional para `VARIANT`:

- Sempre gerar e corrigir variantes com **3 dígitos** (`001`-`999`), nunca `01`-`99`.
- Motivo: com 2 dígitos, arquivos como `_100` podem ficar fora da ordem alfabética/natural esperada em Drive, CSVs e revisões manuais.
- Ao corrigir assets já feitos, renomear o arquivo real no Drive e depois normalizar CSVs/propostas locais para refletir o novo nome.
- Manter evidência auditável da mudança com `old_name`, `new_name`, `verified_name`, `drive_id`, `status` e hash do relatório; não apagar a trilha de auditoria.

Regras importantes:

- O nome deve ser uppercase, limpo, sem acento e com underscore.
- Não colocar status no nome.
- Não colocar site no nome.
- Não colocar gestor/origem no nome.
- Não colocar IDs longos no nome.
- `drive_id`, `page_id`, `meta_creative_id`, `origin_campaign_id` e origem ficam no inventário/metadados.
