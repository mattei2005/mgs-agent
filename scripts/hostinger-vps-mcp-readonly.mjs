#!/usr/bin/env node
// Expose only fixed-VM GET operations through the official Hostinger MCP runtime.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const policy = JSON.parse(fs.readFileSync('/root/mgs-agent/data/hostinger-vps-zeus.json', 'utf8'));
const pkg = `${policy.install_dir}/node_modules/hostinger-api-mcp`;
const {startServer} = await import(pathToFileURL(`${pkg}/src/core/runtime.js`).href);
const {default: catalog} = await import(pathToFileURL(`${pkg}/src/core/tools/vps.js`).href);
// The official meta-tools are general-purpose. In this local GET-only catalog,
// execute and multi-execute cannot mutate anything, including unknown operations.
const {META_TOOLS} = await import(pathToFileURL(`${pkg}/src/core/catalog.js`).href);
for (const tool of META_TOOLS) {
  tool.annotations = {...tool.annotations, readOnlyHint: true, destructiveHint: false};
}
const allowed = new Set(policy.allowed_operations);
const tools = catalog.filter(t => allowed.has(t.name)).map(source => {
  assert.equal(source.method, 'GET', 'Write operation refused');
  assert.equal(source.annotations?.readOnlyHint, true);
  assert.equal(source.group, 'vps');
  assert.ok(source.path.startsWith('/api/vps/v1/virtual-machines/{virtualMachineId}'));
  const tool = structuredClone(source);
  // Bind the actual URL, not merely a schema hint: caller cannot select another VM.
  tool.path = tool.path.replace('{virtualMachineId}', String(policy.virtual_machine_id));
  delete tool.inputSchema.properties.virtualMachineId;
  tool.inputSchema.required = tool.inputSchema.required.filter(k => k !== 'virtualMachineId');
  tool.inputSchema.additionalProperties = false;
  tool.description += ` Fixed MGS target: ${policy.hostname} (${policy.virtual_machine_id}). Read-only; no virtualMachineId parameter needed.`;
  return tool;
});
assert.equal(tools.length, allowed.size, 'Allowlisted operation missing from official catalog');
assert.equal(JSON.parse(fs.readFileSync(`${pkg}/package.json`, 'utf8')).version, policy.package_version);
assert.equal(process.env.API_BASE_URL, 'https://developers.hostinger.com');
assert.ok(process.env.HOSTINGER_API_TOKEN);
assert.equal(process.argv.length, 2, 'No alternate transports/arguments allowed');
startServer({name: 'mgs-hostinger-vps-readonly', version: policy.package_version, tools});
