# MGS OS — Rotas Operacionais

> Status: proposta canônica v0.3
> Fonte-mãe: `context/company-os.md`
> Base operacional: `context/company-current-operating-model.md`

## Regra padrão de roteamento

```text
Identificar assunto
→ identificar área
→ identificar dono humano/agente
→ consultar fonte de verdade
→ verificar permissão
→ executar, responder ou escalar
→ registrar se afetar produção, permissão, custo, credencial ou infra
```

## Rotas por tipo de pedido

```text
Pedido/evento                          Dono primário                  Agente        Escalação
-------------------------------------- ------------------------------ ------------ ----------------------
Criar REC/P1                           Raquel / Rodolfo / Content     Atena        Zeus se exceção/erro.
Editar/publicar conteúdo WordPress      Raquel / Rodolfo / Content     Atena        Zeus se risco técnico.
Criar artigo SEO                        Raquel / Rodolfo / Content     Atena        Zeus se prioridade conflita.
Montar/configurar site WordPress        Rodolfo / Tech                 Zeus apoio   Rodolfo aprova.
Configurar pixel Facebook/Google Ads    Rodolfo / Tech/Growth          Zeus apoio   Rodolfo aprova.
Criar criativo estático                 Kelly + Geizian / Creative     Hera         Rodolfo se padrão/ferramenta.
Criar/editar vídeo                      Kelly + Geizian / Creative     Hera         Rodolfo se padrão/ferramenta.
Organizar criativos Canva/Drive         Kelly + Geizian / Creative     Hera         Rodolfo se estrutura mudar.
Disponibilizar criativo aprovado ao Ares Kelly + Geizian / Creative     Hera         Ares usa em testes.
Criar/subir campanha Facebook Ads       Rodolfo + Geizian + gestores   Ares         Budget/risco escala Rodolfo.
Criar/subir campanha Google Ads         Rodolfo + Geizian + gestores   Ares         Budget/risco escala Rodolfo.
Criar/subir campanha TikTok Ads         Rodolfo + Geizian + gestores   Ares         Futuro; Rodolfo aprova.
Analisar ROI campanha                   Growth + Revenue + Finance     Ares         Zeus/Rodolfo se anomalia.
Configurar estratégia ChatPion/Messenger Rodolfo + Geizian + gestores   N/A          Sem Ares.
Configurar quiz + captura SMS/email      Rodolfo / Growth               N/A          Rodolfo.
Operar SMS Funnel                        Rodolfo / Growth               N/A          Rodolfo.
Ajustar blocos/preço AdOps              Revenue / SmartBidding         N/A          Rodolfo/Geizian/gestor.
Aprovar site em rede AdX/SmartBidding    Revenue / Rodolfo              Zeus apoio   Rodolfo.
Fechamento financeiro                   Rodolfo / Finance              Zeus report  Rodolfo.
Autorizar usuário externo               Rodolfo / Security             Zeus         Rodolfo confirma.
Alterar credencial/token                 Security / Rodolfo             Zeus         Rodolfo confirma.
Erro Hermes/VPS/agente                  Tech / Zeus                    Zeus         Rodolfo se crítico.
Inventário/reorganização estrutural      Tech / Zeus                    Zeus         Rodolfo aprova blocos.
```

## Content Operations

REC/P1, edição/publicação WordPress e artigos SEO pertencem à Atena. Se precisar intervenção manual, Rodolfo e Raquel cuidam.

Zeus só entra quando houver exceção, erro recorrente, risco técnico, usuário sem autorização ou conflito operacional.

## Tech / WordPress / Pixel

Montar/configurar site WordPress e configurar pixel de Facebook Ads/Google Ads continuam sob responsabilidade do Rodolfo. Zeus pode ajudar como apoio técnico/orquestrador quando Rodolfo solicitar ou quando houver problema operacional.

## Creative Operations — Hera

Tudo relacionado a criativos — criação, edição, vídeo, estático, organização e padrões — pertence à Hera.

```text
Comando humano principal       Kelly
Também podem pedir             Rodolfo, Geizian e gestores
Agente                         Hera
Área                           Creative Operations
```

Kelly é a responsável humana por criar criativos para os gestores. Geizian orienta e apoia. Rodolfo mantém decisão final sobre ferramentas, estrutura e padrões.

Fluxo Hera → Drive → Ares:

```text
1. Kelly, Rodolfo, Geizian ou gestor pede criativos.
2. Hera cria variações nos formatos necessários, ex.: feed e stories para Facebook/Instagram.
3. Kelly avalia/aprova o criativo.
4. Hera salva o criativo aprovado na pasta correta do Google Drive.
5. Ares acessa essa pasta para usar os criativos em testes de campanhas novas.
```

Regra: Ares e Hera podem ler e escrever nas pastas de criativos aprovados no Drive para conseguir gerenciar os criativos. Hera organiza/escreve os assets aprovados; Ares consome, organiza quando necessário e usa em campanhas/testes.

## Growth / Campaigns — Ares

Tudo relacionado a campanhas, independente do source, pertence ao Ares.

