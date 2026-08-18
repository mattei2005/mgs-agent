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
fora_de_escopo         Pedido pertence o Ares, Atena, Zeus ou humano.
```

Não marque como `aprovado` ou `pronto_para_ares` se não houver aprovação explícita ou se o asset final não estiver definido.
## Drive/Canva — reestruturação multivertical

Shared Drive raiz operacional atual validado por readback:

```text
MGS-AGENTS
https://drive.google.com/drive/folders/0AEwt4Ye690ocUk9PVA
└── CRIATIVOS
    └── {OPERAÇÃO}/{IMG|VID}/{STATUS}
```

O root canônico é exclusivamente o Shared Drive `0AEwt4Ye690ocUk9PVA`, administrado no Google Workspace por `support@matteiservicesinc.com`. Nomes, paths e estrutura permanecem iguais. Não criar operações (`CAR_BR_PT`, `CC_US_ES`, etc.) como filhas diretas de `MGS-AGENTS`; criar/mover sempre dentro de `MGS-AGENTS/CRIATIVOS`.

Regra de REPORT-INFRA para mudanças de skill/script/data/config feitas pelo Ares: não declarar “enviei o REPORT-INFRA” com base apenas em intenção. Primeiro executar o envio real pelo helper canônico `/root/mgs-agent/scripts/send-report-infra-embed.sh` ou, se usar fallback textual, validar o transporte correspondente: `HTTP 200/201` com `message_id` no bot poster atual, ou `HTTP 204` no webhook legado. Em seguida, confirmar via Discord API que a mensagem existe em `#alerts-infra` (`1498132022634483894`), com `content` vazio e embed esperado, antes de afirmar na thread original. Não usar scripts com nome de outro agente como caminho padrão (`ares-report-infra.sh`) quando houver helper canônico MGS.

### Gate de capacidades no UPLOAD MANUAL

Arquivos enviados por Kelly, Evo ou outro colaborador diretamente em `UPLOAD MANUAL` pertencem ao Shared Drive/organização, não ao uploader individual. Não exigir transferência de propriedade nem licença Workspace adicional do colaborador.

1. Validar que o item possui `driveId=0AEwt4Ye690ocUk9PVA` e está sob `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`.
2. Consultar as capabilities reais e exigir que o Ares consiga baixar, editar, mover, enviar à lixeira e excluir quando a ação estiver autorizada.
3. No fluxo de tratar/mover, validar a cópia limpa em `01_READY` e mover o bruto para `99_LEGACY`; em pedido explícito de copiar/manter, preservar a entrada conforme solicitado.
4. Falha de capability dentro do Shared Drive é drift de infraestrutura/acesso. Não pedir transferência de owner ao gestor.
5. Usar HTTP + readback da operação como prova final e preservar inventário, checksum e linhagem.
6. Não trocar silenciosamente a identidade canônica do Ares pela conta do colaborador.

Detalhe operacional: `references/my-drive-collaborator-control-and-deletion.md`.

### Concorrência, idempotência e lote já em processamento

O mesmo pedido Discord pode chegar a mais de uma sessão, e dois fluxos podem observar o mesmo snapshot de `UPLOAD MANUAL`. Evitar qualquer segundo write concorrente sobre a mesma linhagem.

1. Imediatamente antes do primeiro write, obter um lock exclusivo por operação + conjunto ordenado de `source_drive_id` (arquivo sob `/root/mgs-agent/tmp/ares-intake-locks/`, usando `flock`) e repetir o inventário/API read-only dentro do lock.
2. Se o conjunto live diminuir ou um source sair da entrada, não presumir perda de permissão e não iniciar um lote parcial. Consultar primeiro `assets.jsonl`, o report `ready-execution` mais recente e processos/runners ativos para os mesmos IDs.
3. Se outra execução estiver ativa, aguardar sua conclusão sem interferir. Se já concluiu, reutilizar o resultado canônico em vez de criar novas cópias ou variantes.
4. Após execução concorrente concluída, verificar de forma independente: source em `99_LEGACY`, destination em `01_READY`, nome/pasta/tamanho/checksum, download + `clean=true`, inventário com uma única linhagem e entrada sem pendências.
5. Só montar um novo plano para o subconjunto restante quando houver evidência de que não existe execução ativa nem conclusão registrada. Sempre gerar snapshot fresco; nunca reutilizar CSV stale para write.
6. O lock cobre a seção crítica desde o re-scan até inventário/report final. Liberar em `finally`/trap mesmo em erro.

### Fonte canônica do Google Drive

