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

Topologia vigente: `context/drive-flat-intake-cutover.md` e binding vivo `flat-intake-binding.json`. A aprovação geral `1566814476626563115` e a confirmação de preservação de acessos `1566825959645253764` supersedem o desenho anterior. Receita executável: `flat-upload-intake.md`.

```text
MGS-AGENTS
https://drive.google.com/drive/folders/0AEwt4Ye690ocUk9PVA
└── UPLOAD MANUAL  [1ARBvLammWUHuAclNmcriwkkgeedKryBd]
    ├── arquivos enviados diretamente
    └── _PROCESSAMENTO  [somente staging técnico e temporário]

30 TB
├── MGS-ARQUIVO/CRIATIVOS/{OPERAÇÃO}/{IMG|VID}/...
└── MGS-CORPORATIVO  [relatórios, referências e backups]
```

O Shared Drive é entrada/staging, não estoque definitivo. Agentes permanecem na SA canônica; não fazer upload binário SA no Meu Drive nem usar OAuth pessoal como fallback. O transporte owner isolado aprovado entrega aos 30 TB, com receipt/ACK/stock e resolvedores vigentes. Não recriar CRIATIVOS, nichos ou gestores na entrada para imitar paths antigos. `MGS-AGENTS/CRIATIVOS/...` pode continuar namespace lógico de inventário: preservar esses registros e IDs, sem tratar o texto como localização física. No flat, operação/gestor/destino vêm do pedido humano registrado, nunca do nome ou pasta do upload.

Regra de REPORT-INFRA: enviar pelo helper canônico `/root/mgs-agent/scripts/send-report-infra-embed.sh`, com content vazio, embed único, sem mentions e sem thread. Ler de volta o message_id exato em #alerts-infra (`1498132022634483894`) antes de declarar envio. Sem helper/transporte, registrar pendência; não usar fallback textual nem publicar uma segunda cópia. Não usar script de outro agente como caminho padrão.

### Gate de capacidades no UPLOAD MANUAL

Arquivos enviados por Kelly, Evo ou outro colaborador diretamente em `UPLOAD MANUAL` pertencem ao Shared Drive/organização, não ao uploader individual. Não exigir transferência de propriedade nem licença Workspace adicional do colaborador.

1. No intake/staging, validar driveId MGS e o parent real: entrada diretamente em UPLOAD MANUAL. No stock/arquivo permanente, usar o binding/metadata My Drive dos 30 TB; não exigir driveId Shared Drive nesses objetos.
2. Exigir apenas capabilities usadas no pedido: download, criação da cópia limpa em staging e movimento do bruto por mesmo ID. canTrash/canDelete não são pré-requisitos de tratamento; o flat confirmado não usa DELETE/trash.
3. Validar RAW/clean e o estágio técnico READY/LEGACY, depois receipt/ACK/stock e entrega permanente. common organiza em 01_READY sem liberar reservas; exclusive entrega em `<NOME> - Exclusivos`; uso confirmado segue a `<NOME> - Usados`. Duplicatas preservam linhagem/destino/uso. Pedido de copiar/manter não autoriza retirar a origem nem iniciar campanha.
4. Falha de capability dentro do Shared Drive é drift de infraestrutura/acesso. Não pedir transferência de owner ao gestor.
5. Usar HTTP + readback da operação como prova final e preservar inventário, checksum e linhagem.
6. Não trocar silenciosamente a identidade canônica do Ares pela conta do colaborador.

Detalhe operacional: `references/my-drive-collaborator-control-and-deletion.md`.

### Concorrência, idempotência e lote já em processamento

O mesmo pedido Discord pode chegar a mais de uma sessão, e dois fluxos podem observar o mesmo snapshot de `UPLOAD MANUAL`. Evitar qualquer segundo write concorrente sobre a mesma linhagem.

