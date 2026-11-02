## Objetivo

Padronizar a taxonomia de criativos usados em aquisição paga da MGS para que Ares consiga organizar, auditar, renomear, inventariar e comparar performance de assets sem depender de nomes soltos, gestores ou sites.

Esta skill consolida a regra recebida no arquivo de taxonomia Empire e adapta para o padrão operacional MGS.
## Quando usar

Use esta skill quando Rodolfo pedir para:

- organizar criativos por vertical/operação;
- validar nomenclatura de arquivos;
- renomear assets antes de campanha;
- montar inventário de criativos;
- classificar ângulo, pessoa/orientação, idioma, país ou formato;
- preparar criativos para Meta Ads / Google Ads;
- comparar performance por criativo, ângulo, formato, país ou idioma;
- criar ou revisar estrutura de Drive de criativos.

Não use esta skill para conteúdo editorial/REC/SEO. Isso fica fora do escopo do Ares.
## Modelo oficial do nome de arquivo

Modelo base, com subtipo veicular opcional para a vertical `CAR`:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_[MOTO_]_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

```text
Conteúdo de carro  CAR_BR_BR_VID_SCORE_BAIXO_PV_033.mp4
Conteúdo de moto   CAR_BR_BR_VID_MOTO_SCORE_BAIXO_PV_035.mp4
```

`MOTO` entra imediatamente depois de `FORMAT` somente quando a evidência visual do asset mostrar motocicletas como produto dominante. Para carro, o padrão permanece sem token adicional. `CAR` continua sendo a vertical/operação; `MOTO` é o subtipo visual do veículo.

Exemplos:

```text
CC_CA_FR_IMG_APPROBATION_NH_001.jpg
CC_CA_FR_IMG_WALLET_NH_001.png
CC_CA_FR_VID_SANS_VERIFICATION_PV_001.mp4
CC_US_ES_IMG_APROBACION_NV_001.jpg
CC_US_ES_VID_LIMITE_ALTO_PH_001.mp4
```
## Campos do nome

