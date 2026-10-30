/** Opt-in review wire only; source binding never verifies a semantic claim. */
export function reviewTools(tools, diagnostic=false) {
  const selected=structuredClone(tools);
  const fields=selected.kit_report.properties;
  fields.status.enum=diagnostic?['rework','insufficient_evidence']:['pass_to_primary','rework','insufficient_evidence'];
  fields.summary.minLength=1;
  fields.summary.maxLength=6000;
  for(const field of ['findings','evidence','unknowns']) fields[field].maxItems=24;
  fields.evidence.items={type:'object',properties:{path:{type:'string',minLength:1},line:{type:'integer',minimum:1}},required:['path','line'],additionalProperties:false};
  fields.unknowns.items={type:'string',minLength:1,maxLength:2000};
  fields.findings.items={type:'object',properties:{contract_id:{type:'string'},severity:{type:'string',enum:['critical','major','info']},description:{type:'string',minLength:1,maxLength:3000},evidence_index:{type:'integer',minimum:0}},required:['contract_id','severity','description','evidence_index'],additionalProperties:false};
  selected.kit_report.description='Return the independent REVIEW report. Status pass_to_primary, rework, or insufficient_evidence. No findings for pass;rework needs a concrete source-backed contract defect. Evidence entries are {path,line} for approved current lines actually read;host supplies exact source quotes but does not verify your interpretation. Cite each changed file for pass. Findings reference supplied contract IDs and zero-based evidence entries. State uncertainty in unknowns;do not convert speculation to a defect. Summary1..6000 characters;arrays at most24 items. Reporting never accepts a change or claims test execution.';
  selected.kit_read.description+=' Host clips oversized windows to120 lines with next_start_line;only displayed lines are evidence.';
  if(diagnostic) selected.kit_report.description=selected.kit_report.description.replace('Status pass_to_primary, rework, or insufficient_evidence.', 'Non-accepting failed-draft diagnosis: only rework or insufficient_evidence. PASS and acceptance are prohibited.');
  return selected;
}

export function reviewPrompt(prompt) {
  return prompt.replace('You are one read-only local research/review subagent.', 'You are one independent read-only local code review subagent.')
    .replace('Investigate the single supplied question, or independently review', 'Independently review')
    .replace('Every evidence citation must be a line actually shown by read/search, with exact trimmed quote.', 'Every evidence citation supplies {path,line} for a current approved line actually shown by read/search. Host binds its exact quote;do not supply a quote field. This proves source identity,not the correctness of your claim.');
}
