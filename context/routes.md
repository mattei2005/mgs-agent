# MGS OS — Rotas Operacionais

> Status: proposta canônica v0.2
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
Pedido/evento                          Dono primário          Agente        Escalação
-------------------------------------- ---------------------- ------------ ----------------------
Criar REC/P1                           Raquel / Content       Atena        Zeus se exceção/erro.
Editar/publicar conteúdo WordPress      Raquel / Content       Atena        Zeus se risco técnico.
Criar artigo SEO                        Raquel / Content       Atena        Zeus se prioridade conflita.
Montar/configurar site WordPress        Rodolfo / Tech         Zeus coord.  Rodolfo aprova.
Configurar pixel                         Rodolfo / Tech/Growth  Ares futuro  Rodolfo aprova.
Criar criativo estático                  Kelly / Creative       Kelly agent  Gestor/Rodolfo.
Criar vídeo                              Kelly / Creative       Kelly agent  Gestor/Rodolfo.
Subir campanha Facebook                  Gestor / Growth        Ares futuro  Geizian/Rodolfo.
Subir campanha Google                    Gestor / Growth        Ares futuro  Geizian/Rodolfo.
Subir campanha TikTok                    Gestor / Growth        Ares futuro  Geizian/Rodolfo.
Operar ChatPion/quiz/tráfego direto      Gestor / Growth        Ares futuro  Geizian/Rodolfo.
Enviar SMS                               Gestor / Growth        Ares futuro  Geizian/Rodolfo.
Analisar ROI campanha                    Growth + Revenue       Ares futuro  Zeus se anomalia.
Ajustar blocos/preço AdOps               Revenue / SmartBidding N/A          Rodolfo/gestor.
Aprovar site em rede                     Revenue / Rodolfo      Zeus coord.  Rodolfo.
Fechamento financeiro                    Rodolfo / Finance      Zeus report  Rodolfo.
Autorizar usuário externo                Rodolfo / Security     Zeus         Rodolfo confirma.
Alterar credencial/token                  Security / Rodolfo     Zeus         Rodolfo confirma.
Erro Hermes/VPS/agente                   Tech / Zeus            Zeus         Rodolfo se crítico.
Inventário/reorganização estrutural       Tech / Zeus            Zeus         Rodolfo aprova blocos.
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
