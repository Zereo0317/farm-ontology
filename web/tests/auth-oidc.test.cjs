const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const crypto = require('node:crypto');
const ts = require('typescript');

function loadTs(relative, extraRequire = () => undefined) {
  const filename = path.join(__dirname, relative);
  const source = fs.readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const m = new Module(filename, module);
  m.filename = filename;
  m.paths = module.paths;
  const original = m.require.bind(m);
  m.require = name => extraRequire(name) ?? original(name);
  m._compile(compiled, filename);
  return m.exports;
}

const session = loadTs('../lib/auth/session.ts');
const oidc = loadTs('../lib/auth/oidc.ts', name => name === './session' ? session : undefined);
const pair = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
const jwk = { ...pair.publicKey.export({ format: 'jwk' }), kid: 'test-key', alg: 'RS256', use: 'sig' };
const issuer = 'https://identity.example';
const clientId = 'farm-web-client';
const verifier = 'v'.repeat(64);
let claims;

function signedToken(overrides = {}, signer = pair.privateKey) {
  const now = Math.floor(Date.now() / 1000);
  const header = Buffer.from(JSON.stringify({ alg: 'RS256', kid: 'test-key', typ: 'JWT' })).toString('base64url');
  const body = Buffer.from(JSON.stringify({
    iss: issuer, sub: 'subject-1', aud: clientId, iat: now, exp: now + 300,
    nonce: 'expected-nonce', email_verified: true, ...overrides,
  })).toString('base64url');
  const data = `${header}.${body}`;
  const signature = crypto.sign('RSA-SHA256', Buffer.from(data), signer).toString('base64url');
  return `${data}.${signature}`;
}

function installProvider() {
  process.env.FARM_OIDC_ISSUER = issuer;
  process.env.FARM_OIDC_CLIENT_ID = clientId;
  process.env.FARM_OIDC_CLIENT_SECRET = 'private-client-secret-for-test';
  process.env.FARM_OIDC_REDIRECT_URI = 'https://farm.example/api/auth/callback';
  process.env.FARM_SESSION_SECRET = 'x'.repeat(48);
  global.fetch = async (input, init = {}) => {
    const url = String(input);
    if (url === `${issuer}/.well-known/openid-configuration`) {
      return Response.json({
        issuer,
        authorization_endpoint: `${issuer}/authorize`,
        token_endpoint: `${issuer}/token`,
        jwks_uri: 'https://keys.example/keys',
      });
    }
    if (url === 'https://keys.example/keys') return Response.json({ keys: [jwk] });
    if (url === `${issuer}/token`) {
      const body = new URLSearchParams(init.body);
      assert.equal(body.get('code_verifier'), verifier);
      assert.equal(body.get('client_id'), clientId);
      return Response.json({ id_token: claims });
    }
    throw new Error(`unexpected fetch ${url}`);
  };
}

test('authorization request uses state, nonce and S256 PKCE with a signed short-lived state cookie', async () => {
  installProvider();
  const result = await oidc.beginOidcLogin('/farm?farm_id=biratori-hokkaido');
  assert.equal(result.url.searchParams.get('response_type'), 'code');
  assert.equal(result.url.searchParams.get('code_challenge_method'), 'S256');
  const [statePayload] = result.stateCookie.split('.');
  const state = JSON.parse(Buffer.from(statePayload, 'base64url').toString('utf8'));
  const expectedChallenge = crypto.createHash('sha256').update(state.verifier).digest('base64url');
  assert.equal(result.url.searchParams.get('code_challenge'), expectedChallenge);
  assert.ok(result.url.searchParams.get('state'));
  assert.ok(result.url.searchParams.get('nonce'));
  assert.ok(result.stateCookie.includes('.'));
  assert.equal(result.url.searchParams.get('nonce'), state.nonce);
});

test('authorization code exchange verifies issuer, audience, signature, expiry, nonce and PKCE verifier', async () => {
  installProvider();
  claims = signedToken();
  const sessionToken = await oidc.finishOidcLogin('one-time-code', verifier, 'expected-nonce');
  const verified = await session.verifySession(sessionToken, process.env.FARM_SESSION_SECRET);
  const expectedActorHash = crypto.createHash('sha256').update(`${issuer}\0subject-1`).digest('hex');
  assert.equal(verified.actorHash, expectedActorHash);
  assert.equal(Object.hasOwn(verified, 'subject'), false);
  const cookiePayload = JSON.parse(Buffer.from(sessionToken.split('.')[0], 'base64url').toString('utf8'));
  assert.equal(cookiePayload.actorHash, expectedActorHash);
  assert.equal(Object.hasOwn(cookiePayload, 'subject'), false);
});

test('wrong issuer, audience, signature, expiry, nonce, or unverified email fail closed', async t => {
  installProvider();
  const invalid = [
    ['issuer', signedToken({ iss: 'https://attacker.example' })],
    ['audience', signedToken({ aud: 'another-client' })],
    ['expired', signedToken({ exp: Math.floor(Date.now() / 1000) - 1 })],
    ['nonce', signedToken({ nonce: 'wrong' })],
    ['unverified email', signedToken({ email_verified: false })],
    ['signature', signedToken({}, crypto.generateKeyPairSync('rsa', { modulusLength: 2048 }).privateKey)],
  ];
  for (const [name, token] of invalid) {
    await t.test(name, async () => {
      claims = token;
      await assert.rejects(() => oidc.finishOidcLogin('one-time-code', verifier, 'expected-nonce'));
    });
  }
});

test('missing OIDC configuration refuses to start login', async () => {
  delete process.env.FARM_OIDC_ISSUER;
  delete process.env.FARM_OIDC_CLIENT_ID;
  delete process.env.FARM_OIDC_CLIENT_SECRET;
  delete process.env.FARM_OIDC_REDIRECT_URI;
  delete process.env.FARM_SESSION_SECRET;
  await assert.rejects(() => oidc.beginOidcLogin('/'));
});
