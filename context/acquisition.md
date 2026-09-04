# Aquisição de Tráfego — MGS

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Princípio

Aquisição é a frente que compra ou direciona tráfego para sites MGS, mede performance por gestor/site/campanha e conecta campanha, criativo, tracking e monetização.

Ares pertence a esta área, mas com limite claro: Ares é agente de campanhas. Ele não configura ChatPion/DigitalTrChat, quiz, SMS Funnel ou estrutura de SMS.

---

## Canais de aquisição

```text
Canal / estratégia             Uso operacional
------------------------------ ------------------------------------------------
Facebook Ads                   Canal principal para campanhas de link click,
                               Messenger/MSG e outras estratégias aprovadas.
Google Ads                     Campanhas direcionadas principalmente para sites
                               MGS ou fluxos aprovados.
TikTok Ads                     Canal potencial/futuro para testes com Ares.
Tráfego direto                 Estratégia de envio direto para sites MGS.
ChatPion / Messenger           Estratégia Facebook/Messenger; não é escopo do Ares.
Quiz + SMS                     Estratégia montada/configurada por Rodolfo;
                               SMS Funnel pode ser usado para envio de SMS.
```

### Alocação ativa de tráfego direto

Desde 2026-08-25, `yolokfx.com` e `vizioid.com` estão alocados para tráfego direto da operação SHEIN, conforme decisão de Rodolfo.

Desde 2026-09-04, o intake de criativos dessa operação usa a pasta canônica `MGS-AGENTS/CRIATIVOS/SHEIN_US_EN` (Drive ID `1yV7Uge_KFN_Sih-iuVd7FY68cpfCUrxi`). Ao subir criativos de tráfego direto da SHEIN, o gestor deve informar `country=US`, `vertical=SHEIN`, `language=EN` e `strategy=tráfego direto`. O nome físico segue a ordem padrão `<VERTICAL>_<COUNTRY>_<LANG>`.

Para as landing pages desta operação, a fonte canônica é o plugin WordPress próprio `mgs-direct-quiz`:

- rota pública V2 por gestor: `/quiz/{pais}/sh2-gNNN/`;
- rota pública V1 por gestor: `/quiz/{pais}/sh1-gNNN/`;
- o número após `sh` corresponde ao modelo visual selecionado;
- modelos visuais configuráveis `V1` e `V2`;
- painel restrito a criar, editar e duplicar configurações de landing;
- desde 2026-09-01, WordPress funciona como plano de controle: cada landing ativa é publicada como `index.html` físico e o request público não inicializa WordPress/PHP;
- criar, editar ou ativar sincroniza o arquivo estático de forma atômica com readback; duplicar mantém a cópia sem rota física até a ativação; desativar retira a rota estática de forma reversível;
- CSS e JavaScript do HTML gerado devem usar HTTPS; o JavaScript preserva UTMs, `fbclid` e parâmetros personalizados exatamente uma vez;
- nenhuma coleta de lead, SMS, evento Facebook ou configuração de campanha no plugin;
- o clique apenas encaminha o visitante ao artigo configurado, preservando os parâmetros recebidos; o artigo de destino é responsável pelo evento Facebook;
- padrão de entrada: `utm_source=facebook`, `utm_medium=gNNN-s`, `utm_campaign=<id da campanha>` e `utm_adgroup=<id do conjunto>`, com campaign/adgroup definidos na criação da campanha de tráfego direto no Facebook, não no plugin.

Os canários G002 estão ativos nos dois sites:

- Yolokfx: `yolokfx.com/quiz/us/sh2-g002/` (V2) e `yolokfx.com/quiz/us/sh1-g002/` (V1);
- Vizioid: `vizioid.com/quiz/us/sh2-g002/` (V2) e `vizioid.com/quiz/us/sh1-g002/` (V1).

Em cada site, ambos os CTAs apontam para `/rec-us-app-shein-circle-of-style/` no próprio domínio.

