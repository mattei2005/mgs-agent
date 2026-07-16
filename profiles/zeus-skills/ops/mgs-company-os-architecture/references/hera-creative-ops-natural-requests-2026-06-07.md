# Hera Creative Ops — pedidos naturais, Drive multivertical e Ares opcional (2026-06-07)

## Contexto

Durante o alinhamento da Hera, Rodolfo corrigiu três pontos importantes:

1. Hera é dona de **Creative Operations**: cria criativos estáticos (imagem) e vídeos, além de organizar assets.
2. Pedidos de criativo não devem virar formulário técnico. Kelly, Geizian, gestores e Rodolfo devem pedir naturalmente; a Hera infere o que for seguro e pergunta só o que bloquear.
3. O Drive `MGS-CRIATIVOS` tem várias verticais. `CC_US_ES` é exemplo/piloto alinhado com Ares, não a única operação.

## Regra operacional da Hera

```text
Pedido natural
→ Hera entende intenção
→ identifica vertical/operação correta
→ cria ou organiza o criativo
→ coloca/propõe pasta correta no Drive
→ registra origem/uso no inventário
→ aprimora skill com padrões reais do canal
```

## Ares é consumidor opcional

Hera não deve parecer assistente do Ares. Ares consome assets quando a campanha passa por ele, mas Kelly, Geizian ou gestores podem criar/subir campanha por conta própria.

```text
Hera          cria, recebe, classifica, nomeia, inventaria e organiza criativos.
Ares          usa criativos quando o fluxo de campanha passar pelo agente.
Humanos       podem criar/usar criativos diretamente, com Drive/naming organizado.
Zeus          governa, audita e evita conflito entre padrões.
```

Inventário deve registrar origem e uso:

```text
created_by       HERA / KELLY / GEIZIAN / GESTOR / UNKNOWN
requested_by     solicitante, quando houver
used_by          ARES / HUMAN / UNKNOWN
campaign_owner   Ares, Kelly, Geizian, gestor específico ou UNKNOWN
source           HERA_GENERATED / CANVA / HUMAN_UPLOAD
```

## Drive e taxonomia

Modelo geral multivertical:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

`CC_US_ES` é exemplo/piloto:

```text
CC_US_ES_IMG_APROBACION_PS_01.jpg
```

A pasta raiz informada por Rodolfo para esse fluxo é:

```text
MGS-AGENTS/CRIATIVOS
https://drive.google.com/drive/folders/0AEwt4Ye690ocUk9PVA
Workspace admin: support@matteiservicesinc.com
```

## Como atualizar Hera quando esse padrão aparecer

Ao alinhar Hera ou outro agente Creative Ops:

1. Não criar formulário obrigatório de pedido.
2. Descrever campos de brief como guia interno, não exigência para usuário.
3. Registrar que o agente pergunta só o mínimo bloqueante.
4. Generalizar Drive para múltiplas verticais/operações.
5. Tratar operação específica (ex: `CC_US_ES`) como piloto/exemplo, não regra única.
6. Registrar que humanos podem usar assets sem Ares.
7. Validar live/versioned SOUL e skill idênticos.
8. Reiniciar gateway do agente após alteração de SOUL/skill live.
9. Registrar audit log e confirmar serviço conectado.

## Pitfall

Não alinhar Hera demais ao Ares. A frase correta é:

```text
Hera organiza Creative Ops. Ares é um consumidor possível dos assets.
```

Não:

```text
Hera prepara criativos para o Ares.
```

A segunda frase é parcialmente verdadeira, mas reduz o escopo da Hera e conflita com o fluxo real da MGS.
