import assert from 'node:assert/strict';
import {test} from 'node:test';
import {createNativeAgent,llm} from '../benchmarks/strata_native_agent_core.mjs';

class ControlAdapter extends llm.LlmAdapter {
  calls = 0;
  constructor(mode) {super(); this.mode=mode;}
  async *stream(options) {
    this.calls++;
    assert.equal(options.provider,'strata-local');
    assert.equal(options.model,'iq3_s');
    if(this.mode === 'throw') throw new Error('CONTROL_NETWORK_FAILURE');
    if(this.mode === 'length') {yield {type:'finish',reason:{kind:'max-tokens'}}; return;}
    const block={type:'tool-call',id:'control-call',name:'kit_block',arguments:'{"reason":"control"}'};
    yield {type:'block-start',index:0,blockType:'tool-call'};
    yield {type:'block-end',index:0,block};
    yield {type:'finish',reason:{kind:this.mode==='partial-length'?'max-tokens':'tool-calls'}};
  }
}
for(const mode of ['tool','throw','length','partial-length']) {
  test('real native Agent lifecycle: '+mode,{timeout:3000}, async () => {
    const adapter=new ControlAdapter(mode);
    let dispatched=0;
    const native=await createNativeAgent({identity:{task_id:'control',unit_id:'control',run_id:'control-'+mode},
      adapter,prompt:'Offline control, use kit tools.',authorize:()=>true,
      dispatch:async()=>{dispatched++; return {host_handoff_verified:true};}});
    try {
      native.agent.followup(llm.createUserMessage({source:{kind:'user'},content:[{type:'text',text:'control'}]}));
      await native.agent.whenIdle();
      assert.equal(adapter.calls,1);
      assert.equal(dispatched,mode==='tool'?1:0);
      const events=native.agent.session.snapshotEvents();
      assert.ok(events.length>0);
    } finally {await native.dispose();}
  });
}

test('native cancellation reaches adapter and never dispatches tools',{timeout:3000},async()=>{
  let entered;
  const started=new Promise(r=>{entered=r;});
  let aborted=false,dispatched=0;
  const adapter=new class extends llm.LlmAdapter {
    async *stream(options) {
      entered();
      await new Promise(resolve=>options.signal.addEventListener('abort',()=>{aborted=true;resolve();},{once:true}));
      yield {type:'finish',reason:{kind:'stop'}};
    }
  }();
  const native=await createNativeAgent({identity:{task_id:'cancel',unit_id:'cancel',run_id:'native-cancel'},adapter,
    prompt:'Offline cancellation',authorize:()=>true,dispatch:async()=>{dispatched++;return {};}});
  try {
    native.agent.followup(llm.createUserMessage({source:{kind:'user'},content:[{type:'text',text:'control'}]}));
    await started;
    native.agent.cancel({kind:'user'});
    await native.agent.whenIdle();
    assert.equal(aborted,true);
    assert.equal(dispatched,0);
  } finally {await native.dispose();}
});
