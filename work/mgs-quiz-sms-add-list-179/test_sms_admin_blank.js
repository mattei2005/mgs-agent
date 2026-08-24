const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(__dirname + '/sms-admin-fixture.html', 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) throw new Error('admin script not found');
const button = { handler: null, addEventListener(type, fn) { if (type === 'click') this.handler = fn; }, click() { this.handler(); } };
const rows = [];
const grid = {
  appendChild(row) {
    const code = row.innerHTML.match(/name="sms_codes\[\]"[^>]*value="([^"]*)"/);
    const preset = row.innerHTML.match(/name="sms_preset_ids\[\]"[^>]*value="([^"]*)"/);
    if (!code || !preset) throw new Error('new fields missing');
    const input = {value: code[1], required: /required/.test(code[0]), focus() { this.focused = true; }};
    row._input = input;
    rows.push({code: input, preset_id: preset[1]});
  }
};
const document = {
  getElementById(id) { return id === 'mgsqSmsAdminGrid' ? grid : id === 'mgsqAddSmsList' ? button : null; },
  createElement() { return {className: '', innerHTML: '', querySelector() { return this._input; }}; }
};
vm.runInNewContext(scripts.join('\n'), {document});
button.click();
if (rows.length !== 1) throw new Error(`expected 1 new row, got ${rows.length}`);
if (rows[0].code.value !== '') throw new Error(`expected blank Gestor, got ${rows[0].code.value}`);
if (rows[0].preset_id !== '') throw new Error('expected blank internal preset id');
if (!rows[0].code.required || !rows[0].code.focused) throw new Error('Gestor is not required/focused');
console.log(JSON.stringify({new_rows: rows.length, gestor_blank: rows[0].code.value === '', preset_id_blank: rows[0].preset_id === '', required: rows[0].code.required, focused: rows[0].code.focused}));
