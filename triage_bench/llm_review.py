"""Blind offline label review. Prediction never opens answer keys or model runs."""

import hashlib
import copy
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import llm, workflow
from .dataset import read_jsonl
from .encoder import CLASSES, FIELDS
from .policy import OPTIONS, TEXT, priority
from .runner import NoRedirect, redact_secret

PROTOCOL = 'northstar-blind-llm-review-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def public_packet(record):
    # Same explicit nested allowlist as the compact workflow. No IDs, labels,
    # family names, prior model answers, or author rationales enter the request.
    state = json.loads(workflow.request_body(record, 'unused')['state'])
    del state['policy']
    return state


def system_prompt():
    return llm.system_prompt().rsplit('Return only one JSON object', 1)[0] + '''
You are an offline reviewer of fictional development incidents. Review only the
facts supplied at decision time. This is initial triage, not final root cause.
Select the best supported answer for each field. Do not repair contradictions by
inventing facts. Compute priority from the stated structured impact even when
the narrative conflicts with it; flag that conflict separately.
Return only a JSON object with exactly these keys:
"answers": the four allowed string decisions;
"evidence": an object with the same four field keys, each a nonempty list of
objects with exactly "path" and "quote". Paths are JSON pointers into the packet,
such as /observations/0/detail or /service_impact/status. Quotes must be exact
nonempty substrings of the cited string, or the string form of a scalar value.
"rationale": a short evidence-based explanation of the initial decisions;
"input_issues": a list of objects with exactly "path", "issue", and
"suggested_correction". Flag material contradictions, underspecified facts, or
invalid scope/impact descriptions. Use an existing packet path. Suggest what
needs clarification, not an invented corrected measurement. Empty if none;
"unresolved_questions": a list of specific questions that prevent reliable
labeling of this input, empty if none. Missing domain evidence can itself justify
noc/gather_evidence/yes without making the input unlabelable.
Do not return alternative answers, confidence scores, or additional keys.
'''


def request_body(record, model, reasoning_effort='none'):
    body = {'model': model, 'messages': [
        {'role': 'system', 'content': system_prompt()},
        {'role': 'user', 'content': 'Incident packet:\n' + json.dumps(public_packet(record), ensure_ascii=False, sort_keys=True)},
    ]}
    if reasoning_effort != 'default':
        body['reasoning_effort'] = reasoning_effort
    return body


