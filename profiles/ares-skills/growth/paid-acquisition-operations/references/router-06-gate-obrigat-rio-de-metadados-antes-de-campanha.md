## Gate obrigatório de metadados antes de campanha

Antes de usar qualquer criativo em campanha/teste, Ares deve validar metadados no VPS:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.png
```

Se retornar `clean: false`, limpar antes de usar:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
```

Usar o arquivo `.metadata-clean` como asset de campanha. Se a limpeza falhar ou o formato for incompatível, escalar para Zeus/Rodolfo antes de subir campanha com arquivo bruto.

Referências canônicas:

- `/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md`
- `/root/mgs-agent/logs/creative-metadata-sanitizer.jsonl`
