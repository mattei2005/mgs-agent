# Fluxo de criação de campanhas SHEIN WEBSITE

**Escopo:** criação de campanhas Meta Ads para SHEIN WEBSITE nas contas cadastradas no fluxo do Hércules  
**Versão operacional descrita:** Production ExecMeta  
**Atualizado em:** 23/09/2026, Toronto

## 1. Objetivo do programa

O programa transforma um pedido comercial escrito no Discord em campanhas Meta criadas, conferidas e ativadas com segurança.

Ele foi desenhado para resolver quatro problemas ao mesmo tempo:

1. interpretar pedidos em linguagem natural sem exigir formulário técnico;
2. impedir que uma campanha seja criada na conta, página, pixel, landing ou tracking errados;
3. controlar o volume de chamadas à API da Meta para reduzir rate limit;
4. sobreviver a interrupções sem repetir uploads, campanhas, conjuntos ou anúncios.

A regra central é simples:

> A IA interpreta o pedido e explica o resultado. O programa determinístico controla validação, fila, capacidade, escrita, recuperação e read-back.

Isso evita que cada agente improvise um script, escolha um writer diferente ou faça chamadas extras “só para conferir”.

---

## 2. O que o fluxo aceita atualmente

O fluxo atual aceita pedidos de **1 a 12 campanhas** no mesmo post, desde que estejam dentro do contrato suportado:

- campanha WEBSITE;
- compra em leilão;
- orçamento no nível da campanha, CBO;
- estrutura fixa **1 campanha → 1 conjunto → 3 anúncios**;
- Cost Cap ou Bid Cap, nunca os dois no mesmo pedido;
- origem criativa na própria conta, em outra conta compatível ou em trio aprovado do Google Drive;
- ativação somente depois do QA e do read-back;
- conta de destino determinada pelo tópico do Discord.

Um pedido com mais de quatro campanhas continua sendo um único pedido comercial. Internamente, o programa o divide em operações filhas de até quatro campanhas. Depois, cada campanha é executada individualmente em um microbatch unitário.

Essa separação é importante:

- **pedido-pai:** representa a intenção e a aprovação do operador;
- **operação filha:** organiza grupos compatíveis e limita o tamanho operacional;
- **microbatch:** cria uma única árvore 1-1-3 por vez.

O operador não precisa dividir manualmente o pedido para atender à arquitetura interna.

---

## 3. Visão geral da arquitetura

```text
Pedido no tópico correto
        ↓
Interpretação pela IA
        ↓
Resolução do tópico e da conta destino
        ↓
Request fechado e vinculado à mensagem aprovada
        ↓
Preflight GET-only da Meta e, se necessário, do Drive
        ↓
Compilação offline + validação + certificação
        ↓
Fila durável serial
        ↓
Admissão de capacidade da conta
        ↓
Upload de uma unidade de mídia, quando necessário
        ↓
Criação de uma campanha PAUSED em microbatch unitário
        ↓
QA e read-back da árvore 1-1-3
        ↓
Próxima campanha
        ↓
Barreira global de QA
        ↓
Ativação serial
        ↓
Read-back terminal por IDs persistidos
        ↓
Fechamento no tópico original
```

O programa não considera “POST enviado” como sucesso. Sucesso só existe quando o estado final foi relido e validado.

---

## 4. Etapa a etapa

### 4.1. Recebimento e resolução da conta

Cada tópico cadastrado representa uma conta de destino. O programa resolve:

```text
thread_id do Discord → operação cadastrada → conta Meta destino
```

O texto do pedido não pode trocar silenciosamente a conta de destino. Quando outra conta aparece no texto, ela pode ser usada como fonte criativa, se o contrato permitir, mas não substitui a conta ligada ao tópico.

Antes de continuar, o programa também verifica:

- se a janela de manutenção está fechada;
- se a operação está ativa e pronta;
- se a conta está corretamente cadastrada;
- se Page, Instagram, pixel, evento, landing e padrão de nomes estão resolvidos.

### 4.2. Interpretação do pedido

A IA extrai do texto:

- produto;
- quantidade;
- budget por campanha;
- Cost Cap ou Bid Cap;
- data e horário em Toronto;
- referência criativa;
- referência técnica local, quando necessária;
- trio do Drive, quando aplicável;
- diretiva de copy, emoji ou ausência de texto;
- status final suportado.

Todos os números do pedido precisam ter destino único. Um número não pode ser ignorado nem reinterpretado livremente.

