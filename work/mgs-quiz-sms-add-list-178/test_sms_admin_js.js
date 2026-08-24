const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(__dirname + '/sms-admin-fixture.html', 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!scripts.length) throw new Error('admin script not found');
const inputs = ['G001','G002','G003','G004','G005','G006'].map(value => ({value}));
const button = {
  handler: null,
  addEventListener(type, fn) { if (type === 'click') this.handler = fn; },
  click() { if (!this.handler) throw new Error('click handler missing'); this.handler(); }
};
const grid = {
  querySelectorAll(selector) { if (selector !== '[name="sms_codes[]"]') throw new Error('unexpected selector'); return inputs; },
  appendChild(row) {
    const match = row.innerHTML.match(/name="sms_codes\[\]"[^>]*value="([^"]+)"/);
    if (!match) throw new Error('new code field missing');
    const input = {value: match[1], required: /required/.test(match[0]), focus() { this.focused = true; }};
    inputs.push(input);
    row._input = input;
  }
};
const document = {
  getElementById(id) { return id === 'mgsqSmsAdminGrid' ? grid : id === 'mgsqAddSmsList' ? button : null; },
  createElement() { return {className: '', innerHTML: '', querySelector() { return this._input; }}; }
};
vm.runInNewContext(scripts.join('\n'), {document, String, Math, parseInt});
button.click();
if (inputs.length !== 7) throw new Error(`expected 7 rows, got ${inputs.length}`);
if (inputs[6].value !== 'G007') throw new Error(`expected G007, got ${inputs[6].value}`);
if (!inputs[6].required || !inputs[6].focused) throw new Error('new code input is not required/focused');
console.log(JSON.stringify({rows_before: 6, rows_after: inputs.length, generated_code: inputs[6].value, required: inputs[6].required, focused: inputs[6].focused}));
