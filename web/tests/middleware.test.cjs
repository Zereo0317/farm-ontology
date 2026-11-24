const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

const filename = path.join(__dirname, '../middleware.ts');
const source = fs.readFileSync(filename, 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const m = new Module(filename, module);
m.filename = filename;
m.paths = module.paths;
const makeResponse = (kind, status = 200) => ({ kind, status, cookies: { set() {} } });
const originalRequire = m.require.bind(m);
m.require = name => {
  if (name === 'next/server') return { NextResponse: {
    next: () => makeResponse('next'),
    json: (_body, options) => makeResponse('json', options.status),
    redirect: () => makeResponse('redirect', 307),
  } };
  if (name === '@/lib/auth/session') return { SESSION_COOKIE: 'farm_session', verifySession: async token => token === 'valid' ? { issuer: 'https://identity.example', subject: 'actor' } : null };
  return originalRequire(name);
};
m._compile(compiled, filename);
const { middleware } = m.exports;

function configure() {
  process.env.FARM_SESSION_SECRET = 's'.repeat(40);
  process.env.FARM_OIDC_ISSUER = 'https://identity.example';
  process.env.FARM_OIDC_CLIENT_ID = 'client';
  process.env.FARM_OIDC_CLIENT_SECRET = 'client-secret';
  process.env.FARM_OIDC_REDIRECT_URI = 'https://farm.example/api/auth/callback';
  process.env.FARM_ACCESS_BUCKET = 'farm-access-test';
}

function request(pathname, session) {
  const url = new URL(pathname, 'https://farm.example');
  return {
    nextUrl: url,
    headers: new Headers({ 'accept-language': 'ja,en;q=0.8' }),
    cookies: { get: name => name === 'farm_session' && session ? { value: session } : undefined },
  };
}

test('farm pages and APIs require a valid individual session', async () => {
  configure();
  assert.equal((await middleware(request('/api/observations'))).status, 401);
  assert.equal((await middleware(request('/api/observations', 'forged'))).status, 401);
  assert.equal((await middleware(request('/field'))).kind, 'redirect');
  assert.equal((await middleware(request('/api/observations', 'valid'))).kind, 'next');
});

test('missing identity configuration fails closed but keeps public routes available', async () => {
  delete process.env.FARM_SESSION_SECRET;
  delete process.env.FARM_OIDC_ISSUER;
  delete process.env.FARM_OIDC_CLIENT_ID;
  delete process.env.FARM_OIDC_CLIENT_SECRET;
  delete process.env.FARM_OIDC_REDIRECT_URI;
  delete process.env.FARM_ACCESS_BUCKET;
  assert.equal((await middleware(request('/api/observations'))).status, 503);
  assert.equal((await middleware(request('/'))).status, 503);
  assert.equal((await middleware(request('/livez'))).kind, 'next');
  assert.equal((await middleware(request('/report/biratori'))).kind, 'next');
  assert.equal((await middleware(request('/api/auth/callback'))).kind, 'next');
});
