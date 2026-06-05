# MGS OS — Rotas Operacionais

> Status: proposta canônica v0.1  
> Fonte-mãe: `context/company-os.md`

## Rotas por tipo de pedido

```text
Pedido/evento                          Dono primário          Agente        Escalação
-------------------------------------- ---------------------- ------------ ----------------------
Criar REC/P1                           Raquel / Content       Atena        Zeus se exceção/erro
Editar/publicar conteúdo WordPress      Raquel / Content       Atena        Zeus se risco técnico
Criar artigo SEO                        Raquel / Content       Atena        Zeus se prioridade conflita
Montar/configurar site WordPress        Rodolfo / Tech         Zeus coord.  Rodolfo aprova
Configurar pixel                         Rodolfo / Tech/Growth  Ares futuro  Rodolfo aprova
Criar criativo estático                  Kelly / Creative       Kelly agent  Gestor/Rodolfo
Criar vídeo                              Kelly / Creative       Kelly agent  Gestor/Rodolfo
Subir campanha Facebook                  Gestor / Growth        Ares futuro  Geizian/Rodolfo
Subir campanha Google                    Gestor / Growth        Ares futuro  Geizian/Rodolfo
Subir campanha TikTok                    Gestor / Growth        Ares futuro  Geizian/Rodolfo
Operar ChatPion/quiz/tráfego direto      Gestor / Growth        Ares futuro  Geizian/Rodolfo
Enviar SMS                               Gestor / Growth        Ares futuro  Geizian/Rodolfo
Analisar ROI campanha                    Growth + Revenue       Ares futuro  Zeus se anomalia
Ajustar blocos/preço AdOps               Revenue / SmartBidding N/A          Rodolfo/gestor
Aprovar site em rede                     Revenue / Rodolfo      Zeus coord.  Rodolfo
Fechamento financeiro                    Rodolfo / Finance      Zeus report  Rodolfo
Autorizar usuário externo                Rodolfo / Security     Zeus         Rodolfo confirma
Alterar credencial/token                  Security / Rodolfo     Zeus         Rodolfo confirma
Erro Hermes/VPS/agente                   Tech / Zeus            Zeus         Rodolfo se crítico
```

## Escalar para Zeus
Usuário externo sem autorização, risco de publicação errada, erro recorrente de agente, falha de cron/script, produção, custo/ROI anormal, budget sensível, credencial, dúvida de dono ou conflito entre áreas.

## Escalar para Rodolfo
Budget, credenciais, produção, acesso permanente, agente novo, política operacional, fechamento financeiro, remoção/migração estrutural ou risco crítico.

## Rota padrão
Identificar assunto → área → dono/agente → fonte de verdade → permissão → executar ou escalar → registrar se afetar produção, permissão, custo ou infra.
