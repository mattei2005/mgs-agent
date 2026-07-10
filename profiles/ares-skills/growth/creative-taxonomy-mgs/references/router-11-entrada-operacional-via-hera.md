## Entrada operacional via Hera

Fluxo aprovado por Rodolfo para entrada de criativos novos:

- Gestores/Kelly enviam o criativo como anexo no Discord da Hera.
- A mensagem deve informar obrigatoriamente `PAIS`, `VERTICAL` e `LINGUA`.
- Hera não deve inventar esses campos; eles são fonte oficial vinda do gestor/Kelly.
- Se faltar qualquer campo obrigatório, Hera deve pedir correção antes de enviar para processamento.
- O nome original do arquivo pode ser livre/Canva; a nomenclatura oficial é gerada depois pelo Ares.
- Hera atua como porta de entrada e organização inicial; Ares atua no tratamento técnico, sanitização, classificação e nomenclatura de aquisição.
- Quando Hera receber um upload válido com `PAIS`, `VERTICAL`, `LINGUA` e anexo, ela deve fazer um único handoff mencionando o Ares (`<@1508864261504630925>`) com os campos estruturados e link/contexto do anexo/processamento.
- Quando Rodolfo pedir explicitamente para Ares acionar/pedir algo à Hera, Ares deve usar o **user mention real da Hera** (`<@1513006098133680290>`). Escrever `@Hera` em texto simples não acorda o bot nem garante leitura pelo gateway.
- Para evitar loop entre agentes, Hera não deve mencionar Ares para confirmações, agradecimentos, status sem ação ou mensagens sem anexo/campos obrigatórios; Ares não deve responder a confirmações da Hera. Depois que uma correção Drive/naming estiver validada e encerrada, thumbs-up, “confirmado”, “registrado”, “sem nova ação”, “status mantido”, “aguardando handoff”, “sem ação pendente”, “silêncio operacional” ou mensagens equivalentes da Hera exigem silêncio total, não uma nova resposta curta. Handoff parcial bloqueado não deve virar ping-pong: Ares só volta a responder se houver handoff final com links/metadata ou pedido humano novo.

Formato recomendado para envio no Discord da Hera:

```text
País: US
Vertical: CC
Língua: ES
[anexo]
```

Formato curto aceito:

```text
US | CC | ES
[anexo]
```

Pasta de entrada recomendada no Drive:

```text
MGS-CRIATIVOS/
└── CRIATIVOS_ENVIADOS/
    └── <VERTICAL>_<COUNTRY>_<LANG>/
        ├── KELLY/
        └── GESTORES/
```

Destino final canônico no Drive, no fluxo atual aprovado:

```text
MGS-CRIATIVOS/
└── <VERTICAL>_<COUNTRY>_<LANG>/
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

Regra importante: como `<VERTICAL>_<COUNTRY>_<LANG>` já contém idioma e a nomenclatura já contém `IMG|VID`, `ANGLE` e `P_ORIENT`, Hera/Ares **não devem criar subpastas intermediárias** como `STORY/EN/01_READY` no fluxo atual, salvo aprovação explícita. Placement/formato (`STORY`, `FEED`, `REELS`) deve ficar no inventário/handoff e ser inferido por dimensão, mas o arquivo final vai direto em `<OPERATION>/<IMG|VID>/01_READY` quando estiver pronto.

Depois da entrada, Ares deve preservar o original/inbox, criar cópia limpa, classificar por OCR/visão, aplicar o nome final e enviar a cópia tratada para as pastas operacionais já existentes. Criativos vindos de `UPLOAD_CANVAS` já tratados continuam como backlog/artefato existente e não devem ser confundidos com novos uploads via Hera.
