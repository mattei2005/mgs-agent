### Escopo por agente/thread antes de reportar pendências

Ao validar `git status` ou arquivos modificados durante revisão de Atena/Zeus/Ares/Hera, não cite alterações de outro agente como “observação” do assunto atual sem checar se pertencem a outra thread/fluxo. Exemplo validado: `data/ares/creative-inventory/upload-canvas-clean-copy-execution-report.csv` pertence à thread Ares `1508906079642456084` e não deve aparecer em report de reestruturação Atena/REC-P1. Transparência é boa, mas ruído cross-scope confunde o CEO.

