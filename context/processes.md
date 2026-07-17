# Processos e Fluxos de Trabalho — MGS

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Princípio

Processos MGS devem deixar claro:

1. quem executa;
2. quem aprova;
3. qual fonte de verdade consultar;
4. quando escalar para Rodolfo, Geizian ou Zeus;
5. qual agente participa e qual agente não participa.

---

## Fluxo de conteúdo — Atena / Raquel

### REC

```text
Etapa   Ação
------- -----------------------------------------------------------------------
1       Definir site, país, idioma, vertical e produto/tema.
2       Consultar dados do produto e fontes permitidas.
3       Gerar artigo seguindo template da vertical.
4       Gerar/selecionar imagem conforme playbook.
5       Publicar como rascunho ou publicar conforme permissão/playbook.
6       Revisão editorial por Raquel ou responsável.
7       Ajustar links, categorias, tags, SEO e imagem.
8       Publicar ao vivo quando aprovado.
9       Configurar/validar ligação REC -> P1 quando aplicável.
```

### P1

P1 é a página de continuação/conversão ligada ao REC.

```text
Característica                 Regra
------------------------------ ------------------------------------------------
Conteúdo                       Mais detalhado que REC.
Ligação                        Normalmente linkado a partir do REC.
CTA                            Leva ao destino final aprovado.
Pagination/interstitial         Pode gerar oportunidade adicional de impressão.
```

### REC + P1

Fluxo combinado que cria REC e P1 em sequência, configura a ligação entre eles e prepara a estrutura editorial/comercial.

### Artigo SEO

```text
Item                           Regra
------------------------------ ------------------------------------------------
Objetivo                       Preencher categoria, captar orgânico e apoiar site.
Tamanho                        Aproximadamente 1.200+ palavras quando aplicável.
CTA                            Não necessariamente leva ao produto final.
Pagination                     Normalmente não usa fluxo REC -> P1.
Supervisão                     Raquel / Content Operations.
```

### Escalonamento de conteúdo

```text
Situação                                  Escalar para
----------------------------------------- -----------------------------------
Erro técnico no WordPress                  Zeus/Rodolfo se produção.
Produto/link inconsistente                 Raquel; Rodolfo se risco.
Pedido fora do playbook                    Zeus/Rodolfo.
Usuário externo pedindo execução           Zeus para autorização.
Mudança estrutural em site/template        Rodolfo/Tech.
```

---

## Fluxo de campanha — Growth / Ares / gestores

Campanhas são executadas por gestores e, progressivamente, pelo Ares conforme escopo aprovado.

```text
Etapa   Ação
------- -----------------------------------------------------------------------
1       Definir site, vertical, país, público e canal.
2       Selecionar criativo aprovado no Google Drive.
3       Configurar campanha em Facebook Ads, Google Ads ou canal aprovado.
4       Aplicar tracking com `UTM_medium` do gestor.
5       Validar pixel/GTM/link/URL quando aplicável.
6       Definir budget dentro do escopo aprovado.
7       Lançar campanha.
8       Monitorar custo, receita, ROI e sinais de risco.
9       Pausar, ajustar ou escalar conforme performance.
10      Reportar anomalias para Geizian/Rodolfo.
```

Gestores e códigos:

```text
Gestor     Código UTM_medium
---------  -----------------
Icaro      g001
Geizian    g002
Isliago    g003
Joe        g004
Kelly      g005
Nicolas    g006
```

Geizian é sócio e também gestor operacional `g002`; ele sobe/testa campanhas e acompanha os gestores.

### Ares no processo de campanha

```text
Ares pode                         Ares não pode
-------------------------------- ------------------------------------------------
Criar/analisar campanhas          Configurar ChatPion/DigitalTrChat.
Gerenciar campanhas aprovadas      Montar/configurar quiz ou SMS Funnel.
Analisar ROI/performance           Alterar budget crítico sem escalar.
Usar assets aprovados do Drive     Mexer em pixel/site/tracking crítico sozinho.
Ler/escrever Drive de criativos    Alterar blocos AdOps/rede/parceiro.
```

