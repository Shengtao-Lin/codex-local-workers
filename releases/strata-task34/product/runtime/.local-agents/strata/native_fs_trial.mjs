/** Explicit experiment: installed native fs tools over host-only source operations. */
export async function installNativeFs(ctx, {load, hostAction, material}) {
  const {FileSystem, FsError} = await load('dsh-fs');
  const {Service} = await load('cordis');
  const plugin = await load('dsh-tool-fs');
  const task = material.task;
  const allowed = new Set([...task.approved_readable_files, ...task.scope.create]);
  const cache = new Map();
  let feedback;
  const deny = text => { throw new FsError(text, 'FS_PERMISSION_DENIED'); };
  class FixedDirectory extends Service {
    constructor(context) { super(context, 'workingDirectory'); }
    async ensure(_agent, signal) {
      if(signal?.aborted) throw new FsError('Cancelled', 'FS_ABORTED');
      return process.cwd();
    }
  }
  new FixedDirectory(ctx);
  class ScopedFs extends FileSystem {
    async resolve(path, options = {}) {
      if(options.signal?.aborted) throw new FsError('Cancelled', 'FS_ABORTED');
      if(typeof path !== 'string' || !allowed.has(path) || path.includes('\\') || path.split('/').some(p => p === '..' || p === '.')) deny('Exact approved relative file required');
      return {targetKey:path, displayPath:path};
    }
    processPath(target) { return target.displayPath; }
    contains(parent, child) { return parent.targetKey === child.targetKey; }
    fileUrl() { deny('File URL unavailable'); }
    async stat(target) {
      const item = cache.get(target.targetKey);
      return item ? {type:'file',version:item.version,size:Buffer.byteLength(item.content)} : undefined;
    }
    async readText(target) {
      const item = cache.get(target.targetKey);
      if(!item) deny('Native read must obtain host evidence first');
      return item.content;
    }
    async streamText(target) { return [await this.readText(target)]; }
    async writeText(target, content) {
      if(!task.scope.create.includes(target.targetKey)) deny('Full-file write only for approved new files; use edit for existing source');
      return this.mutate('native_create', target, {content});
    }
    async editText(target, request) {
      if(request.replaceAll) deny('replace_all not admitted in this candidate');
      return this.mutate('native_edit', target, {find:request.oldString,replace:request.newString});
    }
    async mutate(action, target, args) {
      feedback = await hostAction(action, {path:target.targetKey,...args}, 'native-fs');
      const outcome = feedback.tool_result?.native_outcome;
      if(!outcome) throw new FsError(JSON.stringify(feedback.tool_result), 'FS_IO_ERROR');
      cache.delete(target.targetKey);
      return outcome;
    }
  }
  new ScopedFs(ctx);
  // Preserve installed schemas/parsers/provider calls/rendering; append actual host check facts.
  const original = ctx.tools.register.bind(ctx.tools);
  ctx.tools.register = definition => {
    if(!['read','edit','write'].includes(definition.name)) deny('Unexpected native tool');
    const execute = definition.execute;
    const render = definition.output.render;
    return original({...definition, output:{...definition.output, render:(args,value) => [
      ...render(args,value), {type:'text',text:JSON.stringify({host_feedback:feedback})}
    ]}, execute:async (args,exec) => {
      if(exec.signal.aborted) throw new FsError('Cancelled', 'FS_ABORTED');
      feedback = undefined;
      try {
      if(definition.name === 'read') {
        const target = await ctx.fs.resolve(args.file_path, {signal:exec.signal});
        const start = args.offset ?? 1, limit = args.limit ?? 120;
        feedback = await hostAction('read', {path:target.targetKey,start_line:start,end_line:start+limit-1}, 'native-read');
        const evidence = feedback.tool_result;
        if(typeof evidence?.content !== 'string') throw new FsError(JSON.stringify(evidence), 'FS_IO_ERROR');
        if(!Number.isSafeInteger(evidence.total_lines) || evidence.total_lines > 200000 ||
           (start > evidence.total_lines && !(start === 1 && evidence.total_lines === 0)))
          throw new FsError('Native read offset outside bounded actual file', 'FS_NOT_FOUND');
        const text = evidence.content.split('\n').map(line => line.replace(/^\d+: /, '')).join('\n');
        const remaining=Math.max(0, evidence.total_lines - evidence.end_line);
        cache.set(target.targetKey, {version:evidence.version_ref ?? evidence.sha256, content:'\n'.repeat(start-1)+text+'\n'.repeat(remaining+1)});
      }
      return await execute(args,exec);
      } catch(error) {
        if(!feedback) await hostAction('native_denied', {reason:String(error)}, 'native-denied');
        throw error;
      }
    }});
  };
  try {
    plugin.apply(ctx, {read:true,readImage:false,write:true,edit:true,readLimit:120,
      readMaxLineLength:2000,readMaxBytes:50000,readStreamMinSize:1000000});
  } finally { ctx.tools.register = original; }
}
