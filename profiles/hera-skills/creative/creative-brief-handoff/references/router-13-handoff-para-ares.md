## Handoff para Ares

Só prepare handoff para Ares quando Ares participar e houver material suficiente para campanha ou teste; por padrão esse handoff é interno/silencioso, não postagem pública na thread humana. Se o uso for humano, entregue um pacote de uso direto com o mesmo nível de organização.

### Regra de handoff silencioso Hera → Ares

Quando houver upload de criativo novo para tratamento pelo Ares, a Hera deve **aplicar diretamente** tudo que for regra de Operações Criativas antes de qualquer aviso: classificar o asset, detectar formato/ângulo/P_ORIENT, limpar metadata, nomear, colocar na pasta READY correta e registrar inventário/handoff local.

Ares **não é necessário** para aplicar regras de criativo, pasta, naming, metadata ou inventário. O Ares só precisa ser avisado por trás dos panos quando houver pacote válido para campanha/teste.

Regra de Discord/thread: se Kelly, Rodolfo ou outro humano pedir “avisa o Ares”, “manda para o Ares”, “deixa o Ares usar”, ou equivalente, a Hera **não deve postar o handoff para o Ares na thread atual** e não deve pedir confirmação pública. Deve fazer o aviso em modo silencioso/background quando houver mecanismo disponível, ou registrar a pendência local de aviso silencioso se o canal/tool estiver bloqueado. Na thread humana, responder apenas o status operacional do que a Hera fez.

É proibido gerar ping-pong Hera ↔ Ares na thread humana: não responder a confirmações do Ares, mensagens automáticas, erros de continuação, “recebido”, “validado read-only”, “sem ação” ou qualquer ruído de agente. Depois de entregar o status ao humano, silêncio até novo pedido humano.

Campos obrigatórios para upload válido:

```text
Campo       Regra
──────────  ─────────────────────────────────────────────
País        Obrigatório. Ex.: US, CA, MX, BR.
Vertical    Obrigatório. Ex.: CC, CAR, EMP, JOB, APP, GAME.
Língua      Obrigatório. Ex.: EN, ES, FR, PT.
Anexo       Obrigatório. Imagem/vídeo enviado no Discord.
```

Formatos aceitos do remetente:

```text
Completo    País: US / Vertical: CC / Língua: ES / [anexo]
Curto       US | CC | ES / [anexo]
```

Se faltar país, vertical, língua ou anexo, pedir correção ao remetente antes de processar; não inventar esses campos e não mencionar Ares. Handoff válido deve conter no mínimo: país, vertical, língua, origem/remetente e link/contexto do anexo.

Pacote mínimo:

```text
Asset/link:
Formato:
País:
Vertical:
Língua:
Origem/remetente:
Site/projeto:
Objetivo da campanha:
Ângulo criativo:
Copy principal:
CTA:
Status de aprovação:
Created_by:
Used_by:
Campaign_owner:
Observações/risco:
```

Se faltar algum item, declare como pendência. Se Ares não estiver envolvido, marque `used_by=HUMAN` ou `UNKNOWN` em vez de inventar handoff.

Exemplo:

```text
Handoff para Ares
─────────────────
Asset/link: [pendente — precisa Drive/Canva]
Formato: Meta feed 1080x1080
Site/projeto: openzed
Objetivo: teste inicial de ângulo benefício
Ângulo: aprovação simples / comparação
Copy principal: Compare options before choosing your next card.
CTA: Apply now
Status: precisa_revisao
Pendência: Kelly/Rodolfo aprovar visual final antes do Ares usar.
```
