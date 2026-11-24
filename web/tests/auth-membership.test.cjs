const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
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

const sessionTools = loadTs('../lib/auth/session.ts');
const membership = loadTs('../lib/auth/membership.ts', name => name === './session' ? sessionTools : undefined);
const session = { version: 1, issuer: 'https://issuer.example', subject: 'subject-private', issuedAt: 1, expiresAt: 9999999999 };
const farmId = 'biratori-hokkaido';
let hash = 'a'.repeat(64);
const record = (overrides = {}) => ({
  schema_version: 1,
  farm_id: farmId,
  actor_hash: hash,
  role: 'operator',
  status: 'active',
  granted_at: '2026-01-01T00:00:00.000Z',
  expires_at: '2999-01-01T00:00:00.000Z',
  updated_at: '2026-01-01T00:00:00.000Z',
  ...overrides,
});

test('membership records use the exact hash-scoped tenant object path', () => {
  assert.equal(membership.membershipObjectPath(farmId, hash), `farms/${farmId}/members/${hash}.json`);
  assert.throws(() => membership.membershipObjectPath('../other', hash));
  assert.throws(() => membership.membershipObjectPath(farmId, 'subject-private'));
});

test('membership is isolated by farm and role and the lookup is fresh for each request', async () => {
  process.env.FARM_ACCESS_BUCKET = 'farm-access-test';
  hash = await membership.farmActorHash(session.issuer, session.subject);
  let current = record();
  let reads = 0;
  const lookup = async (_bucket, requestedFarm, actorHash) => {
    reads++;
    assert.equal(requestedFarm, farmId);
    assert.match(actorHash, /^[a-f0-9]{64}$/);
    return current;
  };
  const allowed = await membership.authorizeFarmActor(session, farmId, 'operator', lookup);
  assert.equal(allowed.ok, true);
  if (allowed.ok) assert.deepEqual(allowed.actor, { actorId: 'subject-private', farmId, role: 'operator' });
  assert.equal((await membership.authorizeFarmActor(session, farmId, 'admin', lookup)).status, 403);
  current = record({ status: 'revoked' });
  assert.equal((await membership.authorizeFarmActor(session, farmId, 'viewer', lookup)).status, 403);
  assert.equal(reads, 3);
});

test('unassigned farms, expired grants and mismatched membership documents fail closed', async () => {
  process.env.FARM_ACCESS_BUCKET = 'farm-access-test';
  hash = await membership.farmActorHash(session.issuer, session.subject);
  assert.equal((await membership.authorizeFarmActor(session, farmId, 'viewer', async () => null)).status, 403);
  assert.equal((await membership.authorizeFarmActor(session, farmId, 'viewer', async () => record({ expires_at: '2000-01-01T00:00:00.000Z' }))).status, 403);
  assert.equal((await membership.authorizeFarmActor(session, farmId, 'viewer', async () => record({ farm_id: 'another-farm' }))).status, 503);
  assert.equal((await membership.authorizeFarmActor(session, '../other', 'viewer', async () => record())).status, 400);
});

test('missing access store configuration refuses authorization', async () => {
  hash = await membership.farmActorHash(session.issuer, session.subject);
  delete process.env.FARM_ACCESS_BUCKET;
  assert.equal((await membership.authorizeFarmActor(session, farmId, 'viewer', async () => record())).status, 503);
});
