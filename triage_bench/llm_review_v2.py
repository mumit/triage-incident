"""Versioned review rubric: labelability is distinct from diagnostic uncertainty."""

from . import llm_review

PROTOCOL = 'northstar-blind-llm-review-v2'


def system_prompt():
    prompt = llm_review.system_prompt()
    prompt = prompt.replace(
        'nonempty substrings of the cited string, or the string form of a scalar value.',
        'nonempty substrings of the cited string, or the JSON form of a scalar value. '
        'For an array or object, quote the entire JSON value; whitespace and object key order do not matter. '
        'Prefer a scalar leaf path when possible.')
    prompt = prompt.replace(
        'Flag material contradictions, underspecified facts, or\ninvalid scope/impact descriptions.',
        'Flag defects in the authored record that prevent a justified policy label, such as '
        'incompatible impact status and service wording, malformed facts, or ambiguous definitions. '
        'Do not flag missing operational evidence merely because a diagnosis is unknown.')
    return prompt + '''
Labelability rubric:
- Missing current domain telemetry is a valid input. It can support retaining
  NOC and gathering evidence. Do not request new telemetry as an input correction
  or unresolved labeling question when this policy disposition is justified.
- Two explicitly unresolved current measurements can validly conflict. Preserve
  both as facts about what sources report; do not reconcile them by inventing a
  reading. Such conflict can justify NOC triage without an authoring defect.
- Absence of an alarmed asset from an explicitly complete dependency graph is
  valid negative evidence. Do not request that an unrelated dependency be added.
- Unknown actual change scope can justify scope verification when the approved
  scope intersects affected services. Distinguish this from change timing alone.
- A current independent domain diagnosis can justify domain inspection despite
  a recent change. A title does not override verified change scope.
- Use unresolved_questions only when you cannot choose a policy disposition
  from the facts, not for telemetry that the selected next_check would collect.
- If two diagnostic actions remain equally justified and the policy gives no
  preference, choose one and state the ambiguity as an unresolved labeling question.
These are general policy-review distinctions, not reference answers for a case.
'''


def request_body(record, model, reasoning_effort='none'):
    body = llm_review.request_body(record, model, reasoning_effort)
    body['messages'][0]['content'] = system_prompt()
    return body


def normalize(response, packet):
    return llm_review.normalize(response, packet, structural_citations=True)
