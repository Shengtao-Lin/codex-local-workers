/** One deterministic wire rebuild. Model-written memory never grants authority. */
export class ContextError extends Error {
  constructor(message,category='bound') {super(message);this.category=category;}
}
export function exceedsContextBound(body) {
  // JSON UTF-8 bytes + conservative framing reserve + full output allowance.
  return Buffer.byteLength(JSON.stringify(body),'utf8')+4096+12288>65536;
}
function object(value) {
  return value!==null && typeof value==='object' && !Array.isArray(value);
}
function sameJson(left,right) {
  return object(left) && object(right) && JSON.stringify(left)===JSON.stringify(right);
}
/** Only omit a byte-equivalent state field already retained in this exact turn.
 * Source, checks and transaction authority remain in the Python host. Nothing
 * is inferred from summaries, prior turns, source text or model-written memory.
 */
function snapshotWithoutClosedDuplicates(current,tail) {
  if(!object(current) || Object.hasOwn(current,'state_in_retained_tool_result') || tail.length!==2 || tail[0].role!=='assistant' || tail[1].role!=='user') return current;
  const calls=Array.isArray(tail[0].content)?tail[0].content.filter(b=>b.type==='tool_use'):[];
  const results=Array.isArray(tail[1].content)?tail[1].content.filter(b=>b.type==='tool_result'):[];
  if(calls.length!==1 || results.length!==1 || calls[0].name!=='kit_propose' ||
      typeof calls[0].id!=='string' || !calls[0].id || results[0].tool_use_id!==calls[0].id || results[0].is_error) return current;
  let content=results[0].content;
  if(Array.isArray(content)) {
    if(content.length!==1 || !object(content[0]) || content[0].type!=='text') return current;
    content=content[0].text;
  }
  if(typeof content!=='string') return current;
  let wrapper;
  try {wrapper=JSON.parse(content);} catch {return current;}
  if(!object(wrapper) || Object.keys(wrapper).length!==1 || !object(wrapper.host_result)) return current;
  const host=wrapper.host_result;
  if(host.tool_result?.status!=='changed_and_checked') return current;
  if(!['task_id','unit_id','run_id'].every(k=>typeof current.identity?.[k]==='string' && current.identity[k]) ||
      !sameJson(current.identity,host.identity) || !sameJson(current.current_check,host.current_check) ||
      typeof current.current_check.path!=='string' || !current.current_check.path ||
      typeof current.current_check.sha256!=='string' || !current.current_check.sha256 ||
      !sameJson(current.files,host.files)) return current;
  const fields=['validation','work_state'].filter(k=>sameJson(current[k],host[k]));
  if(!fields.length) return current;
  const snapshot={...current};
  for(const field of fields) delete snapshot[field];
  snapshot.state_in_retained_tool_result={
    tool_use_id:calls[0].id,fields,
    note:'Identical current state fields are present in the following retained kit_propose host_result; identity, check and file versions match.',
  };
  return snapshot;
}
export function rebuildContext(body, task, current, {checkBound=true,deduplicateClosedState=false}={}) {
  const tail=closedToolTurn(body.messages??[]);
  const snapshot=deduplicateClosedState?snapshotWithoutClosedDuplicates(current,tail):current;
  const result={...body,messages:[{role:'user',content:[{type:'text',text:JSON.stringify({
    task,current:snapshot,context_rebuilt:true,
    prior_evidence:'Host state retains current changes/checks and the latest closed conversation turn. Original history is archived. No budget reset.',
  })}]},...tail]};
  if(checkBound && exceedsContextBound(result)) throw new ContextError('Context preflight bound exceeded');
  return result;
}

/** Keep ALL appended native turns between at most two progress-gated rebuilds.
 * A second rebuild requires a newer host effective-edit revision, not a read,
 * model claim or green self-report. Prefix drift always stops.
 */
export class ContextWindow {
  constructor(task,{deduplicateClosedState=false}={}) {this.task=task;this.deduplicateClosedState=deduplicateClosedState; this.anchor=null; this.prefix=null; this.length=0;this.rebuilds=0;this.editRevision=-1;}
  rebuild(body,current,editRevision=0,{checkBound=true}={}) {
    if(!Number.isSafeInteger(editRevision) || editRevision<0) throw new ContextError('Invalid host edit revision','prefix');
    if(this.rebuilds>=2 || (this.rebuilds && editRevision<=this.editRevision)) throw new ContextError('Only one context rebuild without new effective edit; at most two per task');
    // Verify the old anchor before replacing it; rebuilding cannot hide drift.
    if(this.anchor!==null) this.assertPrefix(body);
    const anchor=JSON.stringify(body.messages??[]);
    const result=rebuildContext(body,this.task,current,{checkBound,deduplicateClosedState:this.deduplicateClosedState});
    this.anchor=anchor;
    this.length=(body.messages??[]).length;
    this.prefix=JSON.parse(JSON.stringify(result.messages));
    this.rebuilds++;
    this.editRevision=editRevision;
    return result;
  }
  assertPrefix(body) {
    if(this.anchor===null) throw new ContextError('No context rebuild anchor','prefix');
    const messages=body.messages??[];
    if(JSON.stringify(messages.slice(0,this.length))!==this.anchor) throw new ContextError('Native conversation prefix changed after context rebuild','prefix');
  }
  project(body,{checkBound=true}={}) {
    this.assertPrefix(body);
    const messages=body.messages??[];
    const result={...body,messages:[...this.prefix,...messages.slice(this.length)]};
    if(checkBound && exceedsContextBound(result)) throw new ContextError('Post-rebuild context bound exhausted');
    return result;
  }
}

export function closedToolTurn(messages) {
  for(let i=messages.length-1;i>=0;i--) {
    const message=messages[i];
    if(message.role!=='assistant' || !Array.isArray(message.content)) continue;
    const calls=message.content.filter(b=>b.type==='tool_use').map(b=>b.id);
    if(!calls.length) continue;
    const tail=messages.slice(i);
    const results=tail.filter(m=>m.role==='user').flatMap(m=>Array.isArray(m.content)?m.content:[])
      .filter(b=>b.type==='tool_result').map(b=>b.tool_use_id);
    if(calls.every(id=>results.includes(id)) && results.every(id=>calls.includes(id))) return tail;
  }
  return [];
}