```text
Sources atuais                 Facebook Ads e Google Ads
Source futuro/potencial         TikTok Ads
Usuários previstos              Rodolfo, Geizian e gestores treinados
Agente                          Ares
Área                            Growth / Media Buying
```

Ares gerencia, cria, analisa e opera campanhas conforme permissão aprovada. Gestores entram depois de Ares estar testado, aprovado e depois de treinamento.

Limite: Ares não configura ChatPion/DigitalTrChat, SMS Funnel ou estrutura de quiz. Ares pode usar campanhas/estratégias resultantes desses fluxos, mas a configuração dessas estruturas fica com Rodolfo, Geizian e gestores conforme o caso.

## Gestores e rastreamento por UTM_medium

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

O `UTM_medium` carrega o código do gestor. Ele é usado para rastrear receita/lucro por gestor, site e campanha.

## Estratégia ChatPion / Messenger

ChatPion, no contexto MGS, significa o fluxo operacional baseado no dashboard `digitaltrchat.com` configurado pelo dev da Smart Bidding.

Responsabilidade: Ares não mexe no ChatPion/DigitalTrChat. O cadastro de usuários é feito por Rodolfo e Geizian. Os gestores acessam os usuários das verticais e fazem a configuração operacional e os fluxos descritos abaixo.

Fluxo resumido:

```text
1. Admin MGS entra no DigitalTrChat.
2. Cria usuários por site/vertical.
3. Gestor loga com o usuário da vertical.
4. Gestor conecta um segurador/perfil Facebook.
5. O segurador tem várias páginas Facebook conectadas.
6. Em Bot Manager, configura flows de mensagens.
7. Campanha roda no Facebook Ads com objetivo Messenger.
8. Usuário clica no anúncio e abre Messenger com mensagem JSON pré-definida.
9. Usuário entra no drip de até 28 mensagens nas primeiras 24h.
10. Depois segue para broadcast via Smart Bidding.
```

Broadcast:

```text
1. Página é cadastrada na dashboard da Smart Bidding.
2. Template de mensagens e horários é selecionado.
3. Após 24h do cadastro, usuário começa a receber broadcast.
4. Pode enviar até 12 mensagens por dia.
5. Cada mensagem pode ter texto, imagem, botão e/ou link para artigo/site MGS.
```

Observação: estratégia de bot/Messenger funciona para Facebook Ads, não para Google Ads.

## Estratégia tráfego direto / quiz / SMS

Outra estratégia de aquisição é tráfego direto via quiz e captura de SMS/email.

Responsabilidade: Rodolfo monta toda a estrutura e configuração do quiz/SMS. Ares não configura quiz nem SMS Funnel.

Fluxo atual:

```text
1. Campanha roda no Facebook Ads ou Google Ads.
2. Usuário clica no anúncio.
3. Usuário abre o quiz.
4. Usuário responde perguntas.
5. Usuário preenche nome, telefone e, se usado, email.
6. SMS Funnel envia SMS após alguns minutos.
7. SMS tem CTA e link.
8. Clique abre artigo/site MGS.
9. Receita vem da monetização do site.
```

Ferramenta atual de SMS: `SMS Funnel` (`app2.smsfunnel.com.br`).

## Revenue / AdOps / Smart Bidding

Ajustar blocos/preço AdOps e aprovar site em rede fazem parte da camada AdX/Smart Bidding.

Fluxo resumido para site novo:

```text
1. Rodolfo monta o site inteiro.
2. Site é enviado para aprovação na Smart Bidding/AdX.
3. URLs monetizáveis são enviadas para cadastro.
4. Smart Bidding configura blocos de anúncio no site.
5. Rodolfo configura pixel.
6. Rodolfo cria contas/campanhas em Facebook Ads ou Google Ads.
7. Campanhas iniciam conforme estratégia de tráfego.
```

## Escalar para Zeus

Escalar para Zeus quando houver:

- usuário externo sem autorização;
- risco de publicação errada;
- erro recorrente de agente;
- falha de cron/script;
- mudança em produção;
- custo/ROI anormal;
- budget sensível;
- credencial;
- dúvida de dono;
- conflito entre áreas;
- pedido fora do playbook.

## Escalar para Rodolfo

Escalar para Rodolfo quando houver:

- budget;
- credenciais;
- produção crítica;
- acesso permanente;
- agente novo;
- política operacional;
- fechamento financeiro;
- remoção/migração estrutural;
- risco jurídico, financeiro, reputacional ou operacional.

## Rotas por área

```text
Área                         Entrada comum                         Saída esperada
---------------------------- -------------------------------------- -----------------------------
Executive / Management        prioridade, decisão, conflito          decisão, direção, governança
Content Operations            pedido editorial/WordPress             conteúdo publicado/ajustado
Growth / Media Buying         campanha, tráfego, custo, ROI          campanha/análise/alerta
Creative Operations           pedido de asset                        criativo entregue
Revenue / AdOps               bloco, aprovação, regra, monetização   ajuste/alerta/relatório
Finance / BI                  fechamento, receita, custo             relatório/decisão financeira
Tech / WordPress / Infra      site, plugin, pixel, Hermes, VPS       ajuste técnico validado
Security / Access             acesso, token, dashboard, API          autorização/negação/audit log
```
