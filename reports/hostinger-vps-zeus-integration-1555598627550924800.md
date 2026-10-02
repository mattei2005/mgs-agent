# Hostinger VPS — integração Zeus

## Autoridade e alvo

- Rodolfo: configuração autorizada em `1555597320769372342`; token criado/salvo pelo usuário e bootstrap confirmado em `1555598627550924800`.
- Thread: `1555572634228490283`.
- API real confirmou VM `1767265`, hostname `srv1767265.hstgr.cloud`, estado `running`.

## Implantação

- Pacote oficial `hostinger-api-mcp@2.7.0`, instalado com dependências locais e lifecycle scripts desativados em `/root/.hermes/profiles/zeus/mcp/hostinger-vps`.
- Policy sem segredo: `data/hostinger-vps-zeus.json`.
- Launcher: `scripts/hostinger-vps-mcp-launch.py`, resolve token por IDs do 1Password e executa Node com ambiente mínimo, sem carregar outras chaves ou OP_SERVICE_ACCOUNT_TOKEN no processo Node.
- Catálogo local: `scripts/hostinger-vps-mcp-readonly.mjs`. Importa runtime/catálogo oficial sem modificar o pacote vendor e oferece apenas cinco operações GET com URL concretizada para VM1767265.
- As ferramentas oficiais search/execute/multi-execute não fazem, por si só, controle de privilégios por operação. A restrição existe no catálogo do servidor local; operações fora da lista não existem no mapa que executa requisições.
- MCP `hostinger-vps` adicionado somente ao config do Zeus, por `atomic_config_write`, com backup privado e readback sem diferença em qualquer chave preexistente; AdsPower preservado. Espelho `profiles/zeus-config.yaml` idêntico.
- Confiança untrusted; readOnlyHint aplicado às meta-tools somente dentro do servidor GET-only. Sem billing, domínios, firewall, restore, reboot ou stop expostos.
- Token permanece somente no 1Password e na memória do processo. Não foi copiado para .env, config, Git ou relatório. Privilégios nativos do token na Hostinger não foram demonstrados como read-only: a barreira verificada é a integração local.

## Validação real

- `work/hostinger-vps-1555598627550924800/smoke-result.json`: handshake MCP, cinco operações GET e identidade do alvo aprovados; negação de reboot/stop/restore/firewall/billing e de batch mutante; ID alternativo não redireciona a URL concreta.
- Consulta de backups retornou 2 registros na primeira página; consulta de ações retornou 15 registros na primeira página. Não são afirmados como totais sem percorrer paginação.
- Snapshot existente retornou campos id/created_at/expires_at/restore_time.
- Métricas retornaram cpu_usage, ram_usage, disk_space, incoming_traffic, outgoing_traffic e uptime.
- `standalone-probe-result.json`: probe executado por python3 resolve o Python ativo do Hermes e aprovou novamente as cinco leituras reais. Essa entrada é estável para diagnósticos e futuros consumidores cron autorizados.
- Gateway adotou a entrada por housekeeping nativo. Log do Zeus confirmou registro de `mcp__hostinger_vps__search`, `mcp__hostinger_vps__execute`, `mcp__hostinger_vps__multi_execute`. Processo Node do adapter observado como filho do gateway.
- O snapshot de ferramentas do turno em curso não é alterado retroativamente; a descoberta ao vivo existe no gateway e a entrada direta via probe está operacional.
- Falha inicial do smoke era incompatibilidade entre aliases camelCase de protocolo e atributos Pydantic do SDK Python instalado. Corrigida para is_error/read_only_hint e reexecução real aprovada.

## Limites, aprendizado e rollback

- Nenhum cron criado ou modificado; nenhuma política de monitor existente alterada.
- Nenhuma ação mutante na Hostinger, alteração de billing/firewall/credential ou restart solicitado por esta integração.
- Provider/API complementa Linux/SSH; atualizações e correções internas não são substituídas pelo MCP.
- Inventário de backup/snapshot não comprova restauração/recoverability: teste de restore requer outro escopo e confirmação crítica.
- Skill `hostinger-vps-operations` guarda operação, barreira GET-only, resolução de credenciais, CLI diagnóstico, aliases SDK e rollback não destrutivo.
- Rollback não destrutivo: desabilitar somente `mcp_servers.hostinger-vps.enabled` via native writer e readback; preservar AdsPower, pacote instalado e credencial 1Password. Excluir arquivos/revogar token exige confirmação própria.

## Governança

Inventário, audit log, registry e checkpoint acompanham o recibo final em `work/hostinger-vps-1555598627550924800/closure-result.json`; REPORT-INFRA enviado exclusivamente pelo helper canônico em embed silencioso e validado pela mensagem exata.