1. No flat ativo, registrar o contexto e usar o mesmo job/claim canônico conforme `flat-upload-intake.md`; consultar assert_source_writer e preservar o manifesto original. O lock local de um adapter não substitui o claim nem autoriza segundo writer. Conservar locks intake → queue → inventory e o lock operacional durante mutações.
2. Se o conjunto live diminuir ou um source sair da entrada, não presumir perda de permissão e não iniciar um lote parcial. Consultar primeiro `assets.jsonl`, o report `ready-execution` mais recente e processos/runners ativos para os mesmos IDs.
3. Se outra execução estiver ativa, aguardar sua conclusão sem interferir. Se já concluiu, reutilizar o resultado canônico em vez de criar novas cópias ou variantes.
4. Após conclusão, verificar o lote por IDs, nomes, tamanho/checksum, download/clean, linhagem única e destino permanente atual autorizado. READY/LEGACY podem ser staging ou namespace histórico; Exclusivos/Usados e relocação same-ID não são falha. Separar saldo do pedido e arquivos não relacionados da entrada; não exigir zero global.
5. Só montar um novo plano para o subconjunto restante quando houver evidência de que não existe execução ativa nem conclusão registrada. Sempre gerar snapshot fresco; nunca reutilizar CSV stale para write.
6. O lock cobre a seção crítica desde o re-scan até inventário/report final. Liberar em `finally`/trap mesmo em erro.

### Fonte canônica do Google Drive

- Projeto: `mgs-core-prod`.
- Identidade: `mgsagent@mgs-core-prod.iam.gserviceaccount.com`.
- 1Password: `Google Service Account - MGS Agent`.
- Runtime: `ARES_DRIVE_AUTH_MODE=service_account`; OAuth pessoal não é fallback.
- Para validar o nome do Shared Drive, usar `GET /drive/v3/drives/{driveId}?fields=id,name`. O recurso raiz em `files/{driveId}` pode retornar `name=Drive`; validar nesse recurso o ID, `driveId`, `trashed` e capabilities, sem exigir que seu nome seja `MGS-AGENTS`. Conferir o nome canônico no recurso `drives` evita bloquear um Drive correto por diferença de representação.
- Após correção, validar token, GET de arquivo real, PATCH controlado + GET/readback e Shared Drive `MGS-AGENTS`.

Estrutura de status do estoque permanente nos 30 TB. CC_US_ES é exemplo/piloto; não recriar a árvore abaixo no Shared Drive. As pastas GEIZIAN e LIBRARY META pertencem ao acervo, não são nova entrada ou pool livre:

```text
MGS-ARQUIVO/CRIATIVOS/
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
MGS-ARQUIVO/CRIATIVOS/CAR_US_EN/VID/01_READY/CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4
```

Exemplo incorreto que deve ser corrigido/não repetido:

```text
MGS-ARQUIVO/CRIATIVOS/CAR_US_EN/VID/STORY/EN/01_READY/CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4
```

Não inserir `READY`, `TESTING`, `TESTED`, `WINNER` ou `REJECTED` no nome do arquivo. O status fica na pasta/inventário para evitar renomear o mesmo asset a cada mudança de status.

Regra de idioma para operações brasileiras: se o país for `BR` e o pedido disser apenas “Português”, usar `LANG=BR` (`CAR_BR_BR`, `GAME_BR_BR`). Usar `LANG=PT` somente quando português de Portugal (`PORTUGUÊS-PT`/`PT-PT`) for explícito.

UPLOAD MANUAL é a única entrada operacional; arquivos vão diretamente à pasta, inclusive IMG/VID acima de 10 MB. O inventário read-only canônico é `ares-drive-upload-manual-inventory.py`; o wrapper upload-canvas é compatibilidade. Inventário não atribui contexto nem autoriza tratar todas as fontes: registrar o pedido humano e seus IDs exatos conforme flat-upload-intake.md. A saída canônica preserva RAW/clean, valida staging e entrega permanente, e arquiva gerações concluídas por mesmo ID/bytes/ACL, sem DELETE. Arquivos sem contexto, saldo ou pedido explícito de copiar/manter são preservados e contabilizados separadamente. UPLOAD_CANVAS é histórico, não recriar.

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
7      Validar staging RAW/clean, receipt/ACK/stock e destino permanente autorizado; reconciliar saída same-ID e o saldo exato do pedido, sem inferir zero global da entrada.
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
