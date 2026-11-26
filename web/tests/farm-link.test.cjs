const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

const filename = path.join(__dirname, '../lib/farm-link.ts');
const source = fs.readFileSync(filename, 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const membership = {
  validateFarmId: value => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(value),
};
const mod = new Module(filename, module);
mod.filename = filename;
mod.paths = module.paths;
mod.require = name => name === '@/lib/auth/membership' ? membership : require(name);
mod._compile(compiled, filename);
const { resolveFarmLink } = mod.exports;

test('opaque farm IDs open without exposing field coordinates', () => {
  assert.deepEqual(resolveFarmLink('biratori-hokkaido'), { farmId: 'biratori-hokkaido' });
});

test('legacy coordinate links require a valid farm ID and preserve the pin', () => {
  assert.deepEqual(resolveFarmLink('42.7018152%2C142.4071291', 'biratori-hokkaido'), {
    farmId: 'biratori-hokkaido', latitude: '42.7018152', longitude: '142.4071291',
  });
  assert.equal(resolveFarmLink('42.7018152%2C142.4071291'), null);
});

test('malformed paths, invalid IDs, and out-of-range coordinates are rejected', () => {
  assert.equal(resolveFarmLink('%E0%A4%A'), null);
  assert.equal(resolveFarmLink('farm-'), null);
  assert.equal(resolveFarmLink('91,142', 'biratori-hokkaido'), null);
  assert.equal(resolveFarmLink('42,181', 'biratori-hokkaido'), null);
});
