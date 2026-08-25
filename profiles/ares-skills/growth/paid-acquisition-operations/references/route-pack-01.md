## Princípios

1. **Comece pela operação piloto** — defina uma operação única (`VERTICAL_COUNTRY_LANG`, ex.: `CC_US_ES`) antes de generalizar.
2. **Estruture antes de conectar credenciais** — taxonomia, Drive, inventário e regras de decisão devem existir antes de API write.
3. **Read-only primeiro** — Meta Ads e Drive começam em leitura; write só em sandbox ou com aprovação explícita.
4. **Credenciais nunca no chat** — buscar via 1Password/vault e reportar apenas presença, item, len/status ou validações sem segredo.
5. **Ações em produção exigem aprovação explícita** — pausar, clonar, subir criativos, tracking/pixels, budget e billing seguem as regras MGS. Billing é critical subset/double-confirm.
6. **Automatizar o manual primeiro** — pergunte/registre como os gestores fazem corte, pausa, replacement e escala antes de propor melhoria.
## Ordem recomendada para uma nova operação

```text
Ordem | Etapa
------|------------------------------------------------------------
1     | Definir operação piloto: VERTICAL_COUNTRY_LANG
2     | Fechar taxonomia oficial de criativos
3     | Definir estrutura Drive por operação
4     | Criar inventário mínimo/rastreabilidade
5     | Definir regras de decisão dos gestores
6     | Criar/atualizar skills operacionais do Ares
7     | Conectar Drive/Meta em read-only
8     | Gerar relatório diagnóstico
9     | Testar execução em sandbox
10    | Liberar write controlado em produção com aprovação
```
## Taxonomia base de criativos

Para qualquer trabalho de nomenclatura, renomeação, inventário ou classificação de criativos, carregar também a skill dedicada `creative-taxonomy-mgs`. Ela é a fonte operacional detalhada para campos, P_ORIENT, status, inventário mínimo, Drive e metadata gate.

Modelo preferencial, com subtipo veicular opcional para `CAR`:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_[MOTO_]_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Regras:

- `STATUS` não entra no nome; fica na pasta ou inventário.
- IDs (`drive_id`, `meta_creative_id`, `campaign_id`) não entram no nome; ficam no inventário/metadados.
- `ANGLE` deve vir de dicionário controlado por operação/idioma.
- Se o ângulo for incerto, usar `UNKNOWN` e preencher `notes`.
- Não inventar classificação confiante sem evidência.
- Nome limpo, uppercase, sem acento, com underscore.
- Na vertical `CAR`, `MOTO` entra imediatamente depois de `FORMAT` somente quando a revisão visual por asset confirmar motocicleta como produto dominante; carro mantém o padrão sem token adicional. Registrar `vehicle_type=MOTO|CARRO` no inventário.

Pitfall: não deixar a taxonomia viva apenas como spec solto ou comentário de sessão. Quando Rodolfo pedir para “criar a skill”/“execute” sobre taxonomia já estabilizada, criar ou atualizar a skill classe `creative-taxonomy-mgs` e apontar esta umbrella para ela, em vez de criar uma skill estreita por sessão.

### P_ORIENT

```text
Código | Person    | Orientation
-------|-----------|------------
PV     | PERSON    | VERTICAL
PH     | PERSON    | HORIZONTAL
NV     | NO_PERSON | VERTICAL
NH     | NO_PERSON | HORIZONTAL
```

Regra atual de Rodolfo: usar somente `PV`, `PH`, `NV`, `NH`. Códigos `PS`, `NS`, `PU`, `NU`, `UU` foram desconsiderados e não devem entrar em nomes finais. Para detalhes, carregar `creative-taxonomy-mgs`.
## Estrutura Drive recomendada

Use pasta por operação, não por site, pois o mesmo criativo pode rodar em sites diferentes.

