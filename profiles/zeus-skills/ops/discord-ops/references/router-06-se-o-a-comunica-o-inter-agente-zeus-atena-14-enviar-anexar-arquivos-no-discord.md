### Enviar/anexar arquivos no Discord

Quando Rodolfo pedir em linguagem natural “manda/envia/anexa esse arquivo”, entregar como **anexo nativo do Discord**, não como texto contendo `MEDIA:/path`. Pitfall validado: final response com `MEDIA:/root/.../title_generator.py` apareceu literalmente no chat. Use o caminho de envio que realmente faz upload; se necessário, copie para `/tmp`, gere uma variante `.txt` para source code e/ou `.tar.gz` com o original, envie para o target exato da thread e, se Rodolfo disser que não chegou, liste/valide o target antes de retry. Referência: `references/discord-file-attachments-and-thread-title-rename-2026-06-13.md`.