def pointer(packet, path):
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('Evidence requires a packet JSON pointer')
    value = packet
    try:
        for part in path[1:].split('/'):
            part = part.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if not part.isdecimal() or (len(part) > 1 and part.startswith('0')):
                    raise ValueError('Invalid array pointer')
                value = value[int(part)]
            else:
                value = value[part]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f'Unknown packet pointer: {path}') from exc
    return value


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def normalize(response, packet, structural_citations=False):
    choice = response['choices'][0]
    if choice.get('finish_reason') != 'stop':
        raise ValueError('Review response did not finish normally')
    content = choice['message']['content']
    if not isinstance(content, str):
        raise ValueError('Review response has no text')
    review = json.loads(content)
    json.dumps(review, allow_nan=False)
    if not isinstance(review, dict) or set(review) != {'answers', 'evidence', 'rationale', 'input_issues', 'unresolved_questions'}:
        raise ValueError('Review response has an invalid schema')
    if not isinstance(review['answers'], dict) or set(review['answers']) != set(OPTIONS):
        raise ValueError('Review needs all four decisions')
    for field, allowed in OPTIONS.items():
        if not isinstance(review['answers'][field], str) or review['answers'][field] not in allowed:
            raise ValueError(f'Invalid review answer: {field}')
    if not nonblank(review['rationale']):
        raise ValueError('Review rationale is required')
    if not isinstance(review['evidence'], dict) or set(review['evidence']) != set(OPTIONS):
        raise ValueError('Every decision requires cited evidence')
    for citations in review['evidence'].values():
        if not isinstance(citations, list) or not citations:
            raise ValueError('Every decision requires cited evidence')
        for citation in citations:
            if not isinstance(citation, dict) or set(citation) != {'path', 'quote'} or not nonblank(citation['quote']):
                raise ValueError('Invalid evidence citation')
            value = pointer(packet, citation['path'])
            text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            matches = citation['quote'] in text
            if structural_citations and isinstance(value, str) and not matches:
                try:
                    quoted = json.loads(citation['quote'])
                    matches = isinstance(quoted, str) and quoted == value
                except ValueError:
                    pass
            if structural_citations and not isinstance(value, (str, list, dict)):
                try:
                    quoted = json.loads(citation['quote'])
                    matches = json.dumps(quoted, allow_nan=False) == json.dumps(value, allow_nan=False)
                except (ValueError, TypeError):
                    matches = False
            if structural_citations and isinstance(value, (list, dict)):
                try:
                    quoted = json.loads(citation['quote'])
                    # Strict JSON type equality avoids true == 1 acceptance.
                    matches = (json.dumps(quoted, sort_keys=True, allow_nan=False)
                               == json.dumps(value, sort_keys=True, allow_nan=False))
                except (ValueError, TypeError):
                    matches = False
            if not matches:
                raise ValueError(f'Citation quote not present at {citation["path"]}')
    if not isinstance(review['input_issues'], list):
        raise ValueError('Input issues must be a list')
    for issue in review['input_issues']:
        if not isinstance(issue, dict) or set(issue) != {'path', 'issue', 'suggested_correction'} or not all(nonblank(value) for value in issue.values()):
            raise ValueError('Invalid input issue')
        pointer(packet, issue['path'])
    questions = review['unresolved_questions']
    if not isinstance(questions, list) or any(not nonblank(question) for question in questions):
        raise ValueError('Invalid unresolved questions')
    return review


def policy_issues(answers, packet):
    issues = []
    if answers['priority'] != priority(packet['service_impact']):
        issues.append('priority conflicts with structured-impact policy')
    if tuple(answers[field] for field in FIELDS) not in CLASSES:
        issues.append('owner/check/evidence combination is outside the seven supported dispositions')
    return issues


