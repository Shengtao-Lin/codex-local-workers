/** Offline native frontend. No SDK profile, Agent, model or provider is booted. */
import {readFileSync} from 'node:fs';
import {createInterface} from 'node:readline';
import {pathToFileURL} from 'node:url';
import {installKitToolBridge} from './strata_kit_tool_bridge.mjs';

const base = 'F:/Strata/harness/node_modules/@deepseek-ai/';
const {Context} = await import(pathToFileURL(base + 'cordis/lib/index.js'));
const {SystemPrompt} = await import(pathToFileURL(base + 'dsh-system-prompt/lib/index.js'));
const {ToolRuntime} = await import(pathToFileURL(base + 'dsh-tools/lib/index.js'));
const frames = createInterface({input:process.stdin, terminal:false})[Symbol.asyncIterator]();
const send = value => process.stdout.write(JSON.stringify(value) + '\n');
async function receive() {
  const {value, done} = await frames.next();
  if (done) throw new Error('Host closed before feedback');
  return JSON.parse(value);
}
const first = await receive();
if (first.kind !== 'host_context') throw new Error('Host handshake required');
let context = first.context;
let terminal = false;
const identity = Object.freeze({...first.identity});
const actions = JSON.parse(readFileSync(process.argv[2], 'utf8'));
if (!Array.isArray(actions) || actions.length < 1 || actions.length > 12) throw new Error('Bounded replay required');
const ctx = new Context();
new SystemPrompt(ctx, {includeHarnessIdentity:false});
new ToolRuntime(ctx, {mode:'native'});
const bridge = installKitToolBridge(ctx, {
  identity,
  // This dedicated process owns only this registered task; Python rechecks identity
  // and executes all path/version/budget/check rules in the existing host loop.
  authorize: () => !terminal,
  dispatch: async ({identity,action,arguments:args,call_id}) => {
    send({kind:'host_action',identity,action,arguments:args,call_id});
    const response = await receive();
    if (JSON.stringify(response.identity) !== JSON.stringify(identity)) throw new Error('Host identity changed');
    if (response.kind === 'host_terminal') {
      terminal = true;
      if (!response.host_handoff_verified) throw new Error('Host stopped without verified handoff: ' + response.status);
      return {status:response.status,host_handoff_verified:true,primary_acceptance:'PENDING'};
    }
    if (response.kind !== 'host_context') throw new Error('Unexpected host frame');
    context = response.context;
    return {status:'HOST_CONTINUE_NOT_ACCEPTANCE',...context};
  },
});
const results = [];
try {
  for (let n=0; n<actions.length; n++) {
    const {name,arguments:original} = actions[n];
    const args = {...original};
    if (args.expected_sha256 === '@current') args.expected_sha256 = context.source_sha256;
    const result = await ctx.tools.execute({name,arguments:args,callId:`native-replay-${n+1}`,signal:new AbortController().signal});
    results.push(result);
    if (result.isError || terminal) break;
  }
} finally {
  bridge.dispose();
}
send({kind:'driver_done',identity,results,provider_calls:0});
process.stdin.destroy();
