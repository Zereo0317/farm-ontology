const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

function loadCallback() {
  const filename = path.join(__dirname, '../app/api/auth/callback/route.ts');
  const source = fs.readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const m = new Module(filename, module);
  m.filename = filename;
  m.paths = module.paths;
  m.require = name => {
    if (name === 'next/server') return { NextResponse: { redirect: (url, status) => ({ url: String(url), status, cookies: { writes: [], set(...args) { this.writes.push(args); } } }) } };
    if (name === '@/lib/auth/session') return {
      cookieHeader: request => request.headers.get('cookie')?.split('=')[1] ?? null,
      OIDC_STATE_COOKIE: 'farm_oidc_state', SESSION_COOKIE: 'farm_session', SESSION_SECONDS: 28800,
      secureCookies: () => true,
      sessionSecret: () => 's'.repeat(48),
      verifyOidcState: async () => ({ state: 'state-1', nonce: 'nonce-1', verifier: 'verifier', next: '/field?farm_id=farm-1' }),
      safeNext: value => value.startsWith('/') && !value.startsWith('//'),
    };
    if (name === '@/lib/auth/oidc') return { finishOidcLogin: async () => 'signed-session' };
    throw new Error(`unexpected import ${name}`);
  };
  m._compile(compiled, filename);
  return m.exports;
}

const callback = loadCallback();
const request = state => new Request(`https://farm.example/api/auth/callback?code=one-time&state=${state}`, { headers: { cookie: 'farm_oidc_state=signed-state' } });

test('callback refuses missing or mismatched OIDC state', async () => {
  const missing = await callback.GET(new Request('https://farm.example/api/auth/callback?code=one-time'));
  assert.equal(new URL(missing.url).pathname, '/login');
  const mismatch = await callback.GET(request('attacker-state'));
  assert.equal(new URL(mismatch.url).searchParams.get('error'), 'state');
  assert.ok(mismatch.cookies.writes.some(([name, value, options]) => name === 'farm_session' && value === '' && options.maxAge === 0));
});

test('successful callback sets an HttpOnly Secure SameSite=Lax session cookie', async () => {
  const response = await callback.GET(request('state-1'));
  assert.equal(response.status, 303);
  assert.equal(response.url, 'https://farm.example/field?farm_id=farm-1');
  const sessionWrite = response.cookies.writes.find(([name]) => name === 'farm_session');
  assert.ok(sessionWrite);
  assert.equal(sessionWrite[1], 'signed-session');
  assert.deepEqual(sessionWrite[2], { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 28800 });
});
