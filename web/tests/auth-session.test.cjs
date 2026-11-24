const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

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

const auth = loadTs('../lib/auth/session.ts');
const secret = 'a'.repeat(48);
const now = Math.floor(Date.now() / 1000);

test('session signature validates and tampered signatures fail', async () => {
  const value = { version: 1, issuer: 'https://identity.example', subject: 'user-1', issuedAt: now, expiresAt: now + 600 };
  const token = await auth.signSession(value, secret);
  assert.equal((await auth.verifySession(token, secret)).subject, 'user-1');
  assert.equal(await auth.verifySession(`${token}x`, secret), null);
  assert.equal(await auth.verifySession(token, 'b'.repeat(48)), null);
});

test('expired and future-issued sessions are refused', async () => {
  const expired = await auth.signSession({ version: 1, issuer: 'https://identity.example', subject: 'u', issuedAt: now - 700, expiresAt: now - 1 }, secret);
  const future = await auth.signSession({ version: 1, issuer: 'https://identity.example', subject: 'u', issuedAt: now + 500, expiresAt: now + 600 }, secret);
  assert.equal(await auth.verifySession(expired, secret), null);
  assert.equal(await auth.verifySession(future, secret), null);
});

test('OIDC state is signed, short-lived, and rejects unsafe redirect destinations', async () => {
  const state = { version: 1, state: 'state-value', nonce: 'nonce-value', verifier: 'v'.repeat(48), next: '/field?farm_id=biratori', issuedAt: now, expiresAt: now + 300 };
  const token = await auth.signOidcState(state, secret);
  assert.equal((await auth.verifyOidcState(token, secret)).state, 'state-value');
  assert.equal(await auth.verifyOidcState(token, 'c'.repeat(48)), null);
  const expired = await auth.signOidcState({ ...state, expiresAt: now - 1 }, secret);
  const unsafe = await auth.signOidcState({ ...state, next: '//attacker.example' }, secret);
  assert.equal(await auth.verifyOidcState(expired, secret), null);
  assert.equal(await auth.verifyOidcState(unsafe, secret), null);
});

test('redirect and cookie parsing are constrained', () => {
  assert.equal(auth.safeNext('/records?a=1'), true);
  assert.equal(auth.safeNext('//attacker.example'), false);
  assert.equal(auth.safeNext('/\\attacker.example'), false);
  assert.equal(auth.cookieHeader(new Request('https://farm.test', { headers: { cookie: 'other=x; farm_session=a%2Eb' } }), 'farm_session'), 'a.b');
  assert.equal(auth.cookieHeader(new Request('https://farm.test', { headers: { cookie: 'farm_session=%ZZ' } }), 'farm_session'), null);
});