Quando todos os campos estão explícitos, o pedido pode seguir pelo caminho rápido. Quando existe ambiguidade, correção intermediária, copy especial ou outro gate definido, o sistema mostra uma confirmação fechada antes de executar.

### 4.3. Request imutável

O pedido aprovado vira um `request.json` de schema fechado, ligado a:

- mensagem de aprovação;
- aprovador autorizado;
- tópico original;
- operação destino;
- grupos de campanhas;
- budget, cap e início;
- escopo textual original.

Campos desconhecidos são recusados. O request não é reescrito silenciosamente durante a execução.

Essa imutabilidade evita que o significado comercial mude entre a aprovação e o write na Meta.

### 4.4. Preflight GET-only

Antes de qualquer POST, o programa lê o estado real da Meta para confirmar:

- campanha de referência correta;
- produto compatível;
- estrutura 1-1-3 íntegra;
- identidade correta;
- ausência de anúncios reprovados na referência;
- contrato WEBSITE;
- inventário de códigos e trackings já usados;
- inexistência de colisão.

Se a mídia vier do Drive, o programa também valida:

- pasta e seletores aprovados;
- tipo do arquivo;
- tamanho;
- MD5 remoto e SHA-256 local;
- thumbnail;
- produto associado;
- blocklist;
- ausência de conflito entre identidade, checksum e produto.

O writer da Meta não acessa o Drive. A mídia é coletada e validada antes, fica local e entra no writer somente com checksums aprovados.

### 4.5. Compilação e certificação offline

Com o request e as evidências live, o programa compila uma spec imutável.

Nesta fase ele define:

- códigos consecutivos sem preencher gaps antigos;
- tracking novo;
- nomes finais;
- Page e Instagram;
- pixel e evento;
- landing cadastrada;
- estratégia de lance;
- estrutura dos três anúncios;
- proveniência de cada criativo;
- operações filhas e microbatches.

A spec passa por self-test e certificação antes de entrar na fila. O writer usado é selecionado pelo registry de release. No estado descrito neste documento, a release de Production é **ExecMeta**.

Isso impede que uma operação nova use um script histórico ou uma versão escolhida manualmente.

### 4.6. Fila durável

Depois da validação, o pedido entra em uma fila persistida em disco.

A fila atual opera em modo **serial**. Ela mantém:

- ordem de entrada;
- estado de cada operação;
- tentativas;
- cooldowns;
- reserva de códigos e tracking;
- recibos enviados ao Discord;
- próxima tentativa permitida;
- vínculo com o manifesto da operação.

Se o processo do agente terminar, o pedido não desaparece. O drainer e o watchdog retomam a operação pelo estado persistido, sem depender de uma nova mensagem do operador.

### 4.7. Criação PAUSED em microbatch unitário

O writer cria no máximo uma árvore por invocação:

```text
1 campanha PAUSED
└── 1 conjunto
    ├── anúncio 1
    ├── anúncio 2
    └── anúncio 3
```

Depois de cada POST confirmado:

1. o ID retornado é persistido atomicamente;
2. o objeto é relido;
3. o shape é conferido;
4. a árvore permanece PAUSED;
5. o QA precisa passar antes de seguir para a próxima campanha.

O programa nunca cria todas as campanhas primeiro para conferir somente no final. A barreira por item reduz o raio de dano de um erro e cria pontos seguros de retomada.

### 4.8. QA global, ativação e fechamento

Quando todas as árvores previstas estão completas e aprovadas em PAUSED, o programa executa uma barreira global de QA.

Somente depois disso inicia a ativação serial. O read-back terminal confirma, por IDs persistidos:

- ownership correto;
- nomes e códigos;
- budget;
- cap e estratégia;
- data de início;
- contrato WEBSITE;
- pixel e evento;
- tracking;
- identidade;
- estrutura 1-1-3;
- estado final.

O pedido só fecha como concluído quando todas as campanhas esperadas chegam ao estado terminal validado.

---

## 5. Como reduzimos o rate limit

A redução do rate limit não veio de “esperar alguns segundos entre chamadas”. Ela veio da mudança da arquitetura para gastar chamadas somente quando existe capacidade reservada e um próximo passo seguro.

### 5.1. Uma única porta de criação

Antes, rotas paralelas, scripts pontuais e conferências repetidas podiam consultar a mesma conta mais de uma vez.

O desenho atual concentra novos pedidos em uma única porta e uma única release de Production. Isso elimina:

