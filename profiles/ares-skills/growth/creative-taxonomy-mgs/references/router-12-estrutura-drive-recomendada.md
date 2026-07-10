## Estrutura Drive recomendada

Estrutura por operação, não por site:

```text
MGS-CRIATIVOS/
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

Para pipeline de backlog com placement/idioma como pastas intermediárias, usar quando aprovado:

```text
MGS-CRIATIVOS/<OPERATION>/<IMG|VID>/<FEED|STORY|LANDSCAPE|UNKNOWN>/<LANG>/<STATUS>/
```
