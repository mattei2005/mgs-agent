# MGS OS — Matriz de Permissões e Autoridade

> Status: proposta canônica v0.1  
> Fonte-mãe: `context/company-os.md`  
> Regra: permissões reais continuam em `data/authorized-users.json`.

## Níveis de decisão

```text
Nível                 Descrição                                      Exemplo
-------------------- ---------------------------------------------- ------------------------------
Operacional           Execução dentro de playbook aprovado            REC/P1, artigo SEO, QA
Supervisão humana     Humano da área valida/coordena                  Raquel, Geizian, Kelly
Orquestração Zeus     Roteamento, auditoria, alerta, coordenação      autorização, incidente
CEO / Rodolfo         Decisão crítica/final                           budget, credencial, produção
```

## Matriz por ação

```text
Ação                                  Executor/proponente       Aprovação necessária
------------------------------------- ------------------------ ----------------------
Criar REC/P1                          Atena / Raquel           Playbook/Raquel
Editar REC/P1                          Atena / Raquel           Playbook/Raquel
Publicar WordPress editorial           Atena                    Regra editorial
Criar artigo SEO                       Atena / Raquel           Playbook/Raquel
Criar criativo                         Kelly / futuro agente    Kelly/gestor/Rodolfo
Subir campanha                         Gestor / Ares futuro     Geizian/Rodolfo
Alterar budget                         Gestor / Ares futuro     Rodolfo/Geizian
Configurar pixel                       Rodolfo/Tech             Rodolfo
Montar site WordPress                  Rodolfo/Tech             Rodolfo
Ajustar blocos AdOps                   Smart Bidding/gestor     Rodolfo/gestor
Fechamento financeiro                  Rodolfo                  Rodolfo
Autorizar usuário externo              Zeus                     Rodolfo confirmado
Alterar authorized-users.json           Zeus                     Rodolfo confirmado
Ler credencial do 1Password             Zeus/agente autorizado   Só uso interno; não exibir
Alterar script/cron produtivo           Zeus/Tech                Rodolfo se risco
Restart gateway em thread ativa         Zeus/Tech                Rodolfo se sensível
Remover/mover arquivo estrutural         Zeus/Tech                Rodolfo aprovado
Criar agente novo                       Zeus/Rodolfo             Rodolfo
```

## Segurança
Nunca expor segredos; credenciais vivem no 1Password; autorização externa exige confirmação do Rodolfo; acesso permanente é exceção; mudanças em produção devem ser pequenas, auditáveis e reversíveis.

## Níveis de acesso

```text
Nível        Uso
----------- -------------------------------------------------------------------
Full         Acesso permanente/equipe; exige decisão explícita de Rodolfo.
One-time     Acesso só para pedido atual; expira após uso.
Limited      Pode conversar/solicitar, mas não executar pipelines sensíveis.
Denied       Pedido negado.
```

## Escalonamento obrigatório
Dinheiro/budget, credenciais, acesso permanente, produção, remoção de dados/arquivos, política, agente novo ou risco jurídico/financeiro/reputacional/operacional.
