## Sanitização antes de campanha

Antes de usar criativo em campanha/teste, validar metadados:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.png
```

Se `clean: false`, limpar uma cópia:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
```

Usar o arquivo `.metadata-clean` como asset final. Não sanitizar RAW original in-place.
