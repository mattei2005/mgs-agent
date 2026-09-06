import {test} from 'node:test';import assert from 'node:assert/strict';
import * as storage from '../storage.mjs';
test('production PostgreSQL adapter is available without replacing PGlite tests',()=>{assert.equal(typeof storage.openPostgres,'function');});
