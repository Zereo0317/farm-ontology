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
  throw Error(`unexpected module ${name}`);
};
m._compile(source, filename);
function request(origin, type = 'application/json') {
  return new Request('https://farm.example/api/boundaries', { method: 'POST', headers: { host: 'farm.example', origin, 'content-type': type }, body: '{}' });
}
test('only same-origin JSON boundary writes reach the record', async () => {
  calls = 0;
  assert.equal((await m.exports.POST(request('https://attacker.example'))).status, 403);
  assert.equal((await m.exports.POST(request('https://farm.example', 'text/plain'))).status, 415);
  assert.equal(calls, 0);
  assert.equal((await m.exports.POST(request('https://farm.example'))).status, 200);
  assert.equal(calls, 1);
});