```text
MGS-AGENTS/CRIATIVOS/
└── <OPERATION>/
    ├── IMG/
    │   ├── 01_READY
    │   ├── 02_TESTING
    │   ├── 03_TESTED
    │   ├── 04_WINNERS
    │   ├── 05_REJECTED
    │   └── 99_LEGACY
    └── VID/
        ├── 01_READY
        ├── 02_TESTING
        ├── 03_TESTED
        ├── 04_WINNERS
        ├── 05_REJECTED
        └── 99_LEGACY
```
## Inventário mínimo

```text
filename
vertical
country
language
format
angle
person
orientation
p_orient
variant
status
performance_label
source
page_id
asset_drive_id
meta_creative_id
origin_campaign_id
width
height
aspect_ratio
placement_fit
created_at
notes
```

Valores usuais:

```text
status: READY, TESTING, TESTED, WINNER, REJECTED, LEGACY
performance_label: GOOD, BAD, INCONCLUSIVE, UNKNOWN
```
## Gate obrigatório de metadados antes de campanha

Antes de usar qualquer criativo em campanha/teste, Ares deve validar metadados no VPS:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.png
```

Se retornar `clean: false`, limpar antes de usar:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
```

Usar o arquivo `.metadata-clean` como asset de campanha. Se a limpeza falhar ou o formato for incompatível, escalar para Zeus/Rodolfo antes de subir campanha com arquivo bruto.

Referências canônicas:

- `/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md`
- `/root/mgs-agent/logs/creative-metadata-sanitizer.jsonl`
## Tamanhos e placements

Não colocar tamanho no nome salvo exceção operacional explícita. Guardar em inventário (`width`, `height`, `aspect_ratio`, `placement_fit`). Para operações Meta comuns:

```text
Formato operacional | Dimensão  | Aspect ratio | Uso
--------------------|-----------|--------------|-------------------------
FEED                | 1080x1080 | 1:1          | Feed Facebook/Instagram
STORY               | 1080x1920 | 9:16         | Stories Facebook/Instagram
```

Mapeamento quando só há FEED/STORY:

```text
Dimensão  | Sem pessoa | Com pessoa | Orientation
----------|------------|------------|------------
1080x1080 | NH         | PH         | HORIZONTAL
1080x1920 | NV         | PV         | VERTICAL
```
## Canva Connect / Canva Teams → Drive de criativos
## Canva → Drive de criativos

Quando Rodolfo pedir para organizar criativos que estão em pastas do Canva e jogar no Google Drive, operar como pipeline **read-only primeiro** e escolher o caminho conforme o plano/acesso Canva. Para lotes já extraídos do Canva e enviados ao Drive em `UPLOAD_CANVAS`, usar o fluxo de inventário visual/proposta antes de qualquer write: `references/upload-canvas-drive-inventory-workflow.md`.

### Caminho oficial: Canva Connect API

1. Criar/usar integração Canva Connect privada com usuário que tenha acesso às pastas da Kelly/gestores.
2. Usar scopes mínimos: `folder:read`, `design:meta:read`, `design:content:read`.
3. Inventariar pastas/designs antes de baixar ou subir qualquer arquivo.
4. Exportar designs via job assíncrono (`POST /v1/exports`, depois polling em `GET /v1/exports/{exportId}`); URLs de download expiram em 24h.
5. Classificar Feed/Stories/Reels por dimensão/aspect ratio e idioma por nome/pasta ou OCR quando necessário.
6. Subir para Drive somente após aprovação explícita para write.

Pitfalls:

- `GET /v1/folders/{folderId}/items` lista pastas, designs e image assets, mas a documentação atual indica que **video assets soltos não são retornados**; designs exportáveis ainda podem gerar MP4 quando o formato estiver disponível.
- Integrações privadas do Canva Connect são direcionadas a Canva Enterprise; em Canva Teams/Equipe, validar no Developer Portal antes de prometer API privada.

Detalhes técnicos, endpoints, scopes e estrutura piloto: `references/canva-connect-drive-creative-sync.md`.