- writers concorrentes para a mesma classe de operação;
- inventários duplicados por ferramentas diferentes;
- retries não coordenados;
- fallback silencioso para scripts antigos;
- chamadas extras causadas por interpretações divergentes.

### 5.2. Fila serial e lock de writer

A configuração atual da fila é serial. Um lock exclusivo impede dois writers de criarem simultaneamente no mesmo espaço operacional.

Isso reduz picos de chamadas e, principalmente, impede que dois processos consumam a mesma janela de capacidade sem enxergar um ao outro.

Fila não é apenas espera. Ela é o mecanismo que garante ordem, ownership e retomada.

### 5.3. Capacidade controlada por conta

O controle local atual trabalha com:

- teto conhecido de **120 chamadas por 15 minutos por conta**;
- bucket conservador de **25 chamadas** quando a conta não está identificada;
- custo declarado de uma unidade por GET ou POST;
- reservas antes de iniciar uma fase.

Esses números são guardrails locais do programa, não uma promessa de capacidade da Meta. Um rate limit real devolvido pela Meta sempre prevalece sobre a estimativa local.

### 5.4. Reserva por fase, não para o pedido inteiro

O programa não exige que o ciclo completo de até 12 campanhas caiba de uma vez na janela.

Ele reserva capacidade para a próxima fase restart-safe:

- upload de uma unidade de mídia;
- criação e QA de uma árvore;
- ativação e read-back terminal.

Cada árvore usa uma reserva conservadora própria. No contrato atual, a criação de uma campanha trabalha com lease de **80 unidades**, sem ultrapassar o teto por conta.

A fase terminal usa os IDs já conhecidos e projeta **quatro chamadas por campanha**: QA fresco, ativação, leitura terminal e uma unidade de margem para repetição limitada de GET. A reserva final respeita o piso selado da operação e nunca pode ultrapassar o teto local.

### 5.5. Microbatch de uma campanha

Criar uma campanha por invocação reduz o risco de consumir a janela inteira antes de persistir o estado.

Ao final de cada unidade, o programa:

- grava os IDs;
- confirma PAUSED + QA;
- libera a capacidade;
- recalcula o que ainda falta;
- só então admite a próxima árvore.

Se a capacidade restante não comportar a próxima unidade, a operação entra em espera sem iniciar novos POSTs.

### 5.6. Deduplicação de mídia

Os vídeos são organizados em `media_units` pela primeira ocorrência do trio. Arquivos repetidos entre grupos são associados por aliases e não reenviados quando o hash ou o ID já está confirmado.

Cada invocação processa no máximo uma unidade de mídia. Uploads concluídos ficam persistidos e não voltam a compor a reserva das próximas fases.

Essa mudança reduz chamadas caras de upload e evita repetir polling de processamento de vídeo.

### 5.7. Persistência antes da próxima chamada

Cada ID, hash e status confirmado é salvo antes da próxima ação.

Por isso, uma retomada sabe exatamente:

- quais uploads já existem;
- quais objetos já foram criados;
- qual foi o último POST confirmado;
- se existe write em voo;
- se a resposta anterior ficou incerta;
- qual é o próximo passo permitido.

Sem essa persistência, a recuperação precisaria fazer varreduras amplas ou repetir writes, aumentando chamadas e risco de duplicação.

### 5.8. POST sem retry automático

POST não é repetido automaticamente.

Se houver timeout, resposta incerta, parcial ou rate limit depois de um write, o programa para novos writes e entra em recuperação por leitura.

Isso evita o pior padrão possível em automação Meta: repetir um POST porque o cliente não recebeu a resposta, mesmo quando a Meta pode ter criado o objeto.

### 5.9. Recovery por IDs, não por varredura ampla

Depois de uma interrupção, o programa usa os IDs persistidos para reler somente os objetos relevantes.

A recuperação é GET-only até determinar o estado real. O writer não reinicia do zero e não recria o que já foi confirmado.

No terminal, as leituras também são ID-scoped. Isso reduz páginas de inventário e chamadas desnecessárias na fase em que a conta já consumiu boa parte da janela.

### 5.10. Separação entre falta de capacidade e rate limit real

O sistema distingue dois estados:

#### Capacidade local insuficiente

`phase_capacity_unavailable` significa que a próxima fase não cabe com segurança na janela estimada.

Nesse caso:

- nenhum novo POST é iniciado;
- a operação fica em `WAITING`;
- o horário de retomada vem do manifesto;
- o pedido continua sendo o mesmo;
- não é comunicado como falha da Meta.

