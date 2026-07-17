# Equipe MGS

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Princípio

Este arquivo descreve a equipe humana, responsabilidades e acesso esperado aos agentes. Ele não concede permissão por si só: permissões executáveis continuam tendo como fonte de verdade `data/authorized-users.json`.

---

## Liderança / Executive

```text
Pessoa              Papel principal                         Observações
------------------ ---------------------------------------- ------------------------------------------------
Rodolfo Mattei      CEO / comando geral                     Estratégia, financeiro, WordPress, pixels,
                                                             arquitetura, Revenue/AdOps e comando da
                                                             operação dos agentes AI.
Geizian             Sócio / operação Growth                 Acompanha gestores, sobe/testa campanhas,
                                                             participa de Revenue/AdOps e apoia Kelly
                                                             na frente criativa.
Ially               Office / Follow-up                      Gerente do escritório; cobra e acompanha
                                                             tarefas pendentes dos gestores quando há
                                                             atraso ou falta de execução.
```

### Rodolfo Mattei

- CEO da MGS Digital Corp.
- Dono executivo da operação.
- Responsável por estratégia, financeiro, WordPress/infra, pixels, arquitetura operacional e Revenue/AdOps.
- Comanda a operação dos agentes AI como um todo.
- Único usuário padrão do Zeus.
- Discord ID: `344196393512075265`.

### Geizian

- Sócio do Rodolfo.
- Atua na operação de Growth / Media Buying e no acompanhamento dos gestores.
- Também sobe e testa campanhas como gestor operacional.
- Código de gestor: `g002`.
- Apoia Kelly na frente de criativos.
- Participa de Revenue/AdOps junto com Rodolfo e gestores.

### Ially

- Funcionária / gerente do escritório.
- Responsável por cobrar, acompanhar e dar follow-up em tarefas dos gestores quando solicitado ou quando houver atraso.
- Escala para Geizian/Rodolfo quando a pendência tiver impacto operacional, financeiro ou de prioridade.

---

## Content Operations

### Raquel Oliveira

- Responsável humana por Content Operations.
- Supervisiona Atena.
- Cuida de postagens, revisão, fluxo editorial, REC/P1, SEO editorial e WordPress editorial.
- Discord ID conhecido: `1496254952501280974`.
- Acesso permanente/full à Atena conforme autorização operacional.

---

## Growth / Media Buying — gestores

Gestores operam campanhas e rotinas de Growth/Revenue conforme escopo aprovado, acompanham custos/ROI e usam código próprio no `UTM_medium` para atribuição de receita/lucro por gestor, site e campanha.

```text
Gestor     Código UTM_medium    Observações
---------  -------------------  ------------------------------------------------
Icaro      g001                 Gestor de tráfego.
Geizian    g002                 Sócio e também gestor operacional; sobe/testa campanhas.
Isliago    g003                 Gestor de tráfego.
Joe        g004                 Gestor de tráfego.
Kelly      g005                 Gestora e responsável humana por criativos.
Nicolas    g006                 Gestor de tráfego.
```

Regra de atribuição: o `UTM_medium` carrega o código do gestor. Esse código é usado para medir receita/lucro por gestor, site e campanha, inclusive quando vários gestores rodam o mesmo site.

---

## Creative Operations

### Kelly

- Pessoa humana, não agente.
- Código de gestor: `g005`.
- Responsável humana pela criação de criativos para gestores.
- Também atua como gestora.
- Trabalha com Geizian/Rodolfo na frente criativa.
- No fluxo com Ares: pede/cria/avalia/aprova criativos; Ares pode criar, tratar, organizar, inventariar e conectar os assets às campanhas.

### Ares — Creative Operations

- Ares é o agente único de Creative Operations.
- Cria/organiza criativos, vídeos e assets conforme escopo aprovado.
- Lê/escreve no Drive, preserva linhagem original → tratado e controla reserva/elegibilidade.
- A mesma identidade conecta o asset a testes/campanhas, respeitando gates de write e budget.

## Agentes AI e acesso humano

```text
Agente   Área                     Acesso humano / supervisão
-------  -----------------------  ------------------------------------------------
Zeus     Executive / Management   Rodolfo somente por padrão. Outras pessoas só
                                  entram em thread do Zeus se Rodolfo pedir.
Atena    Content Operations       Raquel supervisiona e tem acesso operacional.
Ares     Creative Ops + Growth    Rodolfo, Geizian, Icaro, Isliago, Joe, Kelly e
                                  Nicolas, conforme registry e escopo.
```

Acesso humano esperado não substitui o registry operacional. Para acesso real, consultar `data/authorized-users.json`.

### Zeus

- General Manager / orquestrador / auditor.
- Controlado por Rodolfo.
- Outras pessoas da empresa só participam em thread de Zeus quando Rodolfo pedir explicitamente.

### Atena

- Agente de conteúdo.
- Atua em REC/P1, SEO, WordPress editorial, revisão e publicação conforme playbook.
- Supervisão humana: Raquel.

### Ares

- Agente unificado de Creative Operations + Growth / Media Buying.
- Acesso permanente: Rodolfo, Geizian, Icaro, Isliago, Joe, Kelly e Nicolas.
- Pode criar/tratar/inventariar criativos, gerenciar/analisar/criar/operar campanhas e produzir relatórios conforme escopo.
- Budget write continua subordinado à aprovação vigente de Rodolfo/Geizian.
- Não configura ChatPion/DigitalTrChat, quiz, SMS Funnel ou estrutura de SMS.

## Finance / BI relacionado à equipe

Comissões de gestores devem ser calculadas na planilha financeira do Rodolfo.

```text
Item                              Regra
--------------------------------- ------------------------------------------------
Base salarial                     R$ 3.000
Até R$ 100.000 de lucro líquido    7% sobre lucro líquido
A partir de R$ 100.000             10% sobre lucro líquido
Regra de pagamento                 Não soma salário + comissão; paga o maior valor.
Fonte de verdade                   Planilha financeira validada por Rodolfo.
```

---

## Registry canônico de permissões

```text
/root/mgs-agent/data/authorized-users.json
```

Esse JSON é a fonte de verdade para permissões executáveis de usuários/agentes. Este arquivo (`context/team.md`) descreve a equipe e o modelo esperado, mas não substitui o registry operacional.