def run(inputs, output, model, endpoint, api_key, reasoning_effort='none',
        context_tokens=32768, timeout=60, min_interval=3.5, progress=None, review_protocol=None):
    """Serial immutable review, with errors preserved and no retries or labels."""
    records = read_jsonl(inputs)
    if not records or len({record['id'] for record in records}) != len(records):
        raise ValueError('Review inputs must have distinct incident IDs')
    output = Path(output)
    if output.exists() or output.with_suffix('.meta.json').exists():
        raise FileExistsError('Choose a new review output path')
    url = urllib.parse.urlparse(endpoint)
    if (url.username or url.password or url.query or url.fragment or not url.hostname
            or (url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in {'localhost', '127.0.0.1', '::1'}))):
        raise ValueError('Use HTTPS or a loopback endpoint without credentials or query parameters')
    if not model or not api_key or any(ord(c) < 32 for c in api_key):
        raise ValueError('A model and valid bearer token are required')
    if reasoning_effort not in {'default', 'none', 'low', 'medium', 'high'}:
        raise ValueError('Invalid reasoning effort')
    if not 0 <= min_interval <= 60 or not 0 < timeout <= 60:
        raise ValueError('Interval and timeout must be within 60 seconds')
    if review_protocol is None:
        import sys
        review_protocol = sys.modules[__name__]
    meta = {'request_protocol': review_protocol.PROTOCOL, 'requested_model': model, 'endpoint': endpoint,
            'reasoning_effort': reasoning_effort, 'input_sha256': sha(inputs),
            'prompt_sha256': hashlib.sha256(review_protocol.system_prompt().encode()).hexdigest(),
            'renderer_sha256': sha(workflow.__file__), 'review_source_sha256': sha(review_protocol.__file__),
            'runner_source_sha256': sha(__file__),
            'policy_sha256': hashlib.sha256(TEXT.encode()).hexdigest(),
            'started_at': datetime.now(timezone.utc).isoformat(), 'records': len(records),
            'execution': f'serial; at least {min_interval}s between starts; no warmup or retries',
            'declared_context_tokens': context_tokens,
            'evaluation_use': 'LLM review of development inputs; not independent accuracy or specialist review'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.source.py').write_bytes(Path(review_protocol.__file__).read_bytes())
    output.with_suffix('.runner.py').write_bytes(Path(__file__).read_bytes())
    output.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    opener = urllib.request.build_opener(NoRedirect())
    started = time.perf_counter()
    previous_start = started - min_interval
    failed = 0
    with output.open('x') as stream:
        for index, record in enumerate(records, 1):
            delay = min_interval - (time.perf_counter() - previous_start)
            if delay > 0:
                time.sleep(delay)
            previous_start = time.perf_counter()
            row = {'id': record['id'], 'status': 'error'}
            try:
                body = json.dumps(review_protocol.request_body(record, model, reasoning_effort), ensure_ascii=False).encode()
                row['request_sha256'] = hashlib.sha256(body).hexdigest()
                if len(body) + 512 > context_tokens:
                    raise ValueError('Context byte-bound preflight failed; no request sent')
                request = urllib.request.Request(llm.chat_endpoint(endpoint), data=body, method='POST',
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json',
                             'User-Agent': 'NorthstarIncidentBench/0.1', 'Authorization': 'Bearer ' + api_key})
                with opener.open(request, timeout=timeout) as response:
                    raw = json.load(response)
                json.dumps(raw, allow_nan=False)
                raw = redact_secret(raw, api_key)
                row.update(raw_response=raw, resolved_model=raw.get('model'), usage=raw.get('usage'))
                review = review_protocol.normalize(raw, public_packet(record))
                row.update(status='ok', review=review, predictions=review['answers'],
                           policy_issues=policy_issues(review['answers'], public_packet(record)))
            except urllib.error.HTTPError as exc:
                row['error'] = f'HTTP {exc.code}'
                exc.close()
            except (ValueError, KeyError, IndexError, TypeError, OSError) as exc:
                row['error'] = redact_secret(f'{type(exc).__name__}: {exc}', api_key)
            failed += row['status'] != 'ok'
            row['latency_ms'] = (time.perf_counter() - previous_start) * 1000
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            stream.flush()
            if progress:
                progress(index, len(records), row)
    meta.update(failed_records=failed, successful_records=len(records) - failed,
                wall_seconds=time.perf_counter() - started, prediction_sha256=sha(output))
    output.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    return meta


def compare(records, labels, rows):
    """Open references only after inference; disagreement never changes inputs."""
    packets = {record['id']: record for record in records}
    keys = {key['id']: key for key in labels}
    predictions = {row['id']: row for row in rows}
    if (len(packets) != len(records) or len(keys) != len(labels) or len(predictions) != len(rows)
            or set(packets) != set(keys) or not set(predictions).issubset(packets)):
        raise ValueError('Invalid or mismatched review/reference IDs')
    field_agreement = dict.fromkeys(OPTIONS, 0)
    agreed = failed = missing = flagged = 0
    cases = []
    for record_id, record in packets.items():
        key = keys[record_id]
        row = predictions.get(record_id)
        reasons = []
        differences = {}
        if row is None:
            missing += 1
            reasons.append('missing review')
        elif row['status'] != 'ok':
            failed += 1
            reasons.append('failed review')
        else:
            answers = row['review']['answers']
            for field in OPTIONS:
                matches = answers[field] in key['accepted_answers'][field]
                field_agreement[field] += matches
                if not matches:
                    differences[field] = {'review': answers[field], 'draft_accepted': key['accepted_answers'][field]}
            agreed += not differences
            if differences:
                reasons.append('disagrees with provisional draft label')
            if row['review']['input_issues']:
                reasons.append('reviewer flags input corrections')
            if row['review']['unresolved_questions']:
                reasons.append('reviewer leaves labeling questions unresolved')
            reasons.extend(policy_issues(answers, public_packet(record)))
        flagged += bool(reasons)
        cases.append({'id': record_id, 'incident_family_id': key['incident_family_id'],
                      'pair_id': key.get('pair_id'), 'differences': differences,
                      'requires_adjudication': bool(reasons), 'reasons': reasons})
    return {'metric': 'agreement with provisional AI-authored labels, not independent accuracy',
            'records': len(records), 'all_four_agree': agreed, 'field_agreement': field_agreement,
            'failed_records': failed, 'missing_records': missing,
            'requires_adjudication': flagged, 'candidate_label_records': len(records) - flagged,
            'cases': cases}


