'use strict';
const $ = id => document.getElementById(id);
let cfg = { revision: 0, routes: [] }, csrf = '', editing = -1;
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : 'success'; }
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...(options.headers || {}) } });
  if (response.status === 401) { location.assign('/login'); throw new Error('Sessão expirada.'); }
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'Não foi possível concluir.');
  return value;
}
function element(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
function render() {
  const filter = $('domain').value, query = $('search').value.toLowerCase();
  $('routes').replaceChildren();
  cfg.routes.forEach((route, index) => {
    if ((filter && route.host !== filter) || !`${route.host}${route.path} ${route.destination}`.toLowerCase().includes(query)) return;
    const row = element('article', undefined, 'route');
    const info = element('div', undefined, 'route-info');
    const source = `https://${route.host}${route.path}`;
    info.append(element('strong', route.host), element('div', route.path, 'path'), element('div', route.destination, 'destination'));
    const actions = element('div', undefined, 'actions');
    const edit = element('button', 'Editar destino', 'secondary'); edit.onclick = () => openEditor(index);
    const copy = element('button', 'Copiar link', 'secondary'); copy.onclick = async () => { try { await navigator.clipboard.writeText(source); message('Link copiado.'); } catch { message('Não foi possível copiar pelo navegador.', true); } };
    const test = element('a', 'Testar', 'button secondary'); test.href = source; test.target = '_blank'; test.rel = 'noopener noreferrer';
    actions.append(edit, copy, test); row.append(info, actions); $('routes').append(row);
  });
  if (!$('routes').children.length) $('routes').append(element('div', cfg.routes.length ? 'Nenhuma rota corresponde ao filtro.' : 'Nenhuma rota cadastrada. Comece em Nova rota.', 'empty'));
}
function updateDomains() { const selected = $('domain').value; $('domain').replaceChildren(new Option('Todos os domínios', '')); [...new Set(cfg.routes.map(r => r.host))].sort().forEach(d => $('domain').add(new Option(d, d))); $('domain').value = selected; }
function openEditor(index = -1) { editing = index; const r = index >= 0 ? cfg.routes[index] : { host: $('domain').value, path: '', destination: '' }; $('host').value = r.host; $('path').value = r.path; $('destination').value = r.destination; $('host').readOnly = index >= 0; $('path').readOnly = index >= 0; $('editor-title').textContent = index >= 0 ? 'Editar destino' : 'Nova rota'; $('editor').hidden = false; (index >= 0 ? $('destination') : $('host')).focus(); }
$('new').onclick = () => openEditor(); $('cancel').onclick = () => { $('editor').hidden = true; }; $('search').oninput = render; $('domain').onchange = render;
$('route-form').onsubmit = async event => {
  event.preventDefault(); $('save').disabled = true;
  try {
    const route = { host: $('host').value.trim().toLowerCase(), path: $('path').value.trim(), destination: $('destination').value.trim() };
    const routes = cfg.routes.map(r => ({ ...r })); if (editing >= 0) routes[editing] = route; else routes.push(route);
    cfg = await api('/api/routes', { method: 'POST', body: JSON.stringify({ revision: cfg.revision, routes }) });
    $('editor').hidden = true; updateDomains(); render(); message('Rota salva e aplicada. O link público foi preservado.');
  } catch (error) { message(error.message + ' Se outro usuário alterou as rotas, recarregue a página antes de salvar.', true); }
  finally { $('save').disabled = false; }
};
$('logout').onclick = async () => { try { await api('/logout', { method: 'POST', body: '{}' }); location.assign('/login'); } catch (error) { message(error.message, true); } };
(async () => { try { const me = await api('/api/me'); csrf = me.csrf; $('username').textContent = me.username; cfg = await api('/api/routes'); updateDomains(); render(); } catch (error) { message(error.message, true); } })();