Acesso ao Ares começa com Rodolfo + Geizian. Gestores entram depois de teste, aprovação e treinamento.

---

## Fluxo unificado de criativos e campanhas — Ares

Google Drive + inventário Ares são as fontes operacionais de assets; Meta/Google APIs vencem para estado real de campanha.

```text
Etapa   Ação
------- -----------------------------------------------------------------------
1       Usuário autorizado pede ou envia criativo ao Ares.
2       Creative Ops cria/trata/sanitiza/nomeia e registra original → tratado.
3       Kelly ou responsável aprova quando aplicável.
4       Ares salva no Drive e valida por readback.
5       Upload de gestor fica reservado e ares_eligible=false.
6       Campaign Ops concilia Drive × Meta antes de selecionar.
7       Ares reserva, executa dentro da autoridade e valida a plataforma.
8       Performance/ROI retornam ao inventário para orientar novas variações.
```

Regras:

- Kelly é pessoa humana/gestora `g005`, não agente.
- Creative Ops e Campaign Ops operam no mesmo agente e no mesmo estado; não existe handoff entre bots.
- `01_READY` significa pronto tecnicamente, não inédito.
- Original e tratado nunca competem como assets independentes sem decisão expressa.

## Fluxo ChatPion / DigitalTrChat — Messenger

ChatPion/DigitalTrChat é estratégia Facebook/Messenger usada principalmente com campanhas de objetivo MSG. No contexto MGS, o ChatPion operacional roda pelo dashboard `digitaltrchat.com`, configurado pelo dev da Smart Bidding.

Limite crítico: Ares não configura ChatPion/DigitalTrChat.

```text
Etapa   Ação
------- -----------------------------------------------------------------------
1       Admin MGS entra no DigitalTrChat.
2       Rodolfo/Geizian criam usuários por site/vertical quando necessário.
3       Gestor loga com o usuário da vertical/campanha.
4       Gestor conecta um segurador/perfil Facebook.
5       O segurador tem páginas Facebook conectadas.
6       Gestor configura flows em Bot Manager.
7       Campanha Facebook Ads usa objetivo Messenger/MSG.
8       Usuário clica no anúncio e abre Messenger com mensagem JSON.
9       Usuário entra no drip de mensagens nas primeiras 24h.
10      Depois pode seguir para broadcast via Smart Bidding.
11      Usuário clica e vai para site MGS monetizado.
12      Receita/performance é acompanhada por site/campanha/gestor.
```

Observação: estratégia de bot/Messenger funciona para Facebook Ads, não para Google Ads.

Escala para Rodolfo/Geizian quando envolver usuário novo, estrutura nova, risco de conta, mudança crítica ou problema de entrega.

---

## Fluxo Quiz + SMS / SMS Funnel

Quiz + SMS é estratégia separada de aquisição/reaproveitamento.

Responsabilidade: Rodolfo monta/configura a estrutura do quiz/SMS. Ares não configura quiz, SMS Funnel ou estrutura de SMS.

```text
Etapa   Ação
------- -----------------------------------------------------------------------
1       Rodolfo define estrutura do quiz, destino e coleta.
2       Campanha roda no Facebook Ads ou Google Ads.
3       Usuário clica no anúncio e abre o quiz.
4       Usuário responde perguntas.
5       Usuário preenche nome, telefone e, se usado, e-mail.
6       SMS Funnel envia SMS após alguns minutos quando aplicável.
7       SMS/CTA leva usuário para artigo/site/fluxo aprovado.
8       Receita vem da monetização do site.
9       Performance entra em análise de Growth/Finance.
```

---

## Fluxo de monetização — Smart Bidding / ActiveView

```text
Etapa   Ação
------- -----------------------------------------------------------------------
1       Site é criado/configurado em WordPress.
2       Conteúdo inicial é publicado.
3       Site é enviado/adicionado à rede parceira correta.
4       Parceiro cria/configura blocos na rede AdX/Ad Manager.
5       Rodolfo/Tech instala ou valida blocos no site.
6       Receita começa a aparecer em dashboard Smart Bidding ou ActiveView.
7       Google paga as parceiras; elas retiram revenue share e repassam a MGS.
8       Reports alimentam Finance / BI.
```