Runtime validado: `mgs-direct-quiz` v1.1.1 nos dois sites, com as quatro rotas G002 entregues por arquivos estáticos e WordPress mantido apenas para edição, duplicação e publicação.

---

## Gestores e rastreamento

Cada gestor tem um código usado no `UTM_medium`. Esse código permite atribuir receita/lucro por gestor, site e campanha, inclusive quando vários gestores rodam o mesmo site.

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

Geizian tem duplo papel: é sócio/gestor operacional e também roda/testa campanhas como gestor `g002`.

Regra de tracking: `UTM_medium` deve carregar o código do gestor. Variações/sufixos operacionais podem existir em campanhas específicas, mas o código base do gestor precisa permanecer identificável.

---

## Facebook Ads

Facebook Ads é uma das principais fontes de aquisição da MGS.

Objetivos usados:

```text
Objetivo       Destino / uso
------------- ------------------------------------------------
Link clicks    Envia usuário direto para site MGS ou URL aprovada.
Messages/MSG   Envia usuário para Messenger, onde ChatPion/DigitalTrChat opera.
```

Operação típica:

1. Gestor escolhe site/vertical/campanha.
2. Gestor usa criativo aprovado no Google Drive.
3. Campanha recebe tracking com `UTM_medium` do gestor.
4. Usuário clica e entra no fluxo/site.
5. Receita é acompanhada por site/campanha/gestor.
6. ROI é acompanhado por gestor, Geizian e Rodolfo.

---

## Google Ads

Google Ads é usado para campanhas de aquisição, normalmente enviando direto para sites MGS ou fluxos aprovados.

Regra: custos, conversão, receita e ROI precisam ser reconciliados com as fontes de monetização e a planilha financeira.

---

## TikTok Ads

TikTok Ads é canal potencial/futuro para testes. Deve entrar no escopo do Ares apenas quando houver estrutura, criativos, tracking, budget e validação operacional aprovados.

---

## Ares — agente de campanhas

Ares é o agente de Growth / Media Buying.

```text
Escopo de Ares                  Status
------------------------------- ------------------------------------------------
Criar/analisar campanhas         Sim, conforme escopo aprovado.
Gerenciar campanhas              Sim, conforme permissão aprovada.
Analisar ROI/performance          Sim.
Usar criativos aprovados          Sim, via Google Drive.
Ler/escrever Drive de criativos   Sim, para organizar/usar assets de campanha.
Configurar ChatPion/DigitalTrChat Não.
Configurar quiz/SMS Funnel        Não.
Configurar estrutura SMS          Não.
Alterar budget crítico            Escala Rodolfo/Geizian.
```

Acesso humano ao Ares:

```text
Fase        Quem conversa com Ares
---------- ------------------------------------------------------------
Inicial     Rodolfo e Geizian.
Depois      Gestores treinados, após Ares estar aprovado, testado e
            com treinamento de uso concluído.
```

---

## Google Drive de criativos

O Google Drive de criativos aprovados é a fonte operacional para assets usados em campanhas.

Fluxo:

```text
1. Kelly/Rodolfo/Geizian/gestor pede ou envia criativo ao Ares.
2. Ares cria/trata, sanitiza, nomeia e inventaria.
3. Kelly/responsável aprova conforme o caso.
4. Ares salva no Drive, registra reserva/elegibilidade e concilia com a Meta antes do uso.
5. Ares acessa o Drive para usar/gerenciar assets em testes e campanhas.
6. Gestores também usam os assets aprovados nas campanhas.
```

---

## ChatPion / DigitalTrChat — Messenger

ChatPion/DigitalTrChat é estratégia de Messenger/Facebook usada com campanhas de objetivo MSG. No contexto MGS, o ChatPion operacional roda pelo dashboard `digitaltrchat.com`, configurado pelo dev da Smart Bidding.

Limite crítico: Ares não configura ChatPion/DigitalTrChat.

Responsabilidades:

