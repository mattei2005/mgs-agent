# MGS OS — Matriz de Permissões e Autoridade

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`
> Regra: permissões reais continuam em `data/authorized-users.json`.

## Níveis de decisão

```text
Nível                 Descrição                                      Exemplo
-------------------- ---------------------------------------------- ------------------------------
Operacional           Execução dentro de playbook aprovado            REC/P1, artigo SEO, QA.
Supervisão humana     Humano da área valida/coordena                  Raquel, Geizian, Kelly.
Orquestração Zeus     Roteamento, auditoria, alerta, coordenação      autorização, incidente.
CEO / Rodolfo         Decisão crítica/final                           budget, credencial, produção.
```

## Matriz por ação

```text
Ação                                  Executor/proponente       Aprovação necessária
------------------------------------- ------------------------ ----------------------
Criar REC/P1                          Atena / Raquel           Playbook/Raquel.
Editar REC/P1                          Atena / Raquel           Playbook/Raquel.
Publicar WordPress editorial           Atena                    Regra editorial.
Criar artigo SEO                       Atena / Raquel           Playbook/Raquel.
Criar/tratar criativo                 Ares / Kelly humana      Kelly/gestor/Rodolfo.
Gerenciar criativo no Drive            Ares                     Escopo aprovado.
Reservar/conciliar Meta × Drive        Ares                     Antes de seleção/write.
Subir/gerenciar campanha               Ares / gestores          Autorização Ares vigente.
Alterar budget                         Ares / gestores          Rodolfo/Geizian.
Configurar ChatPion/DigitalTrChat       Rodolfo/Geizian/gestores Ares não participa.
Configurar quiz/SMS Funnel              Rodolfo                  Ares não participa.
Configurar pixel                       Rodolfo/Tech             Rodolfo.
Montar site WordPress                  Rodolfo/Tech             Rodolfo.
Analisar ROI                           Ares / Zeus report       Rodolfo/Geizian.
Cobrar tarefa pendente de gestor        Ially                    Geizian/Rodolfo se escalar.
Ajustar blocos AdOps                   Smart Bidding/gestor     Rodolfo/gestor.
Fechamento financeiro                  Rodolfo                  Rodolfo.
Autorizar usuário externo              Zeus                     Rodolfo confirmado.
Alterar authorized-users.json           Zeus                     Rodolfo confirmado.
Ler credencial do 1Password             Zeus/agente autorizado   Só uso interno; não exibir.
Alterar script/cron produtivo           Zeus/Tech                Rodolfo se risco.
Restart gateway/agente                  Zeus/Tech                Rodolfo se sensível/crítico.
Remover/mover arquivo estrutural         Zeus/Tech                Rodolfo aprovado.
Criar agente novo                       Zeus/Rodolfo             Rodolfo.
```

### Exceção ativa por operação

- **Eggbev-US-CC-EN-BOT / Eggbev-US-CC-EN-01-G006:** por decisão explícita de Rodolfo em 30/08/2026, Nicolas pode definir, reduzir ou aumentar budgets de campanha — inclusive a baseline de USD45 — sem nova aprovação do Rodolfo. Cada write continua exigindo instrução explícita do Nicolas ou política operacional aprovada, pré-leitura e readback Meta. A delegação não autoriza billing, `account_spend_limit`, credenciais nem escala automática sem regra própria aprovada.

## Segurança

Nunca expor senhas, tokens, application passwords ou qualquer credencial em texto claro no chat. Credenciais vivem no 1Password. Autorização externa exige confirmação do Rodolfo. Acesso permanente é exceção. Mudanças em produção devem ser pequenas, auditáveis e reversíveis.

## Níveis de acesso externo

```text
Nível        Uso
----------- -------------------------------------------------------------------
Full         Acesso permanente/equipe; exige decisão explícita de Rodolfo.
One-time     Acesso só para pedido atual; expira após uso.
Limited      Pode conversar/solicitar, mas não executar pipelines sensíveis.
Denied       Pedido negado.
```

## Escalonamento obrigatório

```text
Tema                                    Escalar para
-------------------------------------- ----------------------------------------
Dinheiro/budget                         Rodolfo/Geizian conforme área.
Credenciais/tokens/API                  Rodolfo.
Acesso permanente                       Rodolfo.
Produção crítica                        Rodolfo se risco relevante.
Remoção/migração estrutural             Rodolfo.
Política operacional                    Rodolfo.
Agente novo                             Rodolfo.
Risco jurídico/financeiro/reputacional  Rodolfo.
Erro crítico de agente/Hermes/VPS       Zeus reporta para Rodolfo.
```

## Regras de execução por Zeus

```text
Ação de Zeus                            Regra
-------------------------------------- ----------------------------------------
Responder status operacional             Pode consultar fontes e responder.
Autorizar/negar usuário                  Confirmar com Rodolfo antes de aplicar.
Editar JSON de permissões                Só após confirmação explícita.
Notificar agente afetado                 Após decisão aplicada.
Registrar audit log                      Obrigatório em autorização/incidente.
Ler credencial                           Apenas para uso interno operacional.
Exibir credencial                        Proibido.
Mudar runtime/prod                       Validar escopo; pedir aprovação se risco.
```
