const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const filename = path.join(__dirname, '../app/api/boundaries/route.ts');
const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const m = new Module(filename, module);
m.filename = filename; m.paths = module.paths;
let calls = 0;
m.require = name => {
  if (name === 'next/server') return { NextResponse: { json: (body, opts) => ({ body, status: opts.status }) } };
  if (name === '@/lib/record') return { callRecord: async () => { calls++; return { status: 200, body: {} }; } };
  if (name === '@/lib/auth/request-body') {
    const rbSrc = ts.transpileModule(fs.readFileSync(path.join(__dirname, '../lib/auth/request-body.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
    const rb = new Module(path.join(__dirname, '../lib/auth/request-body.ts'), module);
    rb.filename = path.join(__dirname, '../lib/auth/request-body.ts');
    rb.paths = module.paths;
    rb._compile(rbSrc, rb.filename);
    return rb.exports;
  } // real (pure Request consumer)
  if (name === '@/lib/auth/authorize') return {
    authorizeFarm: async (_request, farmId) => farmId ? { ok: true, actor: { farmId, actorId: 'actor', role: 'operator' } } : { ok: false, status: 400, reason: 'farm required' },
    hasSameOrigin: request => request.headers.get('origin') === 'https://farm.example',
    validRequestId: value => typeof value === 'string' && /^[0-9a-f-]{36}$/i.test(value),
  };
  throw Error(`unexpected module ${name}`);
};
m._compile(source, filename);
function request(origin, type = 'application/json') {
  return new Request('https://farm.example/api/boundaries', { method: 'POST', headers: { host: 'farm.example', origin, 'content-type': type }, body: JSON.stringify({ farm_id: 'farm-1', request_id: '123e4567-e89b-42d3-a456-426614174000' }) });
}
test('only same-origin JSON boundary writes reach the record', async () => {
  calls = 0;
  assert.equal((await m.exports.POST(request('https://attacker.example'))).status, 403);
  assert.equal((await m.exports.POST(request('https://farm.example', 'text/plain'))).status, 415);
  assert.equal(calls, 0);
  assert.equal((await m.exports.POST(request('https://farm.example'))).status, 200);
  assert.equal(calls, 1);
});

test('oversize and non-object bodies never reach the record', async () => {
  calls = 0;
  const headers = { host: 'farm.example', origin: 'https://farm.example', 'content-type': 'application/json' };
  const large = new Request('https://farm.example/api/boundaries', { method: 'POST', headers, body: JSON.stringify({ note: 'x'.repeat(65536) }) });
  const array = new Request('https://farm.example/api/boundaries', { method: 'POST', headers, body: '[]' });
  assert.equal((await m.exports.POST(large)).status, 413);
  assert.equal((await m.exports.POST(array)).status, 400);
  assert.equal(calls, 0);
});