#### Rate limit real da Meta

Quando a Meta devolve rate limit:

- todos os novos writes param;
- o cooldown é persistido;
- o estado confirmado é preservado;
- a retomada respeita o horário calculado;
- o primeiro passo posterior é read-back;
- não se cria uma nova operação para contornar o bloqueio.

Essa distinção impede falsos diagnósticos e evita transformar uma espera preventiva em novas chamadas que causariam um rate limit verdadeiro.

### 5.11. Comunicação por mudança material

O Discord recebe mensagem apenas quando existe mudança relevante:

- pedido recebido;
- nova campanha criada e validada em PAUSED;
- nova tentativa que realmente recebeu rate limit;
- bloqueio que exige ação;
- fechamento terminal.

Ticks, polls internos, writer ocupado e estado sem mudança ficam silenciosos. Além de reduzir ruído, isso evita read-backs e reenvios desnecessários no próprio fluxo de entrega.

---

## 6. O que acontece em falhas

### Falha antes de qualquer write

O programa bloqueia sem criar objetos quando encontra, por exemplo:

- conta ou tópico inválido;
- operação não pronta;
- referência incompatível;
- anúncio reprovado na fonte;
- landing sem proveniência;
- colisão de código ou tracking;
- falta de capacidade;
- certificado ou release divergente.

### Falha depois de parte da criação

O programa preserva:

- campanhas e objetos já confirmados;
- IDs;
- status PAUSED;
- hashes de mídia;
- posição exata do pedido;
- informação sobre write incerto.

A operação continua no mesmo manifesto. Não nasce um “r1”, uma spec paralela ou outro writer apenas para tentar de novo.

### Rate limit somente no read-back final

Se todos os writes já foram confirmados e o rate limit ocorre somente na conferência terminal, o writer não é relançado.

O sistema espera o cooldown e executa recuperação estritamente GET-only pelos IDs conhecidos. Só depois disso marca PASS e publica o fechamento.

---

## 7. Por que esse desenho é mais seguro

O programa combina cinco propriedades:

1. **determinismo:** o mesmo request aprovado produz o mesmo contrato;
2. **idempotência operacional:** estado confirmado não é repetido;
3. **contenção:** uma campanha por microbatch e uma fase por reserva;
4. **recuperação:** falha não apaga o progresso nem exige adivinhar o estado;
5. **prova de conclusão:** sucesso depende de read-back, não de intenção ou log.

O ganho principal não é apenas diminuir respostas 429. É impedir que um rate limit cause duplicação, campanhas incompletas, ativações sem QA ou perda de rastreabilidade.

---

## 8. Resumo executivo

O fluxo atual funciona assim:

1. o pedido chega no tópico da conta;
2. a IA interpreta e fecha os campos comerciais;
3. o programa resolve conta, identidade e contrato;
4. faz preflight somente de leitura;
5. compila e certifica uma spec imutável;
6. coloca o pedido em fila durável serial;
7. reserva capacidade para a próxima fase;
8. cria uma campanha PAUSED por vez;
9. persiste cada ID antes de continuar;
10. executa QA por campanha e depois QA global;
11. ativa serialmente;
12. confirma tudo por read-back;
13. publica o resultado no tópico original.

A redução de rate limit veio principalmente de:

- uma porta única;
- fila serial;
- capacidade account-scoped;
- reservas por fase;
- microbatch unitário;
- mídia deduplicada;
- IDs persistidos;
- POST sem retry;
- recovery GET-only;
- read-back por IDs em vez de varreduras amplas.

Não há percentual de redução declarado neste documento porque isso exigiria uma série histórica comparável de chamadas, janelas e respostas 429 antes e depois. O que está documentado aqui é o mecanismo técnico atualmente usado para reduzir pressão sobre a API e limitar o impacto quando a Meta aplica rate limit.

---

## 9. Fontes canônicas consultadas

Este documento foi produzido a partir das fontes vivas do fluxo em 23/09/2026:

- skill `shein-website-ai-creation`;
- skill `shein-website-simple-creation`;
- mapa técnico `shein-website-simple-creation/references/file-map.md`;
- configuração `scripts/shein_dispatch_config.json`;
- configuração `scripts/meta_capacity_config.py`;
- registry `scripts/meta_campaign_release_registry.json`;
- orquestrador e fila canônicos da release ExecMeta.

Estado, limites e implementação podem mudar em nova release. Para operação real, a fonte viva e o registry vigente sempre prevalecem sobre este documento.