def verify_run(records, rows, meta, input_hash):
    import sys
    protocol = sys.modules[__name__]
    if meta['request_protocol'] != PROTOCOL:
        from . import llm_review_v2
        protocol = llm_review_v2
    if meta['input_sha256'] != input_hash or meta['request_protocol'] != protocol.PROTOCOL:
        raise ValueError('Review protocol or inputs differ')
    packets = {record['id']: record for record in records}
    if len({row['id'] for row in rows}) != len(rows) or any(row['id'] not in packets for row in rows):
        raise ValueError('Invalid review IDs')
    if meta['prompt_sha256'] != hashlib.sha256(protocol.system_prompt().encode()).hexdigest():
        raise ValueError('Review prompt differs')
    if meta['renderer_sha256'] != sha(workflow.__file__):
        raise ValueError('Review input renderer differs')
    for row in rows:
        record = packets[row['id']]
        body = json.dumps(protocol.request_body(record, meta['requested_model'], meta['reasoning_effort']), ensure_ascii=False).encode()
        if row['request_sha256'] != hashlib.sha256(body).hexdigest():
            raise ValueError('Saved review request differs from blind packet')
        if row['status'] == 'ok':
            review = protocol.normalize(row['raw_response'], public_packet(record))
            if (review != row['review'] or review['answers'] != row['predictions']
                    or policy_issues(review['answers'], public_packet(record)) != row['policy_issues']):
                raise ValueError('Review differs from its saved provider response')
    if (meta['records'] != len(records) or meta['failed_records'] != sum(row['status'] != 'ok' for row in rows)
            or meta['successful_records'] != sum(row['status'] == 'ok' for row in rows)):
        raise ValueError('Review counts differ')


