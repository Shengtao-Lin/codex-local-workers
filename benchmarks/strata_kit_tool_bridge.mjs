/** Experimental tool seam only; no native filesystem, shell, provider or SDK boot.
 * The trusted host callbacks must own scope, versions, budgets and validation.
 * This adapter does NOT implement those policies or claim OS isolation.
 */
const definitions = {
  kit_read: {
    action: 'read',
    properties: {path: {type: 'string'}, start_line: {type: 'integer'}, end_line: {type: 'integer'}},
  },
  kit_search: {
    action: 'search',
    properties: {path: {type: 'string'}, query: {type: 'string'}},
  },
  kit_propose: {
    action: 'propose',
    properties: {path: {type: 'string'}, expected_sha256: {type: 'string'}, content: {type: 'string'}},
  },
  kit_block: {action: 'blocked', properties: {reason: {type: 'string'}}},
};

export function installKitToolBridge(ctx, {identity, authorize, dispatch}) {
  if (!identity || Object.keys(identity).sort().join(',') !== 'run_id,task_id,unit_id' ||
      Object.values(identity).some(v => typeof v !== 'string' || !v) ||
      typeof authorize !== 'function' || typeof dispatch !== 'function') {
    throw new TypeError('Trusted identity, synchronous authorization and host dispatch required');
  }
  const boundIdentity = Object.freeze({...identity});
  const names = Object.keys(definitions);
  let closed = false;
  let active = false;
  const cleanups = [];
  // Unlike an extensible allow/deny waterfall, this guard cannot be force-allowed
  // by a later permissive plugin. Use a dedicated context, not the user's GUI.
  cleanups.push(ctx.tools.guard(exec => {
    if (closed || !Object.hasOwn(definitions, exec.name)) return 'Tool not in approved kit bridge';
    try {
      const decision = authorize({identity: boundIdentity, execution: exec});
      if (decision && typeof decision.then === 'function') {
        // Misconfigured async authorization is denied, with its rejection
        // contained rather than leaking an unhandled process rejection.
        Promise.resolve(decision).catch(() => {});
        return 'Host authorization must be synchronous';
      }
      if (decision !== true) return 'Host authorization denied';
    } catch {
      return 'Host authorization failed closed';
    }
    return undefined;
  }));
  try {
    for (const name of names) {
      const {properties, action} = definitions[name];
      cleanups.push(ctx.tools.register({
        name,
        description: `Request ${action} from the trusted kit host. ${action === 'read' ? '1..120 lines per request; use end_line-start_line+1<=120. ' : action === 'search' ? 'Literal search,10 matches max, exact approved files or approved directory selector only. ' : ''}No new authority; host evidence and tool_budget are authoritative.`,
        parameters: {type: 'object', properties, required: Object.keys(properties), additionalProperties: false},
        output: {
          schema: {type: 'object', properties: {host_result: {}}, required: ['host_result'], additionalProperties: false},
          render: (_args, value) => [{type: 'text', text: JSON.stringify(value)}],
        },
        async execute(args, exec) {
          if (closed || active || exec.signal.aborted) throw new Error('Bridge unavailable, busy or cancelled');
          // The registry's raw ToolDefinition schema is presentation, not a
          // replacement for host validation. Reject mixed/identity injection.
          if (!args || Array.isArray(args) || typeof args !== 'object' ||
              Object.keys(args).sort().join(',') !== Object.keys(properties).sort().join(',') ||
              Object.entries(properties).some(([k, s]) => s.type === 'integer'
                ? !Number.isSafeInteger(args[k]) : typeof args[k] !== 'string')) {
            throw new Error('Invalid bridge arguments');
          }
          active = true;
          try {
            return {host_result: await dispatch({
              identity: boundIdentity,
              action,
              arguments: args,
              call_id: exec.callId,
              signal: exec.signal,
            })};
          } finally {
            active = false;
          }
        },
      }));
    }
  } catch (error) {
    closed = true;
    for (const cleanup of cleanups.reverse()) cleanup();
    throw error;
  }
  return {names: Object.freeze(names), dispose() {
    closed = true;
    for (const cleanup of cleanups.splice(0).reverse()) cleanup();
  }};
}
