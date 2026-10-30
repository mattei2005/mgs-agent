# t_0bb85547 — Isolamento sintético do transporte

## Problema, causa e solução
- Problema: o teste de HTTP 429 falhava antes do fake HTTP sob Ares.
- Causa comprovada: a fixture `act_100` não satisfazia o formato mínimo do guard real e o teste dependia da identidade/registry live. Baseline reproduzida com 1 falha e zero tentativas de rede externa (`baseline.json`, `baseline.txt`).
- Solução: somente `tests/test_shein_pipeline_hardening.py` foi alterado no código do repositório por esta tarefa. Fixture local usa conta sintética válida `111111`, JSON de escopo validado pelo loader real e provenance temporária. O guard real permanece ativo, com o predicado Ares fixado em True apenas na instância privada do teste. Nenhuma alteração do ambiente global para atravessar o guard.
- O teste HTTP verifica exatamente uma chamada fake, POST externo e filho POST, HTTP 429/código 4, estágio correto e substituição completa dos headers antigos pelos atuais; nenhum replay.
- Teste negativo separado cobre conta malformada, conta fora do escopo e filho fora do escopo, todos antes de qualquer HTTP. A regressão ampliada também executa os testes reais existentes de dependências e de escopo.

## Validação final no runtime existente
Runtime: `/root/.hermes/hermes-agent-port-main-3f2afed3-mgs-20261021/.venv/bin/python`.
- Teste isolado sob Ares: 1 passed (`targeted-final.json`).
- Harness original, `--suite`, sob Ares: 550 passed + 333 subtests, 42 arquivos (`original-final.json`).
- Ampliação com `test_ares_scope_campaign_dependencies.py` e `test_mgs_ares_asset_scope.py`, sob Ares: 571 passed + 348 subtests, 44 arquivos (`expanded-final.json`).
- Sem falhas, skips, exclusões ou módulos importados de origem incorreta; bloqueio externo ativo por audit hook e zero tentativas externas em todas essas execuções. Loopback liberado exclusivamente para os testes locais de renderer.
- Verificação adicional sob Zeus: os dois testes passam sem qualquer rede; ambiente global idêntico antes/depois e factory do guard restaurada (`isolation-zeus.json`).
- `git diff --check -- tests/test_shein_pipeline_hardening.py`: PASS.
- Todos os 41 arquivos da bateria do parent preservados. `test_shein_decision_wait.py` já apareceu no workspace compartilhado, fora das alterações desta tarefa, elevando a seleção original para 42. A execução final é um retrato dessa seleção atual; não representa teste de todo o repositório. Contagens anteriores menores estão preservadas, não substituídas artificialmente.
- Hashes confirmam transport/guard de produção e os dois arquivos do parent inalterados em relação ao início desta tarefa (`final-checks.json`). O patch próprio integral está em `tests.patch`, independente de autosnapshots Git.

## Limites e aprendizado
- Não foram operadas campanhas ou assumida `t_8f7a90a8`; nenhuma escrita Meta/Drive, token, grant, configuração, gateway ou runtime; nenhum pacote instalado. Alterações concorrentes do workspace não foram tocadas.
- Aprendizado persistido apenas na skill genérica própria `software-development-methods`, item 6 de Non-Negotiables: separar contrato HTTP de escopo, preservar guard e teste negativo, validar com identidade restrita/rede bloqueada. Readback via `skill_view` confirmou o conteúdo em `/root/.hermes/profiles/zeus/skills/software-development/software-development-methods/SKILL.md`.
- Sem mudança em scripts/config/data operacional ou infraestrutura estrutural. Alteração apenas em teste, evidência local em work e aprendizado genérico próprio; não houve REPORT-INFRA obrigatório por esses alvos.
- Um helper auxiliar de leitura via execute_code retornou `KeyError: content` pela forma do envelope da ferramenta; substituído por leitura/cópia local do harness, sem efeito no produto ou testes.
- Diagnóstico LSP de imports não resolvidos corresponde ao `sys.path` dinâmico do arquivo; execução real confirmou imports do diretório scripts. Header HTTPError usa agora `email.message.Message`, removendo o aviso de tipo desse argumento.

## Pendências
Nenhuma no escopo desta tarefa. Evidências locais não foram anexadas ao usuário, conforme a regra de comunicação.
