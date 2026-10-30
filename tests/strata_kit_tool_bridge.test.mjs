/** Exercises installed real ToolRuntime with stub host callbacks, ZERO LLM.
 * Does not load SDK profiles, filesystem/Web/shell/LLM plugins or credentials.
 */
import assert from 'node:assert/strict';
import {test} from 'node:test';
import {pathToFileURL} from 'node:url';
import {installKitToolBridge} from '../benchmarks/strata_kit_tool_bridge.mjs';

const base = 'F:/Strata/harness/node_modules/@deepseek-ai/';
const {Context} = await import(pathToFileURL(base + 'cordis/lib/index.js'));
const {SystemPrompt} = await import(pathToFileURL(base + 'dsh-system-prompt/lib/index.js'));
const {ToolRuntime} = await import(pathToFileURL(base + 'dsh-tools/lib/index.js'));

const identity = {task_id: 'offline-task', unit_id: 'offline-unit', run_id: 'offline-run'};
function fixture({authorize = () => true, dispatch} = {}) {
  const ctx = new Context();
  new SystemPrompt(ctx, {includeHarnessIdentity: false});
  new ToolRuntime(ctx, {mode: 'native'});
  const calls = [];
  const bridge = installKitToolBridge(ctx, {identity, authorize, dispatch: dispatch ?? (async request => {
    calls.push(request);
    return {status: 'HOST_STUB_ONLY_NOT_VALIDATION'};
  })});
  let n = 0;
  const call = (name, args, signal = new AbortController().signal) => ctx.tools.execute({
    name, arguments: args, callId: `control-${++n}`, signal,
  });
  return {ctx, calls, bridge, call};
}

test('only four bridge tools presented, bound host identity reaches dispatch', async () => {
  const f = fixture();
  assert.deepEqual(f.ctx.tools.schemas().map(s => s.name).sort(), ['kit_block','kit_propose','kit_read','kit_search']);
  const result = await f.call('kit_read', {path: 'src/a.py', start_line: 1, end_line: 10});
  assert.equal(result.isError, false);
  assert.deepEqual(f.calls[0].identity, identity);
  assert.equal(f.calls[0].action, 'read');
  assert.equal(f.calls[0].signal.aborted, false);
  f.bridge.dispose();
});

test('deny stops host dispatch; an allow waterfall cannot override monotonic guard', async () => {
  const f = fixture({authorize: () => false});
  f.ctx.on('tools/pre-execute', async () => ({kind: 'allow'}));
  assert.equal((await f.call('kit_block', {reason: 'x'})).isError, true);
  assert.equal(f.calls.length, 0);
  f.bridge.dispose();
});

test('unexpected raw native shell is blocked before its body', async () => {
  const f = fixture();
  let invoked = false;
  f.ctx.tools.register({name: 'shell', description: 'negative stub', parameters: {type:'object',properties:{}},
    output: {schema: {type:'object'}, render: () => []},
    execute: async () => {invoked = true; return {};},
  });
  assert.equal((await f.call('shell', {})).isError, true);
  assert.equal(invoked, false);
  assert.equal(f.calls.length, 0);
  f.bridge.dispose();
});

for (const authorize of [() => undefined, () => 'allow', async () => true,
  async () => {throw new Error('async guard failure');}, () => {throw new Error('guard failure');}]) {
  test('only explicit synchronous host true authorizes', async () => {
    const f = fixture({authorize});
    assert.equal((await f.call('kit_block', {reason: 'x'})).isError, true);
    assert.equal(f.calls.length, 0);
    f.bridge.dispose();
  });
}

test('model cannot inject run identity or mixed actions', async () => {
  const f = fixture();
  const r = await f.call('kit_read', {path:'src/a.py', start_line:1, end_line:3, run_id:'forged'});
  assert.equal(r.isError, true);
  assert.equal(f.calls.length, 0);
  f.bridge.dispose();
});

test('cancelled call never reaches host', async () => {
  const f = fixture();
  const controller = new AbortController();
  controller.abort();
  assert.equal((await f.call('kit_block', {reason:'stop'}, controller.signal)).isError, true);
  assert.equal(f.calls.length, 0);
  f.bridge.dispose();
});

test('host scope/version rejection returns error, never successful validation', async () => {
  const f = fixture({dispatch: async () => {throw new Error('Host rejected path/version');}});
  const r = await f.call('kit_propose', {path:'../forbidden.py', expected_sha256:'old', content:'x'});
  assert.equal(r.isError, true);
  assert.equal(r.value, undefined);
  f.bridge.dispose();
});

test('one active host operation, remaining operations fail closed', {timeout:1000}, async () => {
  let resolve;
  const f = fixture({dispatch: () => new Promise(r => {resolve = r;})});
  const first = f.call('kit_block', {reason:'x'});
  while (!resolve) await new Promise(r => setImmediate(r));
  assert.equal((await f.call('kit_block', {reason:'y'})).isError, true);
  resolve({status:'STUB'});
  assert.equal((await first).isError, false);
  f.bridge.dispose();
});

test('disposed bridge tools no longer callable', async () => {
  const f = fixture();
  f.bridge.dispose();
  assert.equal((await f.call('kit_block', {reason:'x'})).isError, true);
  assert.equal(f.calls.length, 0);
});

test('missing host or partial identity cannot install', () => {
  assert.throws(() => installKitToolBridge({}, {identity, authorize: () => true}));
  assert.throws(() => installKitToolBridge({}, {identity: {task_id:'x'}, authorize: () => true, dispatch: () => {}}));
});
