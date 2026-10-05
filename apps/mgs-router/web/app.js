'use strict';
const $ = id => document.getElementById(id);
let cfg = { revision: 0, routes: [], catalog: [], groups: [] }, csrf = '', editing = -1, editingDestination = '', editingGroup = '', groupScope = 'routes';
let domains = { revision: 0, domains: [], dns: {} }, routeAscending = true, destinationAscending = true;
const checks = new Map();
const PAGE_SIZE = 30, pages = {routes:1, destinations:1};
function paginate(scope,rows) { const totalPages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE)); pages[scope]=Math.max(1,Math.min(pages[scope],totalPages)); for(const position of ['', '-top']) { const prefix=scope+position; $(prefix+'-page').textContent=`Página ${pages[scope]} de ${totalPages}`; $(prefix+'-prev').disabled=pages[scope]<=1; $(prefix+'-next').disabled=pages[scope]>=totalPages; } return rows.slice((pages[scope]-1)*PAGE_SIZE,pages[scope]*PAGE_SIZE); }
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : 'success'; if ($('group-dialog').open) { $('group-message').textContent = text; $('group-message').className = error ? 'error' : 'success'; } }
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...(options.headers || {}) } });
  if (response.status === 401) { location.assign('/login'); throw new Error('Sessão expirada.'); }
  const value = await response.json(); if (!response.ok) throw new Error(value.error || 'Não foi possível concluir.'); return value;
}
function element(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
function button(text, action, cls = 'secondary') { const e = element('button', text, cls); e.type = 'button'; e.onclick = action; return e; }
function cell(row, text, cls) { const td = element('td', text, cls); row.append(td); return td; }
function emptyRow(parent, text, columns) { const row = element('tr'); const td = cell(row, text, 'empty'); td.colSpan = columns; parent.append(row); }
function switchView(view) {
  const keys = { rotas: 'routes', destinos: 'destinations', dominios: 'domains' }, active = keys[view] || 'routes';
  Object.values(keys).forEach(key => { $('view-' + key).hidden = key !== active; $('nav-' + key).classList.toggle('active', key === active); $('nav-' + key).setAttribute('aria-current', key === active ? 'page' : 'false'); });
}
[['routes','rotas'],['destinations','destinos'],['domains','dominios']].forEach(([id, hash]) => { $('nav-' + id).onclick = () => { location.hash = hash; switchView(hash); }; });
window.addEventListener('hashchange', () => switchView(location.hash.slice(1))); switchView(location.hash.slice(1));
function routeTargets(route) { if (route.response_status) return []; return route.destinations?.length ? route.destinations : [{ url: route.destination, weight: 100, destination_id: route.destination_id }]; }
function catalogByID(id) { return (cfg.catalog || []).find(d => d.id === id); }
function usage(id) { return cfg.routes.filter(r => routeTargets(r).some(t => t.destination_id === id)); }
function choices(select, options, label) { const value = select.value; select.replaceChildren(new Option(label, '')); options.forEach(([text, id]) => select.add(new Option(text, id))); select.value = value; }
function normalizeGroups(value) {
  if (value.group_schema !== 2) { const legacy = value.groups || []; value = {...value, group_schema:2, route_groups:[...legacy], destination_groups:[...legacy]}; delete value.groups; }
  return {...value, action_schema:1};
}
function groupKey() { return groupScope === 'routes' ? 'route_groups' : 'destination_groups'; }
function groupItems() { return groupScope === 'routes' ? cfg.routes : cfg.catalog || []; }
function updateGroups() {
  const route = (cfg.route_groups || []).slice().sort().map(g => [g,g]), landing = (cfg.destination_groups || []).slice().sort().map(g => [g,g]);
  choices($('route-group-filter'), route, 'Todos os grupos'); choices($('destination-group-filter'), landing, 'Todos os grupos');
  choices($('route-group'), route, 'Sem grupo'); choices($('catalog-group'), landing, 'Sem grupo');
}
function fillPicker(select, id = '') { choices(select, (cfg.catalog || []).slice().sort((a,b) => a.name.localeCompare(b.name, 'pt-BR', {numeric:true})).map(d => [`${d.name}${d.group ? ' · ' + d.group : ''}`, d.id]), 'URL manual'); select.value = id; }
function render() {
  const filter = $('domain').value, group = $('route-group-filter').value, query = $('search').value.toLowerCase(); $('routes').replaceChildren(); beginSelection('routes');
  const rows=cfg.routes.map((route,index) => ({route,index})).sort((a,b) => (routeAscending ? 1 : -1) * (a.route.name || a.route.path).localeCompare(b.route.name || b.route.path, 'pt-BR', {numeric:true})).filter(({route}) => {
    const targets = routeTargets(route), searchable = `${route.name || ''} ${route.group || ''} ${route.host}${route.path} ${targets.map(t => `${t.url} ${catalogByID(t.destination_id)?.name || ''}`).join(' ')}`;
    return (!filter || route.host === filter) && (!group || route.group === group) && searchable.toLowerCase().includes(query);
  });
  const count=rows.length; paginate('routes',rows).forEach(({route,index}) => {
    const targets=routeTargets(route); const row = element('tr', undefined, 'route'), source = `https://${route.host}${route.path}`;
    const nameCell = cell(row); nameCell.append(selectionBox('routes', routeKey(route), row), stateDot(route.disabled ? 'Desativada' : 'Ativa'), button(route.name || route.path, () => openEditor(index), 'text-link')); 
    cell(row, route.group || '—'); const link = element('a', source, 'path'); link.href = source; link.target = '_blank'; link.rel = 'noopener noreferrer'; cell(row).append(link);
    const details = element('details'), summary = element('summary', route.response_status ? 'Sem destino — HTTP 500 (Keitaro)' : targets.length === 1 ? (catalogByID(targets[0].destination_id)?.name || '1 destino') : `${targets.length} destinos`); details.append(summary);
    const total = targets.reduce((sum,t) => sum + t.weight, 0);
    targets.forEach(t => details.append(element('div', `${targets.length > 1 ? (route.relative_weights ? `Peso ${t.weight}/${total} — ` : `${t.weight}% — `) : ''}${t.url}`, 'destination'))); cell(row).append(details);
    const actions = element('div', undefined, 'actions'); const edit = button('Editar destino', () => openEditor(index));
    const copy = button('Copiar link', async () => { try { await navigator.clipboard.writeText(source); message('Link copiado.'); } catch { message('Não foi possível copiar pelo navegador.', true); } });
    actions.append(edit, copy); cell(row).append(actions); $('routes').append(row);
  });
  if (!count) emptyRow($('routes'), cfg.routes.length ? 'Nenhuma rota corresponde ao filtro.' : 'Nenhuma rota cadastrada. Comece em Nova rota.', 5);
  $('route-count').textContent = `${count} de ${cfg.routes.length} campanhas · até ${PAGE_SIZE} por página.`; finishSelection('routes');
}
function renderCatalog() {
  const query = $('destination-search').value.toLowerCase(), group = $('destination-group-filter').value; $('destinations').replaceChildren(); beginSelection('destinations');
  const rows=(cfg.catalog || []).slice().sort((a,b) => (destinationAscending ? 1 : -1) * a.name.localeCompare(b.name, 'pt-BR', {numeric:true})).filter(d => (!group || group===d.group) && `${d.name} ${d.url} ${d.group || ''} ${d.id}`.toLowerCase().includes(query));
  const count=rows.length; paginate('destinations',rows).forEach(d => {
    const row = element('tr'); const idCell=cell(row, undefined, 'hint'); idCell.append(selectionBox('destinations', d.id, row), element('span',d.id)); const nameCell=cell(row); nameCell.append(stateDot(d.disabled ? 'Desativada' : 'Ativa'),button(d.name, () => openDestination(d.id), 'text-link')); cell(row, d.group || '—'); const url = element('a', d.url, 'path'); url.href = d.url; url.target = '_blank'; url.rel = 'noopener noreferrer'; cell(row).append(url); cell(row, String(usage(d.id).length)); cell(row).append(button('Editar', () => openDestination(d.id))); $('destinations').append(row);
  });
  if (!count) emptyRow($('destinations'), 'Nenhum destino corresponde ao filtro.', 6);
  $('destination-count').textContent = `${count} de ${(cfg.catalog || []).length} Landing Pages cadastradas · até ${PAGE_SIZE} por página.`; finishSelection('destinations');
}
function renderGroups() {
  $('groups').replaceChildren(); beginSelection('groups'); (cfg[groupKey()] || []).slice().sort().forEach(g => {
    const row = element('tr'); const nameCell=cell(row); nameCell.append(selectionBox('groups',g,row),stateDot(groupState(g)),button(g, () => openGroup(g), 'text-link'));
    cell(row).append(button(String(groupItems().filter(item => item.group === g).length), () => {
      const isRoute = groupScope === 'routes'; $(isRoute ? 'route-group-filter' : 'destination-group-filter').value = g;
      pages[isRoute?'routes':'destinations']=1; isRoute ? render() : renderCatalog(); $('group-dialog').close();
    }, 'text-link'));
    const actions = cell(row); actions.append(button('Editar nome', () => openGroup(g)), button('Excluir grupo', () => deleteGroup(g), 'danger')); $('groups').append(row);
  });
  if (!cfg[groupKey()]?.length) emptyRow($('groups'), 'Nenhum grupo cadastrado.', 3); finishSelection('groups');
}
function showGroups(scope) {
  selected.groups.clear(); groupScope = scope; $('group-dialog-title').textContent = scope === 'routes' ? 'Grupos de Campanhas' : 'Grupos de Landing Pages';
  $('group-scope-hint').textContent = 'Grupos independentes. Alterações nesta área não afetam os grupos da outra área.';
  $('group-message').textContent = ''; openGroup(); renderGroups(); $('group-dialog').showModal();
}
$('route-groups').onclick = () => showGroups('routes'); $('destination-groups').onclick = () => showGroups('destinations');
$('close-groups').onclick = () => $('group-dialog').close();
function refresh() { updateGroups(); updateDomains(); render(); renderCatalog(); renderGroups(); }
async function saveConfig(next) { cfg = normalizeGroups(await api('/api/routes', { method: 'POST', body: JSON.stringify(next) })); refresh(); }
function showDNS(host) { $('dns-instructions').hidden = false; $('dns-host').textContent = `Domínio: ${host}`; const d = domains.dns; $('dns-record').textContent = `Tipo: ${d.type} | Nome: ${host} | Conteúdo: ${d.value} | TTL: ${d.ttl} | Proxy: ${d.proxy}`; $('dns-notice').textContent = d.notice; }
function updateDomains() {
  const selected = $('domain').value, hosts = [...new Set([...domains.domains, ...cfg.routes.map(r => r.host)])].sort();
  $('domain').replaceChildren(new Option('Todos os domínios', '')); hosts.forEach(d => $('domain').add(new Option(d, d))); $('domain').value = selected; $('domain-list').replaceChildren();
  hosts.forEach(host => {
    const row = element('article', undefined, 'domain-card'), info = element('div', undefined, 'route-info'), status = checks.get(host);
    info.append(element('strong', host), element('div', status ? `${status.verified ? 'Verificado' : 'Pendente'} — ${status.message}` : 'Ainda não verificado', status?.verified ? 'domain-status verified' : 'domain-status pending'));
    if (status?.checked_at) info.append(element('div', `Última verificação: ${new Date(status.checked_at).toLocaleString('pt-BR')} — resultado salvo; Verificar consulta online novamente.`, 'hint'));
    const actions = element('div', undefined, 'actions'), dns = button('Ver instruções DNS', () => showDNS(host));
    const verify = button('Verificar', async () => {
      verify.disabled = true; verify.textContent = 'Verificando…';
      try { const result = await api('/api/domains/check', { method: 'POST', body: JSON.stringify({ host }) }); if (result.host !== host || typeof result.verified !== 'boolean') throw new Error('Resposta de verificação não corresponde ao domínio.'); checks.set(host, result); updateDomains(); }
      catch (error) { message(error.message, true); verify.disabled = false; verify.textContent = 'Verificar'; }
    }, status?.verified ? 'verified' : 'secondary');
    actions.append(dns, verify); row.append(info, actions); $('domain-list').append(row);
  });
  if (!hosts.length) $('domain-list').append(element('p', 'Nenhum domínio cadastrado.', 'hint'));
}
$('domain-form').onsubmit = async event => {
  event.preventDefault(); $('add-domain').disabled = true;
  try { const added = $('new-domain').value.split(',').map(v => v.trim().toLowerCase()); if (added.some(v => !v)) throw new Error('Informe domínios válidos, sem itens vazios.'); const next = [...new Set([...domains.domains, ...cfg.routes.map(r => r.host), ...added])]; domains = await api('/api/domains', { method: 'POST', body: JSON.stringify({ revision: domains.revision, domains: next }) }); $('new-domain').value = ''; updateDomains(); showDNS(added[0]); message('Domínio cadastrado. Configure o DNS; nenhum DNS foi alterado automaticamente.'); }
  catch (error) { message(error.message, true); } finally { $('add-domain').disabled = false; }
};
function addTarget(url = '', weight = 50, id = '') {
  const relative = editing >= 0 && cfg.routes[editing]?.relative_weights;
  const row = element('div', undefined, 'target-row'), pickerLabel = element('label', 'Destino cadastrado'), picker = element('select'), uLabel = element('label', 'URL de destino'), u = element('input'), wLabel = element('label', relative ? 'Peso relativo original' : 'Percentual (%)'), w = element('input');
  picker.className = 'target-picker'; fillPicker(picker, id); picker.onchange = () => { const d = catalogByID(picker.value); if (d) u.value = d.url; u.readOnly = !!d; }; pickerLabel.append(picker);
  u.type = 'url'; u.className = 'target-url'; u.value = url; u.readOnly = !!id; u.placeholder = 'https://wantabrand.com/...'; w.type = 'number'; w.className = 'target-weight'; w.min = '1'; w.max = relative ? '1000000' : '100'; w.step = '1'; w.value = weight;
  u.required = w.required = $('weighted').checked; const remove = button('Remover da rota', () => row.remove()); uLabel.append(u); wLabel.append(w); row.append(pickerLabel, uLabel, wLabel, remove); $('targets').append(row);
}
function toggleWeighted() { const active = $('weighted').checked; $('weighted-destinations').hidden = !active; $('single-destination').hidden = active; $('destination').required = !active && !(editing >= 0 && cfg.routes[editing]?.response_status); document.querySelectorAll('.target-url,.target-weight').forEach(i => { i.required = active; }); if (active && !$('targets').children.length) { addTarget($('destination').value, 50, $('destination-picker').value); addTarget('', 50); } }
$('weighted').onchange = toggleWeighted; $('add-target').onclick = () => addTarget();
$('destination-picker').onchange = () => { const d = catalogByID($('destination-picker').value); if (d) $('destination').value = d.url; $('destination').readOnly = !!d; };
function openEditor(index = -1) {
  editing = index; const r = index >= 0 ? cfg.routes[index] : { host: $('domain').value, path: '', destination: '', name: '' };
  $('weight-notice').textContent = r.relative_weights ? 'Pesos originais relativos: a proporção é preservada sem arredondamento; a soma não precisa ser 100.' : 'A soma dos percentuais deve ser 100%.';
  $('query-notice').textContent = r.keitaro_query ? 'Modo Keitaro: somente macros UTM presentes são substituídas. URL fixa, fragmentos e macros ausentes permanecem como na origem; parâmetros extras não são acrescentados.' : 'UTMs e parâmetros recebidos são preservados. Macros UTM recebem os valores do link, sem duplicação. Domínio e caminho ficam fixos após o cadastro. Cadastre grupos no botão Grupos desta área.';
  $('route-enabled').checked = !r.disabled; $('host').value = r.host; $('path').value = r.path; $('route-name').value = r.name || ''; $('route-group').value = r.group || ''; $('destination').value = r.destination || ''; fillPicker($('destination-picker'), r.destination_id || ''); $('destination').readOnly = !!r.destination_id; $('host').readOnly = $('path').readOnly = index >= 0;
  $('targets').replaceChildren(); $('weighted').checked = !!r.destinations?.length; if (r.destinations) r.destinations.forEach(t => addTarget(t.url, t.weight, t.destination_id)); toggleWeighted();
  $('editor-title').textContent = index >= 0 ? 'Editar rota' : 'Nova rota'; $('editor').hidden = false; $('editor').scrollIntoView({block:'nearest'}); (index >= 0 ? $('route-name') : $('host')).focus();
}
$('new').onclick = () => openEditor(); $('cancel').onclick = () => { $('editor').hidden = true; }; $('search').oninput = $('domain').onchange = $('route-group-filter').onchange = () => {pages.routes=1;render();};
$('sort-routes').onclick = () => { routeAscending = !routeAscending; pages.routes=1;render(); };
$('route-form').onsubmit = async event => {
  event.preventDefault(); $('save').disabled = true;
  try {
    const old = editing >= 0 ? cfg.routes[editing] : {};
    const route = { host: $('host').value.trim().toLowerCase(), path: $('path').value.trim(), name: $('route-name').value.trim(), group: $('route-group').value, disabled: !$('route-enabled').checked };
    if (old.keitaro_query) route.keitaro_query = true;
    if ($('weighted').checked) {
      route.destinations = [...$('targets').children].map(row => ({ url: row.querySelector('.target-url').value.trim(), weight: Number(row.querySelector('.target-weight').value), destination_id: row.querySelector('.target-picker').value }));
      if (old.relative_weights) route.relative_weights = true;
      if (!route.destinations.length || route.destinations.some(t => !t.url || !Number.isInteger(t.weight) || t.weight < 1 || t.weight > (route.relative_weights ? 1000000 : 100)) || (!route.relative_weights && route.destinations.reduce((sum, t) => sum + t.weight, 0) !== 100)) throw new Error(route.relative_weights ? 'Informe pesos relativos inteiros positivos.' : 'Informe os destinos e percentuais inteiros com soma de 100%.');
    } else if (old.response_status && !$('destination').value.trim()) { route.response_status = old.response_status; }
    else { route.destination = $('destination').value.trim(); route.destination_id = $('destination-picker').value; }
    const routes = cfg.routes.map(r => ({ ...r })); if (editing >= 0) routes[editing] = route; else routes.push(route);
    await saveConfig({ ...cfg, routes }); $('editor').hidden = true; message('Rota salva e aplicada. O link público foi preservado.');
  } catch (error) { message(error.message + ' Se outro usuário alterou a configuração, recarregue antes de salvar.', true); } finally { $('save').disabled = false; }
};
function openDestination(id = '') {
  editingDestination = id; const d = catalogByID(id); $('destination-enabled').checked = !d?.disabled; $('destination-name').value = d?.name || ''; $('catalog-url').value = d?.url || ''; $('catalog-group').value = d?.group || ''; $('destination-impact').textContent = id ? `Usado em ${usage(id).length} rota(s). Alterar a URL atualiza todas essas rotas; será solicitada confirmação.` : 'Pode ser reutilizado nas rotas. Cadastrar não altera rotas existentes.'; $('destination-title').textContent = id ? 'Editar destino' : 'Novo destino'; $('destination-editor').hidden = false; $('destination-name').focus();
}
$('new-destination').onclick = () => openDestination(); $('cancel-destination').onclick = () => { $('destination-editor').hidden = true; }; $('destination-search').oninput = $('destination-group-filter').onchange = () => {pages.destinations=1;renderCatalog();};
$('sort-destinations').onclick = () => { destinationAscending = !destinationAscending;pages.destinations=1;renderCatalog(); };
$('destination-form').onsubmit = async event => {
  event.preventDefault(); $('save-destination').disabled = true;
  try {
    const old = catalogByID(editingDestination), d = { id: editingDestination || 'd-' + crypto.randomUUID(), name: $('destination-name').value.trim(), url: $('catalog-url').value.trim(), group: $('catalog-group').value, disabled: !$('destination-enabled').checked }, affected = old && old.url !== d.url ? usage(d.id).length : 0;
    if (old && !old.disabled && d.disabled && !window.confirm(`Desativar esta Landing Page? Ela deixa de receber tráfego em ${usage(d.id).length} campanha(s). As demais recebem proporcionalmente aos pesos; sem destino ativo, não haverá redirecionamento.`)) return;
    if (affected && !window.confirm(`Alterar esta URL atualizará ${affected} rota(s). Os links públicos e percentuais serão preservados. Confirma?`)) return;
    const catalog = (cfg.catalog || []).map(item => item.id === d.id ? d : item); if (!old) catalog.push(d);
    const routes = cfg.routes.map(r => { const next = {...r}; if (r.destination_id === d.id) next.destination = d.url; if (r.destinations) next.destinations = r.destinations.map(t => t.destination_id === d.id ? {...t, url:d.url} : {...t}); return next; });
    await saveConfig({...cfg, catalog, routes}); $('destination-editor').hidden = true; message('Destino salvo.' + (affected ? ` ${affected} rota(s) atualizada(s).` : ''));
  } catch (error) { message(error.message + ' Recarregue se a configuração foi alterada por outro usuário.', true); } finally { $('save-destination').disabled = false; }
};
async function deleteGroup(name) {
  const key = groupKey(), scope = groupScope;
  if (!cfg[key]?.includes(name)) { message('Grupo alterado por outro usuário. Recarregue antes de excluir.', true); return; }
  const count = groupItems().filter(item => item.group === name).length;
  if (!window.confirm(`Excluir o grupo “${name}” de ${scope === 'routes' ? 'Campanhas' : 'Landing Pages'}? ${count} item(s) ficarão sem grupo. Nenhuma rota, URL ou percentual será alterado. Os grupos da outra área permanecem intactos.`)) return;
  try {
    const next = {...cfg, [key]:cfg[key].filter(g => g !== name)};
    const itemsKey = scope === 'routes' ? 'routes' : 'catalog';
    next[itemsKey] = (cfg[itemsKey] || []).map(item => item.group === name ? {...item, group:''} : item);
    await saveConfig(next); if (editingGroup === name) openGroup();
    message('Grupo excluído somente desta área. Links, URLs e percentuais preservados.');
  } catch (error) { message(error.message + ' Recarregue antes de tentar novamente.', true); }
}
function openGroup(name = '') {
  editingGroup = name; $('group-name').value = name;
  $('group-editor-title').textContent = name ? 'Editar nome do grupo' : 'Criar grupo';
  $('save-group').textContent = name ? 'Salvar nome' : 'Criar grupo';
  $('cancel-group').hidden = $('group-impact').hidden = !name;
  $('group-impact').textContent = name ? `O novo nome será aplicado a ${groupItems().filter(item => item.group === name).length} item(s) somente desta área, sem mudar links, URLs ou percentuais.` : '';
  if (name) $('group-name').focus();
}
$('cancel-group').onclick = () => openGroup();
$('group-form').onsubmit = async event => {
  event.preventDefault(); $('save-group').disabled = true;
  try {
    const key = groupKey(), name = $('group-name').value.trim(), old = editingGroup;
    if (!name) throw new Error('Informe o nome do grupo.');
    if (cfg[key]?.includes(name) && name !== old) throw new Error('Já existe um grupo com esse nome nesta área.');
    if (old && !cfg[key]?.includes(old)) throw new Error('Grupo alterado por outro usuário. Recarregue antes de salvar.');
    if (old === name) { openGroup(); message('Nome mantido.'); return; }
    const next = {...cfg, [key]:old ? cfg[key].map(g => g === old ? name : g) : [...cfg[key],name]};
    const itemsKey = groupScope === 'routes' ? 'routes' : 'catalog';
    next[itemsKey] = (cfg[itemsKey] || []).map(item => old && item.group === old ? {...item,group:name} : item);
    const filters = groupScope === 'routes' ? ['route-group-filter','route-group'] : ['destination-group-filter','catalog-group'];
    const selected = filters.map(id => [id,$(id).value]);
    await saveConfig(next);
    if (old) { selected.forEach(([id,value]) => { if (value === old) $(id).value = name; }); render(); renderCatalog(); }
    openGroup(); message(old ? 'Nome do grupo atualizado somente desta área.' : 'Grupo criado.');
  } catch (error) { message(error.message, true); } finally { $('save-group').disabled = false; }
};
$('logout').onclick = async () => { try { await api('/logout', { method: 'POST', body: '{}' }); location.assign('/login'); } catch (error) { message(error.message, true); } };
(async () => { try { const me = await api('/api/me'); csrf = me.csrf; $('username').textContent = me.username; [cfg, domains] = await Promise.all([api('/api/routes'), api('/api/domains')]); cfg = normalizeGroups(cfg); Object.entries(domains.checks || {}).forEach(([host, result]) => { if (result.host === host && typeof result.verified === 'boolean') checks.set(host, result); }); refresh(); } catch (error) { message(error.message, true); } })();

// Bulk actions are metadata writes under the same configuration revision.
const selected = {routes:new Set(), destinations:new Set(), groups:new Set()};
const visible = {routes:new Set(), destinations:new Set(), groups:new Set()};
let bulkBusy = false;
function routeKey(route) { return route.host + '\n' + route.path; }
function stateDot(state) { const dot=element('span',undefined,'state-dot ' + (state==='Ativa' ? 'on' : state==='Desativada' ? 'off' : 'mixed')); dot.title=state; dot.setAttribute('aria-label',state); return dot; }
function groupState(name) { const rows=groupItems().filter(x=>x.group===name); if(!rows.length)return 'Sem itens'; return rows.every(x=>x.disabled) ? 'Desativada' : rows.every(x=>!x.disabled) ? 'Ativa' : 'Misto'; }
function beginSelection(scope) { visible[scope].clear(); }
function selectionBox(scope,id,row) {
  visible[scope].add(id); const box=element('input'); box.type='checkbox'; box.className='row-select'; box.dataset.selection=scope; box.dataset.key=id;
  box.setAttribute('aria-label','Selecionar ' + (scope==='routes' ? 'campanha' : scope==='destinations' ? 'Landing Page' : 'grupo') + ' ' + id.replace('\n',' '));
  box.checked=selected[scope].has(id); row.classList.toggle('selected-row',box.checked);
  box.onchange=()=>{ if(box.checked)selected[scope].add(id);else selected[scope].delete(id);row.classList.toggle('selected-row',box.checked);updateSelection(scope); };return box;
}
function finishSelection(scope) { for(const id of selected[scope])if(!visible[scope].has(id))selected[scope].delete(id);updateSelection(scope); }
function updateSelection(scope) {
  const count=selected[scope].size, all=$('select-all-'+scope);all.checked=!!visible[scope].size && count===visible[scope].size;all.indeterminate=count>0 && count<visible[scope].size;
  all.disabled=bulkBusy || !visible[scope].size; $('bulk-'+scope).hidden=!count;$('bulk-'+scope+'-count').textContent=count + ' selecionado(s)';
  document.querySelectorAll(`[data-bulk-scope="${scope}"]`).forEach(b=>b.disabled=bulkBusy);
}
for(const scope of ['routes','destinations','groups']) {
  $('select-all-'+scope).onchange=event=>{selected[scope].clear();if(event.target.checked)for(const id of visible[scope])selected[scope].add(id); if(scope==='routes')render();else if(scope==='destinations')renderCatalog();else renderGroups();};
}
function copiedName(name,existing) { const base=(name||'Sem nome').slice(0,265);let n=1,candidate;do{candidate=base+' (cópia'+(n===1?'':' '+n)+')';n++;}while(existing.has(candidate));existing.add(candidate);return candidate; }
function clonedRoute(route,routes,group) {
  const copy=JSON.parse(JSON.stringify(route)), keys=new Set(routes.map(routeKey));let n=1,path;
  do{path=route.path.slice(0,940)+'-copia'+(n===1?'':'-'+n);n++;}while(keys.has(route.host+'\n'+path));
  copy.path=path;copy.name=copiedName(route.name||route.path,new Set(routes.map(r=>r.name||r.path)));copy.disabled=true;if(group!==undefined)copy.group=group;return copy;
}
function clonedLanding(landing,group) { const copy={...landing,id:'d-'+crypto.randomUUID(),name:(landing.name.slice(0,285)+' (cópia)'),disabled:true};if(group!==undefined)copy.group=group;return copy; }
async function bulkAction(scope,action) {
  if(bulkBusy)return;const ids=new Set(selected[scope]);if(!ids.size)return;
  if(action==='clear'){selected[scope].clear();scope==='routes'?render():scope==='destinations'?renderCatalog():renderGroups();return;}
  const groupArea=groupScope, groupField=groupArea==='routes'?'route_groups':'destination_groups', itemsField=scope==='groups' ? (groupArea==='routes'?'routes':'catalog') : (scope==='routes'?'routes':'catalog');
  const items=(cfg[itemsField]||[]).filter(x=>scope==='groups'?ids.has(x.group):ids.has(scope==='routes'?routeKey(x):x.id));
  if(scope==='destinations' && action==='delete') {
    const used=items.filter(d=>usage(d.id).length);if(used.length){message(`Exclusão bloqueada: ${used.length} Landing Page(s) selecionada(s) são usadas por campanhas. Retire as referências antes de excluir. Nenhum item foi excluído.`,true);return;}
  }
  if(scope==='groups' && ['enable','disable'].includes(action) && !items.length){message('Os grupos selecionados estão vazios. Nenhum item foi alterado.');return;}
  const label=scope==='groups'?'grupo(s) de '+(groupArea==='routes'?'Campanhas':'Landing Pages'):scope==='routes'?'campanha(s)':'Landing Page(s)';
  const verb={delete:'Excluir',clone:'Clonar',enable:'Ativar',disable:'Desativar'}[action];if(!verb)return;
  let impact=action==='clone'?'As cópias serão criadas desativadas. Campanhas recebem novos caminhos; originais e pesos ficam intactos.':action==='delete'?(scope==='groups'?'Só os grupos serão removidos; os itens ficam sem grupo. Links, URLs, pesos e estados permanecem iguais.':'Os registros selecionados serão removidos do Router. Os arquivos dos sites e o DNS não serão alterados.'):(itemsField==='routes'?'Campanhas desativadas não redirecionam. Ativar restaura os destinos configurados.':'Landing Pages desativadas saem da distribuição. As demais recebem proporcionalmente aos pesos; sem destino ativo, a campanha não redireciona.');
  if(!window.confirm(`${verb} ${ids.size} ${label}? ${scope==='groups'?'Itens nesta área: '+items.length+'. ':''}${impact}`))return;
  bulkBusy=true;for(const key of Object.keys(selected))updateSelection(key);
  try {
    const next=JSON.parse(JSON.stringify(cfg));const chosen=x=>scope==='groups'?ids.has(x.group):ids.has(scope==='routes'?routeKey(x):x.id);
    if(action==='delete') {
      if(scope==='groups'){next[groupField]=next[groupField].filter(g=>!ids.has(g));next[itemsField]=(next[itemsField]||[]).map(x=>chosen(x)?{...x,group:''}:x);}
      else next[itemsField]=(next[itemsField]||[]).filter(x=>!chosen(x));
    } else if(action==='clone') {
      if(scope==='groups') {
        const names=new Set(next[groupField]);for(const name of ids) {
          const group=copiedName(name,names);next[groupField].push(group);
          for(const item of items.filter(x=>x.group===name))next[itemsField].push(itemsField==='routes'?clonedRoute(item,next.routes,group):clonedLanding(item,group));
        }
      } else for(const item of items)next[itemsField].push(scope==='routes'?clonedRoute(item,next.routes):clonedLanding(item));
    } else next[itemsField]=(next[itemsField]||[]).map(x=>chosen(x)?{...x,disabled:action==='disable'}:x);
    await saveConfig(next);selected[scope].clear();$('editor').hidden=true;$('destination-editor').hidden=true;editing=-1;editingDestination='';openGroup();refresh();
    message(`${verb}: ${ids.size} ${label} processado(s).`+(action==='clone'?' Cópias desativadas; originais preservados.':''));
  } catch(error) {message(error.message+' Nenhuma atualização parcial foi aplicada. Recarregue se outro usuário alterou a configuração.',true);}
  finally{bulkBusy=false;for(const key of Object.keys(selected))updateSelection(key);}
}
document.querySelectorAll('[data-bulk-action]').forEach(b=>b.onclick=()=>bulkAction(b.dataset.bulkScope,b.dataset.bulkAction));

for(const scope of ['routes','destinations']) for(const position of ['', '-top']) { const prefix=scope+position; $(prefix+'-prev').onclick=()=>{pages[scope]--;scope==='routes'?render():renderCatalog();}; $(prefix+'-next').onclick=()=>{pages[scope]++;scope==='routes'?render():renderCatalog();}; }
