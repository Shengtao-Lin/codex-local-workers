/** Minimal installed native Agent composition; never loads a product profile. */
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {installKitToolBridge} from './strata_kit_tool_bridge.mjs';
if (!process.env.KIT_STRATA_HARNESS_ROOT) throw new Error('Explicit installed Strata harness root required');
const root = resolve(process.env.KIT_STRATA_HARNESS_ROOT, 'node_modules/@deepseek-ai');
export const load = name => {
  if (!/^[a-z][a-z0-9-]+$/.test(name)) throw new Error('Invalid internal module name');
  return import(pathToFileURL(resolve(root, name, 'lib/index.js')));
};
export const llm = await load('dsh-llm');
const {Context} = await load('cordis');
const {SystemPrompt} = await load('dsh-system-prompt');
const {ToolRuntime} = await load('dsh-tools');
const {SessionStore} = await load('dsh-session');
const {SessionProjectionRegistry} = await load('dsh-session-projection');
const {AgentRegistry} = await load('dsh-agent');
const {AgentLoop} = await load('dsh-agent-loop');

export async function createNativeAgent({identity, adapter, authorize, dispatch, prompt, toolDefinitions, configureContext, externalToolNames = [], onInvalidArguments}) {
  const ctx = new Context();
  new SystemPrompt(ctx, {includeHarnessIdentity:false, personaPrefix:prompt});
  new SessionStore(ctx);
  new SessionProjectionRegistry(ctx);
  new AgentRegistry(ctx);
  new llm.LlmRuntime(ctx);
  new ToolRuntime(ctx, {mode:'native'});
  if (configureContext) await configureContext(ctx);
  ctx.llm.registerAdapter(['strata-local'], adapter);
  new AgentLoop(ctx, {agents:[],maxParallelToolCalls:{get:()=>1}});
  // Terminal marker is trusted host output, never a model FINISH assertion.
  const seam = {tools:{
    guard: fn => ctx.tools.guard(fn),
    register: definition => ctx.tools.register({...definition,execute:async (args,exec) => {
      const value = await definition.execute(args,exec);
      if (value.host_result?.host_handoff_verified === true || value.host_result?.host_finished === true) exec.concludeTurn();
      return value;
    }}),
  }};
  const bridge = installKitToolBridge(seam,{identity,authorize,dispatch,toolDefinitions,externalToolNames,onInvalidArguments});
  try {
    const handle = await ctx.agents.create({sessionId:identity.run_id,
      agentOptions:{provider:'strata-local',model:'iq3_s',maxTokens:12288}});
    return {ctx,agent:handle.agent,async dispose() {await handle.dispose(); bridge.dispose();}};
  } catch (error) {
    bridge.dispose();
    throw error;
  }
}