Regra atual:

```text
Smart Bidding   Parceiro Google/AdX/Ad Manager e dashboard principal/preferida.
ActiveView      Parceiro Google/AdX/Ad Manager; exceção ativa para openzed,
                cliquet e respectivos subdomínios.
```

Mudanças em blocos, rede, wrappers, precificação, tecnologia ou regras AdOps escalam para Rodolfo.

---

## Fluxo Finance / BI — Rodolfo

Finance / BI é responsabilidade do Rodolfo.

```text
Fonte / dado                   Uso
------------------------------ ------------------------------------------------
Smart Bidding reports           Receita/performance.
ActiveView reports              Receita/performance de sites ainda na AV.
Tráfego inválido                Risco e ajuste no fechamento.
Facebook Business Manager       Custo de mídia.
Google Ads                      Custo de mídia quando usado.
UTM_medium                      Atribuição por gestor.
Planilha financeira             ROI, lucro líquido, despesas, salários e comissões.
```

Rodolfo confere reports Smart Bidding/ActiveView, custos de mídia, tráfego inválido, comissões, salários e despesas. A planilha financeira validada por Rodolfo é a fonte final de ROI, lucro líquido, comissões e fechamento.

Comissão dos gestores:

```text
Base salarial                     R$ 3.000
Até R$ 100.000 lucro líquido       7% sobre lucro líquido
A partir de R$ 100.000             10% sobre lucro líquido
Regra                              Não soma salário + comissão; paga o maior valor.
```

---

## Fluxo Office / Follow-up — Ially

Ially é responsável por cobrança e acompanhamento de tarefas pendentes dos gestores quando necessário.

```text
Etapa   Ação
------- -----------------------------------------------------------------------
1       Tarefa/pedido fica pendente, atrasado ou sem retorno.
2       Ially cobra o gestor responsável.
3       Ially acompanha resposta/conclusão.
4       Se continuar pendente ou tiver impacto, escala para Geizian/Rodolfo.
```

---

## Comunicação interna

```text
Canal / sistema                 Uso
------------------------------- ------------------------------------------------
Discord                         Operação dos agentes e threads de trabalho.
#zeus-admin-agent                Zeus; controle padrão somente Rodolfo.
#atena-content-agent             Atena / Content Operations.
Ares                             Canal/thread unificado de criativos, campanhas e relatórios.
Google Drive                     Criativos aprovados.
Dashboards externos              Ads, monetização, ChatPion, SMS Funnel, reports.
```

Zeus só conversa diretamente com Rodolfo por padrão. Outras pessoas entram em threads do Zeus apenas se Rodolfo pedir explicitamente.

---

## Infraestrutura e credenciais

```text
Área                            Fonte / regra
------------------------------- ------------------------------------------------
Código MGS                      /root/mgs-agent
Repositório                     GitHub privado da MGS.
Credenciais                     1Password; nunca expor em chat.
Permissões operacionais          data/authorized-users.json
Logs/auditoria                  logs/events-audit.jsonl
```

Alterações em runtime, crons, scripts produtivos, permissões, credenciais, sites ou agentes exigem escopo claro, validação e aprovação quando houver risco.

---

## Regra de conflito entre processos

```text
Conflito                                      Vence
-------------------------------------------- ----------------------------------
Fala recente do Rodolfo vs processo antigo     Fala recente do Rodolfo.
Fonte operacional validada vs documento antigo Fonte operacional validada.
Ares vs ChatPion/quiz/SMS                       Ares não configura esses fluxos.
Kelly vs Ares                                   Kelly é dona humana criativa; Ares é agente unificado.
SB vs AV                                        SB é dashboard principal; AV só exceções.
Permissão real vs documentação                  data/authorized-users.json.
Credencial em qualquer lugar                    1Password.
```
