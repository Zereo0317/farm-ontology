const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const ts = require('typescript');
const source = fs.readFileSync(require('node:path').join(__dirname, '../middleware.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const m = new Module('middleware', module);
m.filename = __filename;
m.paths = module.paths;
const makeResponse = (kind, status = 200) => ({ kind, status, cookies: { set() {} } });
const originalRequire = m.require.bind(m);
m.require = (name) => name === 'next/server' ? { NextResponse: {
  next: () => makeResponse('next'),
  json: (_body, options) => makeResponse('json', options.status),
  redirect: () => makeResponse('redirect', 307),
} } : originalRequire(name);
m._compile(compiled, __filename);
const { middleware } = m.exports;
function request(path, cookie) {
  const url = new URL(path, 'https://example.test');
  return { nextUrl: url, headers: new Headers(), cookies: { get: name => name === 'farm_access' && cookie ? { value: cookie } : undefined } };
}
test('boundary routes require an access cookie', () => {
  process.env.WEB_ACCESS_TOKEN = 'secret';
  assert.equal(middleware(request('/api/boundaries')).status, 401);
  assert.equal(middleware(request('/walk')).kind, 'redirect');
  assert.equal(middleware(request('/api/boundaries', 'wrong')).status, 401);
  assert.equal(middleware(request('/api/boundaries', 'secret')).kind, 'next');
});
test('missing secret never opens protected routes', () => {
  delete process.env.WEB_ACCESS_TOKEN;
  assert.equal(middleware(request('/api/boundaries')).status, 503);
  assert.equal(middleware(request('/walk')).status, 503);
  assert.equal(middleware(request('/livez')).kind, 'next');
});