def export(inputs, labels, predictions, output_dir):
    """Save portable raw evidence and only undisputed candidate labels."""
    records, keys, rows = read_jsonl(inputs), read_jsonl(labels), read_jsonl(predictions)
    meta = json.loads(Path(predictions).with_suffix('.meta.json').read_text())
    if meta['prediction_sha256'] != sha(predictions):
        raise ValueError('Saved review predictions changed')
    verify_run(records, rows, meta, sha(inputs))
    comparison = compare(records, keys, rows)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    snapshot = {'study': 'Northstar blind LLM development review', 'input_sha256': sha(inputs),
                'draft_label_sha256': sha(labels), 'labels_specialist_reviewed': False,
                'evaluation_use': 'development only; teacher agreement is not independent accuracy',
                'draft_labels': keys, 'metadata': meta, 'reviews': rows, 'comparison': comparison}
    source_path = Path(predictions).with_suffix('.source.py')
    source = source_path.read_text() if source_path.exists() else Path(__file__).read_text()
    if hashlib.sha256(source.encode()).hexdigest() != meta['review_source_sha256']:
        raise ValueError('Review source snapshot differs from run metadata')
    snapshot['review_source'] = source
    if 'source_prediction_sha256' in meta:
        snapshot['source_prediction_text'] = Path(predictions).with_suffix('.original.jsonl').read_text()
        snapshot['source_reviews'] = [json.loads(line) for line in snapshot['source_prediction_text'].splitlines()]
        snapshot['source_metadata'] = json.loads(Path(predictions).with_suffix('.original.meta.json').read_text())
    if 'runner_source_sha256' in meta:
        runner_source = Path(predictions).with_suffix('.runner.py').read_text()
        if hashlib.sha256(runner_source.encode()).hexdigest() != meta['runner_source_sha256']:
            raise ValueError('Review runner source snapshot differs')
        snapshot['runner_source'] = runner_source
    (output_dir / 'evidence.json').write_text(json.dumps(snapshot, indent=2, allow_nan=False) + '\n')
    selected = {case['id'] for case in comparison['cases'] if not case['requires_adjudication']}
    rows_by_id = {row['id']: row for row in rows}
    key_by_id = {key['id']: key for key in keys}
    candidates = []
    for record in records:
        if record['id'] in selected:
            answers = rows_by_id[record['id']]['review']['answers']
            candidates.append({'id': record['id'], 'split': 'development_candidate',
                               'incident_family_id': key_by_id[record['id']]['incident_family_id'],
                               'pair_id': key_by_id[record['id']].get('pair_id'), 'labels': answers,
                               'accepted_answers': {field: [answer] for field, answer in answers.items()},
                               'review_status': 'LLM-reviewed development candidate; no specialist review',
                               'review_model': rows_by_id[record['id']]['resolved_model'],
                               'review_prediction_sha256': meta['prediction_sha256']})
    (output_dir / 'candidate.labels.jsonl').write_text(''.join(json.dumps(key) + '\n' for key in candidates))
    (output_dir / 'candidate.inputs.jsonl').write_text(''.join(json.dumps(record) + '\n' for record in records if record['id'] in selected))
    disputed = {case['id'] for case in comparison['cases'] if case['requires_adjudication']}
    (output_dir / 'adjudication.inputs.jsonl').write_text(''.join(json.dumps(record) + '\n' for record in records if record['id'] in disputed))
    (output_dir / 'adjudication.labels.jsonl').write_text(''.join(json.dumps(key) + '\n' for key in keys if key['id'] in disputed))
    artifacts = ('candidate.labels.jsonl', 'candidate.inputs.jsonl', 'adjudication.inputs.jsonl', 'adjudication.labels.jsonl')
    (output_dir / 'artifacts.json').write_text(json.dumps({name: sha(output_dir / name) for name in artifacts}, indent=2) + '\n')
    return snapshot


def verify_evidence(snapshot_path, inputs, labels):
    snapshot = json.loads(Path(snapshot_path).read_text())
    records, keys = read_jsonl(inputs), read_jsonl(labels)
    if (snapshot['input_sha256'] != sha(inputs) or snapshot['draft_label_sha256'] != sha(labels)
            or snapshot['draft_labels'] != keys or snapshot['labels_specialist_reviewed'] is not False
            or snapshot['evaluation_use'] != 'development only; teacher agreement is not independent accuracy'):
        raise ValueError('Review evidence dataset or provenance differs')
    verify_run(records, snapshot['reviews'], snapshot['metadata'], sha(inputs))
    if hashlib.sha256(snapshot['review_source'].encode()).hexdigest() != snapshot['metadata']['review_source_sha256']:
        raise ValueError('Archived review source differs from run metadata')
    if 'runner_source_sha256' in snapshot['metadata']:
        if hashlib.sha256(snapshot['runner_source'].encode()).hexdigest() != snapshot['metadata']['runner_source_sha256']:
            raise ValueError('Archived runner source differs from run metadata')
    if 'source_reviews' in snapshot:
        meta = snapshot['metadata']
        if (snapshot['source_metadata']['prediction_sha256'] != meta['source_prediction_sha256']
                or snapshot['source_metadata']['input_sha256'] != snapshot['input_sha256']):
            raise ValueError('Offline revalidation source identity differs')
        if (hashlib.sha256(snapshot['source_prediction_text'].encode()).hexdigest() != meta['source_prediction_sha256']
                or [json.loads(line) for line in snapshot['source_prediction_text'].splitlines()] != snapshot['source_reviews']):
            raise ValueError('Offline revalidation source responses changed')
        if revalidate_rows(records, snapshot['source_reviews']) != snapshot['reviews']:
            raise ValueError('Offline revalidation changed more than response validation')
    comparison = compare(records, keys, snapshot['reviews'])
    if comparison != snapshot['comparison']:
        raise ValueError('Recorded label agreement differs from reviews')
    return snapshot