```text
Parte                         Responsável
----------------------------- ------------------------------------------------
Cadastro de usuários           Rodolfo + Geizian.
Usuários por vertical           Rodolfo + Geizian.
Acesso aos usuários             Gestores conforme vertical/campanha.
Configuração operacional        Gestores.
Fluxos/bot/messages             Gestores conforme playbook e estrutura existente.
Broadcast Smart Bidding         Parceiro/estrutura Smart Bidding + gestores.
Escala/decisão crítica          Rodolfo/Geizian.
```

Fluxo típico:
```text
1. Admin MGS entra no DigitalTrChat.
2. Cria usuários por site/vertical.
3. Gestor loga com o usuário da vertical.
4. Gestor conecta um segurador/perfil Facebook.
5. O segurador tem várias páginas Facebook conectadas.
6. Em Bot Manager, configura flows de mensagens.
7. Campanha roda no Facebook Ads com objetivo Messenger/MSG.
8. Usuário clica no anúncio e abre Messenger com mensagem JSON pré-definida.
9. Usuário entra no drip de mensagens nas primeiras 24h.
10. Depois pode seguir para broadcast via Smart Bidding.
11. Usuário clica e vai para site MGS monetizado.
12. Receita/performance é acompanhada por site/campanha/gestor.
```

Observação: estratégia de bot/Messenger funciona para Facebook Ads, não para Google Ads.

---

## Quiz + SMS / SMS Funnel

Quiz + SMS é estratégia separada de aquisição/reaproveitamento. Pode capturar nome, telefone e, se usado, e-mail antes de enviar o usuário para destino aprovado.

Responsabilidade: Rodolfo monta/configura a estrutura do quiz/SMS. Ares não configura quiz nem SMS Funnel.

SMS Funnel é ferramenta externa usada para envio de SMS quando a estratégia exige.

Fluxo típico:
```text
1. Campanha roda no Facebook Ads ou Google Ads.
2. Usuário clica no anúncio.
3. Usuário abre o quiz.
4. Usuário responde perguntas.
5. Usuário preenche nome, telefone e, se usado, e-mail.
6. SMS Funnel envia SMS após alguns minutos.
7. SMS tem CTA e link.
8. Clique abre artigo/site MGS.
9. Receita vem da monetização do site.
```

---

## Operação típica do gestor

Gestores trabalham com:

- criação e acompanhamento de campanhas;
- uso de criativos aprovados;
- segmentação por país, idade, interesse, vertical e público;
- tracking com `UTM_medium` próprio;
- otimização de budget dentro de escopo aprovado;
- monitoramento diário de custo, receita e ROI;
- ajustes em criativos, públicos, campanhas e links conforme playbook;
- uso de ChatPion/DigitalTrChat quando a campanha for Messenger/MSG.

---

## Pixels e tracking

```text
Item                         Uso
---------------------------- ------------------------------------------------
GTM                          Google Tag Manager em sites conforme setup técnico.
Meta Pixel                   Pixel por vertical/site/campanha quando aplicável.
UTM_medium                   Código do gestor.
UTM propagation              Propagação de UTMs em WordPress/snippets quando aplicável.
pageview/session tracking     Anti-duplicação e controle de pageviews quando aplicável.
```

Alterações em pixels, GTM ou tracking crítico escalam para Rodolfo/Tech.

---

## Escalonamento

```text
Situação                                  Escalar para
----------------------------------------- -----------------------------------
Budget relevante ou risco financeiro       Rodolfo/Geizian
ROI anormal                                Rodolfo/Geizian
Pixel/GTM/tracking quebrado                Rodolfo/Tech
Credencial/dashboard externo               Rodolfo
Criativo sem aprovação                     Kelly/Rodolfo/Geizian
Uso de Ares por gestor ainda não treinado   Rodolfo/Geizian
ChatPion/quiz/SMS envolvendo Ares           Corrigir rota; Ares não configura
```
