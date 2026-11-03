# Correção canônica — destino READY sem subpastas de placement

Sessão de origem: alinhamento Creative Ops/Campaign Ops/Kelly no teste do asset `CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4`.

## Aprendizado operacional

Quando Kelly/humano manda criativo com país, vertical e língua, o Ares deve detectar tipo/formato/ângulo/pessoa, limpar metadata, renomear e colocar no READY canônico da operação.

No fluxo comum, o destino permanente é o abaixo; uma entrega exclusiva explícita usa a pasta registrada do gestor. O Shared Drive é somente staging e paths MGS-AGENTS antigos permanecem namespace lógico/histórico. Consultar `flat-upload-intake.md`; não subir binários SA diretamente no My Drive. A correção preserva a regra sem subpastas de placement e não altera reservas.

O destino permanente para asset pronto é:

```text
MGS-ARQUIVO/CRIATIVOS/{VERTICAL}_{COUNTRY}_{LANG}/{IMG|VID}/{STATUS}/{FILENAME}
```

Exemplo validado:

```text
MGS-ARQUIVO/CRIATIVOS/CAR_US_EN/VID/01_READY/CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4
```

## O que não repetir

Não criar subpastas finais por placement/idioma:

```text
MGS-ARQUIVO/CRIATIVOS/CAR_US_EN/VID/STORY/EN/01_READY/...
```

`STORY`, `FEED`, `REELS`, idioma visível e dimensões ficam no inventário/handoff, não como caminho final por enquanto.

## Naming

Não colocar status no filename:

```text
Correto:   CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001.mp4
Incorreto: CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_READY_001.mp4
```

Motivo: status muda para `TESTING`, `TESTED`, `WINNER` ou `REJECTED`; se o status estiver no nome, o mesmo asset precisa ser renomeado a cada etapa. Status fica na pasta e/ou inventário.

## Verificação mínima após mover

Antes de responder “movido/validado”, confirmar:

```text
- file ID permanece o mesmo quando for move/rename de Drive.
- nome final é o esperado.
- parent atual é a pasta canônica `{OP}/{IMG|VID}/{STATUS}`.
- a subpasta incorreta `STORY/EN/01_READY` não contém mais o file ID.
- checksum/tamanho permanecem estáveis quando aplicável.
```
