'use strict';

const fs = require('fs');
const childProcess = require('child_process');

const CONFIG_PATH = process.env.ARES_META_LIBRARY_PROXY_CONFIG || '/root/mgs-agent/data/ares/creative-ops/meta-library-proxy.json';
const LOCAL_SOCKS = 'socks5://127.0.0.1:1080';

function fieldMap(item) {
  const out = {};
  for (const field of item.fields || []) {
    const key = String(field.label || field.id || '').trim().toLowerCase();
    if (key) out[key] = String(field.value || '');
  }
  return out;
}

function browserEnv() {
  const clean = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (/(TOKEN|PASSWORD|SECRET|CREDENTIAL|DISCORD_BOT_TOKEN|OP_SERVICE_ACCOUNT_TOKEN)/i.test(key)) continue;
    clean[key] = value;
  }
  return clean;
}

function resolveDedicated(config) {
  const vault = process.env[config.vault_env || 'OP_DEFAULT_VAULT'] || config.vault_fallback;
  if (!vault || !config.item_id) throw new Error('Config residencial incompleta: vault/item_id ausente.');
  let item;
  try {
    const raw = childProcess.execFileSync('op', ['item', 'get', config.item_id, '--vault', vault, '--format', 'json'], {
      encoding: 'utf8', timeout: 20000, maxBuffer: 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe']
    });
    item = JSON.parse(raw);
  } catch (_) {
    throw new Error('Não foi possível resolver o proxy residencial no 1Password.');
  }
  const fields = fieldMap(item);
  const protocol = fields.protocol.trim().toLowerCase();
  const allowed = new Set(config.allowed_protocols || []);
  if (!allowed.has(protocol)) throw new Error('Protocolo do proxy residencial não permitido.');
  if (!fields.host || !/^\d{2,5}$/.test(fields.port) || !fields.username || !fields.credential) {
    throw new Error('Campos obrigatórios do proxy residencial ausentes no 1Password.');
  }
  const port = Number(fields.port);
  if (port < 1 || port > 65535) throw new Error('Porta do proxy residencial inválida.');
  return {
    mode: 'dedicated-us-residential',
    expectedCountry: config.expected_country || 'US',
    playwrightProxy: {
      server: `${protocol}://${fields.host}:${port}`,
      username: fields.username,
      password: fields.credential
    },
    browserEnv: browserEnv()
  };
}

function resolveProxyConfig() {
  const explicitServer = process.env.ARES_META_LIBRARY_PROXY || '';
  const explicitMode = process.env.ARES_META_LIBRARY_PROXY_MODE || '';
  if (explicitServer || explicitMode === 'windows-home-socks') {
    const server = explicitServer || LOCAL_SOCKS;
    if (server !== LOCAL_SOCKS) throw new Error('Fallback recusado: somente SOCKS local 127.0.0.1:1080.');
    return { mode: 'windows-home-socks', expectedCountry: 'US', playwrightProxy: { server }, browserEnv: browserEnv() };
  }
  if (explicitMode === 'direct-vps') throw new Error('Rota direct-vps proibida para o perfil Meta Library.');
  const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  if (config.direct_vps_allowed !== false) throw new Error('Config insegura: direct_vps_allowed deve ser false.');
  if (explicitMode && explicitMode !== config.mode) throw new Error('Modo de proxy não autorizado.');
  return resolveDedicated(config);
}

module.exports = { resolveProxyConfig };
