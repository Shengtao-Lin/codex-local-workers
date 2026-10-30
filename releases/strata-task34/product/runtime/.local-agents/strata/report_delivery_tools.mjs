/** Expose existing host bounds; no permissions or success criteria are added. */
export function deliveryTools(tools,binding=false,investigation=false,compact=false) {
  const selected=structuredClone(tools);
  const fields=selected.kit_report.properties;
  fields.summary.maxLength=6000;
  fields.status.enum=['answered','insufficient_evidence'];
  for(const field of ['findings','evidence','unknowns']) fields[field].maxItems=24;
  fields.unknowns.items={type:'string',minLength:1,maxLength:2000};
  selected.kit_report.description+=' Summary maximum6000 characters; each report array maximum24 items. Cite representative observed lines;unknowns separately. Primary reads the full archive;host makes a marked preview.';
  selected.kit_read.description+=' Host returns at most120 lines and marks clipped windows;only actual displayed lines are evidence.';
  if(binding) {
    fields.evidence.items={type:'object',properties:{path:{type:'string',minLength:1},line:{type:'integer',minimum:1}},required:['path','line'],additionalProperties:false};
    selected.kit_report.description='Return a read-only report,never final acceptance. Status answered or insufficient_evidence. summary1..6000 characters;findings/evidence/unknowns arrays maximum24 items each;unknowns strings1..2000. Evidence entries are {path,line},only approved source lines already observed in the current version;host binds their exact quotes. Do not send a quote field. Findings entries are {contract_id,severity,description,evidence_index};severity critical/major/info;description1..3000;evidence_index zero-based. No defect findings for answered;state missing evidence in unknowns. All mechanical errors are rejected together;resubmit a complete report.';
  }
  if(investigation) selected.kit_report.description=selected.kit_report.description.replace('No defect findings for answered;', 'answered means the investigation question was addressed and may include source-backed findings,including defects;this is never change acceptance;');
  if(compact) {
    delete fields.findings;
    selected.kit_report.description='Return status,summary,evidence,unknowns only. Status answered or insufficient_evidence. Give the complete concise answer and any supported problems in summary (1..6000 characters),representative observed {path,line} citations in evidence (max24),explicit unknowns as strings (max24,each1..2000). Host binds exact current quotes. No findings array,contract IDs,severity or numeric cross-references are needed. Missing evidence limits the answer;reporting never accepts work.';
  }
  return selected;
}

export function deliveryPrompt(prompt,binding=false,investigation=false,compact=false) {
  let selected=binding?prompt.replace('Every evidence citation must be a line actually shown by read/search, with exact trimmed quote.',
    'Every evidence citation supplies only {path,line} for a current approved line actually shown by read/search. The host binds exact source quotes;do not transcribe or supply quote fields.'):prompt;
  if(investigation) selected=selected.replace('Report only concrete contract defects; uncertainty or missing evidence is insufficient_evidence, not a speculative defect.', 'Report source-backed observations and findings;answered means the question is addressed,including any discovered defects. State missing evidence in unknowns and do not turn uncertainty into a defect.')
    .replace('Report pass_to_primary only when evidence supports the change; Primary still independently accepts.', 'Use answered or insufficient_evidence. Primary independently evaluates the complete investigation;no report accepts a change.');
  if(compact) selected=selected.replace('Findings reference the supplied contract IDs and zero-based evidence entries.', 'Give supported observations or problems in the summary with source locations;use the evidence array for representative source citations. No separate findings array or numeric evidence mapping.');
  return selected;
}