def revalidate_rows(records, rows):
    """V2 diagnostic only: validate saved responses, preserve source outcomes."""
    from . import llm_review_v2
    packets = {record['id']: public_packet(record) for record in records}
    derived = copy.deepcopy(rows)
    for row in derived:
        row['source_status'] = row['status']
        row['source_error'] = row.get('error')
        if row['status'] == 'error' and 'raw_response' in row:
            try:
                review = llm_review_v2.normalize(row['raw_response'], packets[row['id']])
                row.update(status='ok', review=review, predictions=review['answers'],
                           policy_issues=policy_issues(review['answers'], packets[row['id']]))
                row.pop('error', None)
            except (ValueError, KeyError, IndexError, TypeError):
                pass
    return derived


def reconcile(primary, secondary, all_cases=False):
    """Independent second review can confirm decisions, never repair flagged facts."""
    expected = {case['id'] for case in primary['comparison']['cases'] if all_cases or case['requires_adjudication']}
    if primary['metadata']['requested_model'] == secondary['metadata']['requested_model']:
        raise ValueError('Adjudication needs a different requested model')
    if primary['metadata'].get('request_protocol') != secondary['metadata'].get('request_protocol'):
        raise ValueError('Reviewers must use the same review protocol')
    primary_keys = {key['id']: key for key in primary.get('draft_labels', [])}
    secondary_keys = {key['id']: key for key in secondary.get('draft_labels', [])}
    if secondary_keys and secondary_keys != {record_id: primary_keys[record_id] for record_id in expected}:
        raise ValueError('Reviewer reference cohorts differ')
    first = {row['id']: row for row in primary['reviews']}
    second = {row['id']: row for row in secondary['reviews']}
    if set(second) != expected:
        raise ValueError('Second review must cover every flagged case exactly once')
    first_cases = {case['id']: case for case in primary['comparison']['cases']}
    results = []
    for record_id, case in first_cases.items():
        row = first.get(record_id)
        reasons = []
        reviewers = [row] if record_id not in expected else [row, second[record_id]]
        for reviewer in reviewers:
            if reviewer is None or reviewer['status'] != 'ok':
                reasons.append('missing or failed reviewer response')
                continue
            if reviewer['review']['input_issues']:
                reasons.append('input correction remains unresolved')
            if reviewer['review']['unresolved_questions']:
                reasons.append('labeling question remains unresolved')
            reasons.extend(reviewer['policy_issues'])
        if record_id in expected and all(reviewer and reviewer['status'] == 'ok' for reviewer in reviewers):
            if reviewers[0]['predictions'] != reviewers[1]['predictions']:
                reasons.append('reviewers disagree on triage decisions')
            if (reviewers[0].get('resolved_model') and
                    reviewers[0].get('resolved_model') == reviewers[1].get('resolved_model')):
                reasons.append('gateway resolved both reviewers to the same model')
        results.append({'id': record_id, 'incident_family_id': case['incident_family_id'],
                        'pair_id': case['pair_id'], 'status': 'pending' if reasons else 'candidate',
                        'reasons': sorted(set(reasons)),
                        'answers': row['predictions'] if row and row['status'] == 'ok' else None,
                        'draft_differences': case['differences'],
                        'review_models': [reviewer.get('resolved_model') for reviewer in reviewers if reviewer]})
    return {'evaluation_use': 'LLM-reviewed development candidates; not independent accuracy',
            'records': len(results), 'second_review_records': len(expected),
            'candidate_records': sum(case['status'] == 'candidate' for case in results),
            'pending_records': sum(case['status'] == 'pending' for case in results),
            'cases': results}
