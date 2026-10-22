import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import {openPostgres, initialize} from '/home/mgsfinance/releases/pg-auth-1545934831664242748/storage.mjs';
import {managerView} from '/home/mgsfinance/releases/pg-auth-1545934831664242748/manager-view.mjs';
import {createApp} from '/home/mgsfinance/releases/pg-auth-1545934831664242748/server.mjs';
assert.equal(process.versions.node, '22.23.4');
const db = await openPostgres({max: 1, options: '-c default_transaction_read_only=on -c statement_timeout=30000'});
let server;
try {
  assert.equal((await db.query('SHOW transaction_read_only')).rows[0].transaction_read_only, 'on');
  const rows = (await db.query("SELECT id FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id")).rows;
  let passed = 0;
  for (const {id} of rows) {
    const scenario = (await db.query('SELECT * FROM scenarios WHERE id=$1', [id])).rows[0];
    for (const key of ['icaro','isliago','joe','kelly','nicolas']) {
      const view = managerView(scenario, null, id.slice(10), key);
      assert.ok(!view.summary_control || view.summary_control.pass);
      passed++;
    }
  }
  const auth = JSON.parse(await fs.readFile(process.env.FINANCE_AUTH_FILE, 'utf8'));
  await initialize(db);
  const app = await createApp(db, {auth});
  server = app.listen(0, '127.0.0.1');
  await new Promise(resolve => server.once('listening', resolve));
  const port = server.address().port;
  async function get(path) {
    return new Promise((resolve, reject) => {
      const q = http.get({host:'127.0.0.1',port,path,headers:{Host:'dash.mgsdigitalcorp.com','X-Forwarded-Proto':'https'}}, response => {
        let bytes = 0;
        response.on('data', chunk => bytes += chunk.length);
        response.on('end', () => resolve({path,status:response.statusCode,bytes}));
      });
      q.on('error', reject);
    });
  }
  const checks = [];
  for (const path of ['/login','/api/scenarios','/api/health','/']) checks.push(await get(path));
  assert.equal(checks[0].status,200);
  assert.equal(checks[1].status,401);
  assert.equal(checks[2].status,401);
  assert.equal(checks[3].status,303);
  console.log(JSON.stringify({pass:true,node:process.versions.node,readonly_database:true,workspaces:rows.length,manager_views:passed,expected:rows.length*5,http_checks:checks,financial_writes:0}));
} finally {
  if (server) await new Promise(resolve => server.close(resolve));
  await db.close();
}
