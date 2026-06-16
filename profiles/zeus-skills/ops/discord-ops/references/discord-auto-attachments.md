# Discord/Hermes — anexos automáticos indesejados

## Sinal

Rodolfo reclama que o Zeus está mandando anexos/preview cards sem ter pedido, mesmo quando a resposta final não contém `MEDIA:`.

## Causa raiz validada

No Hermes Gateway, a pipeline de entrega executa `BasePlatformAdapter.extract_local_files()` antes de enviar ao Discord. Essa função detecta caminhos locais absolutos mencionados no texto final, por exemplo `/root/mgs-agent/context/mgs-os-map.md`, e se o arquivo existe e tem extensão entregável (`.md`, `.yaml`, `.json`, `.pdf`, etc.), o gateway remove o caminho do texto e envia o arquivo como anexo nativo.

Isso parece “anexo enviado pelo agente”, mas pode ser auto-detecção do gateway, não intenção explícita do modelo.

## Correção durável aplicada/esperada

Preferir desabilitar auto-anexo de caminhos locais nus para canais operacionais MGS:

- Config do perfil:
  - `gateway.auto_attach_local_files: false`
- Ponte runtime:
  - `gateway/run.py` deve exportar `HERMES_AUTO_ATTACH_LOCAL_FILES=0` quando essa opção estiver false.
- Guard no gateway:
  - `gateway/platforms/base.py` deve fazer `extract_local_files()` retornar `([], content)` quando `HERMES_AUTO_ATTACH_LOCAL_FILES` estiver false.

`MEDIA:/abs/path` continua sendo o mecanismo explícito para anexos quando Rodolfo pedir anexo.

## Verificação recomendada

Criar um arquivo `.md` temporário e testar `BasePlatformAdapter.extract_local_files()` com a env ligada/desligada:

- `HERMES_AUTO_ATTACH_LOCAL_FILES=1` → deve detectar o arquivo e remover o caminho do texto.
- `HERMES_AUTO_ATTACH_LOCAL_FILES=0` → deve retornar zero arquivos e preservar o caminho no texto.

Também verificar config live/versionado do Zeus:

- `/root/.hermes/profiles/zeus/config.yaml`
- `/root/mgs-agent/profiles/zeus-config.yaml`

Ambos devem conter `gateway.auto_attach_local_files: false`.

## Regra de estilo MGS

Para Rodolfo, anexos só devem ser enviados quando ele pedir explicitamente arquivo/anexo. Se ele disser “mostra por aqui/no chat”, entregar inline, sem arquivo.