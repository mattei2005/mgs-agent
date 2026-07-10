### Enviar arquivos grandes/anexos no Discord

Quando Rodolfo pedir “anexa aqui”, não responda apenas caminhos `MEDIA:/path` como texto esperando que o Discord converta se houver risco de truncamento ou múltiplos arquivos grandes. Para arquivos fonte/logs grandes, criar um pacote único em `/tmp` (`tar -czf /tmp/nome.tar.gz ...`) e colocar `MEDIA:/tmp/nome.tar.gz` sozinho/claramente na resposta final. Validar tamanho e conteúdo antes de responder. Se o envio anterior apareceu como texto no Discord, corrigir imediatamente com pacote único anexável.