```text
Campo      | Regra
-----------|----------------------------------------------------------
VERTICAL   | Código da vertical: CC, CAR, EMP, JOB, APP, GAME etc.
COUNTRY    | País alvo: US, CA, MX, BR etc.
LANG       | Idioma do criativo: EN, ES, FR, DE, BR, PT etc.
FORMAT     | IMG ou VID
VEHICLE    | Opcional na vertical CAR: `MOTO` quando motocicleta for o produto dominante; omitido para carro
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
- Para vertical `CAR`, revisar o conteúdo real e registrar `vehicle_type=MOTO|CARRO`; usar `MOTO` no nome apenas quando a timeline/imagem provar motocicleta como produto dominante.
- `drive_id`, `page_id`, `meta_creative_id`, `origin_campaign_id` e origem ficam no inventário/metadados.

Regra MGS para português confirmada por Rodolfo em 2026-07-12:

```text
Código | Uso
-------|------------------------------------------------------------
BR     | Português do Brasil; padrão quando país=BR e o pedido diz apenas “Português”.
PT     | Português de Portugal; usar quando PORTUGUÊS-PT/PT-PT for explícito.
```

Exemplos: `CAR_BR_BR` e `GAME_BR_BR` são operações válidas. `CAR_BR_PT`/`GAME_BR_PT` representam conteúdo em português de Portugal direcionado ao país BR quando isso for explicitamente solicitado.
## Verticais

Códigos iniciais aceitos:

```text
Código | Vertical
-------|-------------------------
CC     | Credit Card / cartão de crédito
CAR    | Car / auto
EMP    | Employment / emprego
JOB    | Jobs / vagas
APP    | Apps
GAME   | Games
```

Se a vertical não for evidente, não inventar. Usar `UNKNOWN` no inventário e marcar para revisão antes de renomear para uso em campanha.
## FORMAT

```text
Código | Regra
-------|------------------------------------------------
IMG    | Imagem estática: jpg, jpeg, png, webp etc.
VID    | Vídeo/animação exportada como mp4/mov etc.
```

Nunca inferir `IMG` vs `VID` só pelo nome vindo do Canva. Validar pelo arquivo real, MIME type, extensão e/ou metadado técnico.
## ANGLE

`ANGLE` deve vir de dicionário controlado por operação/idioma.

Regras:

- Não inventar ângulo confiante sem evidência textual/visual.
- Se houver dúvida, usar `UNKNOWN` no plano de renomeação e preencher `notes`.
- Padronizar por idioma quando fizer sentido, mas manter comparabilidade operacional.

Exemplo inicial para CC em espanhol:

```text
ANGLE              | Significado operacional
-------------------|--------------------------------------------------
APROBACION          | Aprovação / pré-aprovação
SIN_VERIFICACION    | Sem verificação / baixa fricção
LIMITE_ALTO         | Limite alto
SIN_CREDITO         | Público sem crédito / histórico limitado
MAL_CREDITO         | Público com crédito ruim / negativado
CASHBACK            | Cashback / recompensas
RECOMPENSAS         | Benefícios, pontos, milhas
COMPARACION         | Escolha/comparativo entre cartões
WALLET              | Uso cotidiano, carteira, pagamento do dia a dia
URGENCIA            | Urgência, aprovação rápida, necessidade imediata
UNKNOWN             | Ângulo incerto; exige note
```

Exemplo inicial para CC em francês:

```text
ANGLE                | Significado operacional
---------------------|--------------------------------------------------
APPROBATION           | Aprovação / pré-aprovação
SANS_VERIFICATION     | Sem verificação / baixa fricção
LIMITE_HAUT           | Limite alto
CHOIX                 | Escolha/comparativo
WALLET                | Carteira / uso cotidiano
UNKNOWN               | Ângulo incerto; exige note
```
## P_ORIENT

`P_ORIENT` combina presença de pessoa + orientação visual. Regra executiva confirmada por Rodolfo em 2026-07-12: nomes finais usam somente quatro códigos; criativos square/feed 1:1 entram como horizontal/não vertical para fins de nomenclatura.

```text
Código | Pessoa     | Orientação
-------|------------|------------
PV     | PERSON     | VERTICAL/STORY
NV     | NO_PERSON  | VERTICAL/STORY
PH     | PERSON     | HORIZONTAL/NÃO VERTICAL
NH     | NO_PERSON  | HORIZONTAL/NÃO VERTICAL
```

Códigos não permitidos no nome final:

```text
PS, NS, PU, NU, UU, UNKNOWN
```

Mapeamento operacional:

```text
Código | Pessoa     | Formato visual      | Uso típico
-------|------------|---------------------|-------------------------
PV     | PERSON     | VERTICAL            | Story/Reels 9:16
NV     | NO_PERSON  | VERTICAL            | Story/Reels 9:16
PH     | PERSON     | SQUARE/HORIZONTAL   | Feed 1:1 ou landscape
NH     | NO_PERSON  | SQUARE/HORIZONTAL   | Feed 1:1 ou landscape
```

Se pessoa ou orientação não puderem ser determinados com segurança, marcar revisão no inventário em vez de criar nome final incorreto. Não usar código `UNKNOWN` no nome final.
## Orientation, placement e dimensões

Dimensão não entra no nome por padrão. Dimensão fica no inventário.

Mapeamento comum para Meta:

```text
Placement | Dimensão típica | Aspect ratio | Orientation
----------|-----------------|--------------|------------
FEED      | 1080x1080       | 1:1          | HORIZONTAL
STORY     | 1080x1920       | 9:16         | VERTICAL
LANDSCAPE | 1080x608        | ~16:9        | HORIZONTAL
UNKNOWN   | desconhecida     | desconhecido | REVIEW
```
## Status e ciclo de vida

Status não entra no nome. Status fica em pasta ou inventário.

Pastas/status recomendados:

```text
Status / Pasta       | Uso
---------------------|--------------------------------------------------
01_READY             | Pronto para teste/campanha
02_TESTING           | Em teste; também abriga subentregues enquanto o anúncio/campanha ainda puder entregar
03_TESTED            | Já testado; só volta ao pool com decisão expressa e `retest_eligible=true`
04_WINNERS           | Vencedores / bom desempenho com entrega individual relevante
05_REJECTED          | Reprovados / baixo desempenho com entrega individual relevante; exclusão técnica da campanha não basta
99_LEGACY            | Legado / arquivo histórico
00_REVIEW            | Revisão manual antes de uso
01_READY_CANDIDATE   | Candidato pronto após organização automática
```

A entrada operacional atual é `MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL`. Ela é uma fila temporária para arquivos enviados fora do Discord, especialmente IMG/VID acima de 10 MB. Depois que a versão limpa for validada no `01_READY` correto, mover o original para `99_LEGACY` sem deletar. `UPLOAD_CANVAS` não existe mais e aparece somente em referências históricas.
