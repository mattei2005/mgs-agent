### Patch local `busy_input_mode` em gateway

Patch em `/root/.hermes/hermes-agent/gateway/run.py` que faz `busy_input_mode: queue` funcionar em gateway mode. Quando o Hermes for atualizado:
1. Verificar: `grep "PATCH (MGS Digital Corp)" /root/.hermes/hermes-agent/gateway/run.py`
2. Se não estiver: `patch -p1 < /root/mgs-agent/patches/hermes/busy_input_mode_queue_gateway.patch`
3. Restart: `systemctl restart zeus-gateway atena-gateway`

Issue upstream: https://github.com/NousResearch/hermes-agent/issues/14905

