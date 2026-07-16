# Controle de uploads externos no Shared Drive MGS

## Estado canônico

A única raiz operacional é o Shared Drive `MGS-AGENTS`:

```text
Drive ID: 0AEwt4Ye690ocUk9PVA
Admin Workspace: support@matteiservicesinc.com
MGS-AGENTS/CRIATIVOS/UPLOAD MANUAL
```

Nomes, paths e estrutura permanecem iguais aos validados no cutover. Arquivos enviados diretamente ao Shared Drive pertencem à organização, não ao uploader individual.

## Invariante operacional

Tudo dentro de `MGS-AGENTS/CRIATIVOS` deve ser operável pelo Ares sem autorização ou transferência de propriedade por arquivo. Kelly, Evo e outros colaboradores podem enviar para `UPLOAD MANUAL` como externos, sem licença Workspace adicional.

## Fluxo canônico

1. Confirmar `driveId=0AEwt4Ye690ocUk9PVA` e o parent esperado.
2. Consultar capabilities reais da identidade operacional do Ares.
3. Para tratar/mover: baixar o bruto, criar e validar a versão limpa em `01_READY`, mover o bruto para `99_LEGACY` e registrar inventário/linhagem.
4. Para copiar/manter: preservar o source conforme o pedido.
5. Em exclusão autorizada, validar lixeira ou `HTTP 404` por readback.
6. Se faltar capability dentro do Shared Drive, classificar como drift de infraestrutura/acesso e escalar; não pedir transferência de owner ao gestor.
7. Nunca trocar silenciosamente a identidade canônica do Ares pela conta do colaborador.

## Comunicação

- Não dizer que Kelly/Evo precisam transferir propriedade.
- Distinguir mover, lixeira, restauração e exclusão definitiva.
- Informar a operação tentada e o readback real.
