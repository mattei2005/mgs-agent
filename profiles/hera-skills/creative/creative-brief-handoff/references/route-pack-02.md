## Fluxo de status

Use status simples e consistentes.

```text
Status                 Quando usar
─────────────────────  ─────────────────────────────────────────────────
intake                 Pedido recebido, mas ainda incompleto.
brief_pronto           Brief estruturado, aguardando execução/revisão.
em_criacao             Variações ou assets sendo produzidos.
precisa_revisao        Falta aprovação humana, link, oferta ou contexto.
aprovado               Pronto para uso operacional.
pronto_para_ares       Pacote aprovado e suficiente para o Ares usar.
bloqueado              Falta decisão, acesso, asset, link ou dono.
fora_de_escopo         Pedido pertence a Ares, Atena, Zeus ou humano.
```

Não marque como `aprovado` ou `pronto_para_ares` se não houver aprovação explícita ou se o asset final não estiver definido.
## Drive/Canva — reestruturação multivertical

Pasta raiz operacional atual validada no Drive:

```text
MGS-AGENTS
https://drive.google.com/drive/folders/14ica5TVauTrzAxcl4T-ViJorF89vRKIl
└── CRIATIVOS
    └── {OPERAÇÃO}/{IMG|VID}/{STATUS}
```

Correção importante validada em 2026-07-02: o ID `14ica5TVauTrzAxcl4T-ViJorF89vRKIl` resolve para `MGS-AGENTS`, não para uma pasta direta `MGS-CRIATIVOS`. Não criar operações (`CAR_BR_PT`, `CC_US_ES`, etc.) como filhas diretas de `MGS-AGENTS`; criar/mover sempre dentro de `MGS-AGENTS/CRIATIVOS`.

Regra de REPORT-INFRA para mudanças de skill/script/data/config feitas pela Hera: não declarar “enviei o REPORT-INFRA” com base apenas em intenção. Primeiro executar o envio real pelo helper canônico `/root/mgs-agent/scripts/send-report-infra-embed.sh` ou, se usar fallback textual, validar HTTP 204 e confirmar via Discord API que a mensagem aparece em `#alerts-infra` (`1498132022634483894`) antes de afirmar na thread original. Não usar scripts com nome de outro agente como caminho padrão (`ares-report-infra.sh`) quando houver helper canônico MGS.

Estrutura de referência por vertical/operação. `CC_US_ES` é exemplo/piloto; outras verticais devem ser organizadas na pasta correta do Drive:

```text
MGS-AGENTS/CRIATIVOS/
├── UPLOAD MANUAL
└── CC_US_ES/
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

### Regra canônica de destino final READY

Para assets organizados para teste/consumo pelo Ares, o destino final **não** deve criar subpastas intermediárias de placement/idioma como `STORY/EN/01_READY`.

```text
Campo/decisão             Onde fica
────────────────────────  ─────────────────────────────────────────────
País/vertical/língua      Pasta de operação: CAR_US_EN, CC_US_ES etc.
IMG ou VID                Pasta de tipo: IMG ou VID.
Status                    Pasta de status: 01_READY, 02_TESTING etc.
STORY/FEED/REELS          Inventário/handoff, não subpasta final.
Ângulo                    Nome do arquivo.
Pessoa/orientação         Nome do arquivo.
```

Exemplo correto:

```text
MGS-CRIATIVOS/CAR_US_EN/VID/01_READY/CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4
```

Exemplo incorreto que deve ser corrigido/não repetido:

```text
MGS-CRIATIVOS/CAR_US_EN/VID/STORY/EN/01_READY/CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4
```

Não inserir `READY`, `TESTING`, `TESTED`, `WINNER` ou `REJECTED` no nome do arquivo. O status fica na pasta/inventário para evitar renomear o mesmo asset a cada mudança de status.

`UPLOAD CANVAS` / `UPLOAD MANUAL` é uma área de entrada, não arquivo permanente. Correção executiva de Rodolfo (2026-07-10): quando a ação operacional for **tratar/mover**, o arquivo-fonte deve sair da pasta de upload somente depois de a versão limpa estar verificada e presente no `01_READY` correto. Para preservar o bruto sem deixar falso backlog, mover o original para `{OPERAÇÃO}/{IMG|VID}/99_LEGACY`, mantendo ID/nome original e sem deletar. A pasta de upload deve conter apenas itens ainda pendentes. Exceção: manter na entrada somente quando Rodolfo/Kelly pedir explicitamente **copiar** ou **manter o original no upload**.

Tamanhos oficiais de referência para `CC_US_ES`; outras verticais podem ser ajustadas conforme necessidade real:

```text
Placement  Dimensão   Aspect ratio  Com pessoa  Sem pessoa
─────────  ─────────  ────────────  ──────────  ──────────
STORY      1080x1920  9:16          PV          NV
FEED       1080x1080  1:1           PS          NS
```

Fluxo seguro:

```text
Etapa  Ação
─────  ─────────────────────────────────────────────────────────────
1      Ler os arquivos brutos em `UPLOAD CANVAS`.
2      Detectar IMG/VID, dimensão, aspect ratio e placement.
3      Sugerir ANGLE/P_ORIENT sem inventar.
4      Gerar inventário e plano de renomeação/destino.
5      Mostrar o plano para Rodolfo.
6      Só copiar/mover/renomear após aprovação explícita.
```

Inventário mínimo para plano de reestruturação:

```text
original_filename
suggested_filename
source_folder
destination_folder
format
angle
p_orient
variant
width
height
aspect_ratio
placement_fit
language
manager/source
canva_design_id
asset_drive_id
created_by
requested_by
used_by
campaign_owner
source
status
notes
```
