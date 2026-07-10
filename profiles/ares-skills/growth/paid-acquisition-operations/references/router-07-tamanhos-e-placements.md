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
