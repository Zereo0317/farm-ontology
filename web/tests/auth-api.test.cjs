const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

function loadObservationRoute({ authorization, record }) {
  const filename = path.join(__dirname, '../app/api/observations/route.ts');
  const source = fs.readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const m = new Module(filename, module);
  m.filename = filename;
  m.paths = module.paths;
  m.require = name => {
    if (name === 'next/server') return { NextResponse: { json: (body, options) => Response.json(body, options) } };
    if (name === '@/lib/auth/authorize') return {
      authorizeFarm: authorization,
      hasSameOrigin: () => true,
      validRequestId: value => typeof value === 'string' && /^[0-9a-f-]{36}$/.test(value),
    };
    if (name === '@/lib/auth/request-body') return loadTs('../lib/auth/request-body.ts');
    if (name === '@/lib/record') return { callRecord: record };
    throw new Error(`unexpected import ${name}`);
  };
  m._compile(compiled, filename);
  return m.exports;
}

function loadNotesRoute({ authorization, record }) {
  const filename = path.join(__dirname, '../app/api/notes/route.ts');
  const source = fs.readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const m = new Module(filename, module);
  m.filename = filename;
  m.paths = module.paths;
  m.require = name => {
    if (name === 'next/server') return { NextResponse: { json: (body, options) => Response.json(body, options) } };
    if (name === '@/lib/auth/authorize') return {
      authorizeFarm: authorization,
      hasSameOrigin: () => true,
      validRequestId: value => typeof value === 'string' && /^[0-9a-f-]{36}$/.test(value),
    };
    if (name === '@/lib/auth/request-body') return loadTs('../lib/auth/request-body.ts');
    if (name === '@/lib/record') return { callRecord: record };
    throw new Error(`unexpected import ${name}`);
  };
  m._compile(compiled, filename);
  return m.exports;
}

function loadTs(relative) {
  const filename = path.join(__dirname, relative);
  const source = fs.readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const m = new Module(filename, module);
  m.filename = filename;
  m.paths = module.paths;
  m._compile(compiled, filename);
  return m.exports;
}

function request(payload) {
  return new Request('https://farm.example/api/observations', {
    method: 'POST',
    headers: { host: 'farm.example', origin: 'https://farm.example', 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

test('observation write uses authorized tenant identity and forwards retry id', async () => {
  let forwarded;
  const route = loadObservationRoute({
    authorization: async (_request, farmId, role) => {
      assert.equal(farmId, 'attacker-selected');
      assert.equal(role, 'operator');
      return { ok: true, actor: { actorId: 'actor', farmId: 'authorized-farm', role: 'operator' } };
    },
    record: async body => { forwarded = body; return { status: 201, body: { file: 'record.json' } }; },
  });
  const response = await route.POST(request({ farm_id: 'attacker-selected', request_id: '123e4567-e89b-42d3-a456-426614174000', latitude: 1, longitude: 2 }));
  assert.equal(response.status, 201);
  assert.equal(forwarded.farm_id, 'authorized-farm');
  assert.equal(forwarded.request_id, '123e4567-e89b-42d3-a456-426614174000');
});

test('observation writes refuse missing authorization and malformed request ids', async () => {
  let calls = 0;
  const record = async () => { calls++; return { status: 200, body: {} }; };
  const denied = loadObservationRoute({ authorization: async () => ({ ok: false, status: 403, reason: 'no membership' }), record });
  assert.equal((await denied.POST(request({ farm_id: 'farm-1', request_id: '123e4567-e89b-42d3-a456-426614174000' }))).status, 403);
  const allowed = loadObservationRoute({ authorization: async () => ({ ok: true, actor: { actorId: 'actor', farmId: 'farm-1', role: 'operator' } }), record });
  assert.equal((await allowed.POST(request({ farm_id: 'farm-1' }))).status, 400);
  assert.equal((await allowed.POST(request({ farm_id: 'farm-1', request_id: '123E4567-E89B-42D3-A456-426614174000' }))).status, 400);
  assert.equal(calls, 0);
});

test('observation and note routes cap JSON reads at 64 KiB before authorization or storage', async () => {
  let calls = 0;
  const dependencies = {
    authorization: async () => ({ ok: true, actor: { actorId: 'actor', farmId: 'farm-1', role: 'operator' } }),
    record: async () => { calls++; return { status: 200, body: {} }; },
  };
  const largePayload = { farm_id: 'farm-1', request_id: '123e4567-e89b-42d3-a456-426614174000', note: 'x'.repeat(70 * 1024) };
  const observation = loadObservationRoute(dependencies);
  const note = loadNotesRoute(dependencies);
  assert.equal((await observation.POST(request(largePayload))).status, 413);
  assert.equal((await note.POST(request(largePayload))).status, 413);
  assert.equal(calls, 0);
});