- Projeto: `mgs-core-prod`.
- Identidade: `mgsagent@mgs-core-prod.iam.gserviceaccount.com`.
- 1Password: `Google Service Account - MGS Agent`.
- Runtime: `ARES_DRIVE_AUTH_MODE=service_account`; OAuth pessoal não é fallback.
- Após correção, validar token, GET de arquivo real, PATCH controlado + GET/readback e Shared Drive `MGS-AGENTS`.

Estrutura de referência por vertical/operação. `CC_US_ES` é exemplo/piloto; outras verticais devem ser organizadas na pasta correta do Drive:

```text
MGS-AGENTS/CRIATIVOS/
├── UPLOAD MANUAL     # fila temporária para arquivos, inclusive >10 MB
├── GEIZIAN           # cópias de conveniência para upload; ignorar no pool/inventário canônico
├── LIBRARY META      # referências; nunca asset final automático
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
MGS-AGENTS/CRIATIVOS/CAR_US_EN/VID/01_READY/CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4
```

Exemplo incorreto que deve ser corrigido/não repetido:

```text
MGS-AGENTS/CRIATIVOS/CAR_US_EN/VID/STORY/EN/01_READY/CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4
```

Não inserir `READY`, `TESTING`, `TESTED`, `WINNER` ou `REJECTED` no nome do arquivo. O status fica na pasta/inventário para evitar renomear o mesmo asset a cada mudança de status.

Regra de idioma para operações brasileiras: se o país for `BR` e o pedido disser apenas “Português”, usar `LANG=BR` (`CAR_BR_BR`, `GAME_BR_BR`). Usar `LANG=PT` somente quando português de Portugal (`PORTUGUÊS-PT`/`PT-PT`) for explícito.

`UPLOAD MANUAL` é a única fila de entrada operacional atual. Ela recebe IMG/VID enviados fora do Discord, especialmente arquivos acima de 10 MB. O inventário read-only canônico é `/root/mgs-agent/scripts/ares-drive-upload-manual-inventory.py`; o nome antigo `ares-drive-upload-canvas-inventory.py` é apenas wrapper de compatibilidade. Quando a ação for **tratar/mover**, o arquivo-fonte deve sair da fila somente depois de a versão limpa estar verificada e presente no `01_READY` correto. Para preservar o bruto sem deixar falso backlog, mover o original para `{OPERAÇÃO}/{IMG|VID}/99_LEGACY`, mantendo ID/nome original e sem deletar. Manter na entrada somente quando Rodolfo/Kelly pedir explicitamente **copiar** ou **manter o original no upload**. `UPLOAD_CANVAS` não existe mais e é somente referência histórica.

Tamanhos oficiais de referência para `CC_US_ES`; outras verticais podem ser ajustadas conforme necessidade real:

```text
Placement  Dimensão   Aspect ratio  Com pessoa  Sem pessoa
─────────  ─────────  ────────────  ──────────  ──────────
STORY      1080x1920  9:16          PV          NV
FEED       1080x1080  1:1           PH          NH
```

Fluxo seguro:

```text
Etapa  Ação
─────  ─────────────────────────────────────────────────────────────
1      Ler os arquivos brutos em `UPLOAD MANUAL`.
2      Detectar IMG/VID, dimensão, aspect ratio e placement.
3      Sugerir ANGLE/P_ORIENT sem inventar.
4      Gerar inventário e plano de renomeação/destino.
5      Se o pedido já autorizou `tratar/mover` dentro da estrutura canônica, esse pedido é a aprovação; não pedir confirmação redundante.
6      Mostrar plano e pedir decisão apenas quando houver ambiguidade, nova estrutura, destino não canônico ou mudança de escopo.
7      Após copiar/mover/renomear, validar `01_READY`, mover o bruto para `99_LEGACY` e confirmar que a entrada contém só pendências.
```

### Rastreabilidade obrigatória de renomeação

Em **todo upload organizado pelo Ares**, independentemente da origem (`UPLOAD MANUAL`, Discord, Canva ou outro intake autorizado):

1. Registrar no inventário o par exato `source_filename → destination_filename`, junto com IDs de origem/destino quando existirem.
2. Na resposta de conclusão ao solicitante, listar **cada arquivo** como `nome original → nome final em READY`.
3. Em lotes grandes, separar por `IMG` e `VID`, mas nunca substituir a lista individual por apenas uma faixa de nomes.
4. Quando a origem for um anexo Discord sem filename humano preservado, usar e identificar explicitamente o filename técnico/cache disponível; não inventar o nome original.
5. Esse mapa é a chave humana para localizar o bruto preservado em `99_LEGACY` e deve acompanhar todas as entregas futuras.

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
