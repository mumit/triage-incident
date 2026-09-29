"""Inference receives public inputs only. No answer keys are read here."""
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .dataset import read_jsonl, write_jsonl
from . import llm
from .policy import OPTIONS, TEXT, priority, questions


def request_body(record, model):
    # Explicit allowlist prevents metadata/labels from being sent accidentally.
    return {'model': model, 'state': TEXT + '\nIncident packet:\n' + json.dumps(record['input'], ensure_ascii=False, sort_keys=True),
            'questions': questions()}


def redact_secret(value, secret):
    if not secret:
        return value
    if isinstance(value, str):
        return value.replace(secret, '[redacted]')
    if isinstance(value, list):
        return [redact_secret(item, secret) for item in value]
    if isinstance(value, dict):
        return {redact_secret(key, secret): redact_secret(item, secret) for key, item in value.items()}
    return value


def normalize(response):
    answers = response['answers']
    predictions, probabilities, confidence = {}, {}, {}
    for field, choices in OPTIONS.items():
        answer = answers[field]
        if field == 'insufficient_evidence' and 'noul' in answer:
            likelihood = answer['noul']
            if isinstance(likelihood, bool) or not isinstance(likelihood, (int, float)) or not math.isfinite(likelihood) or not 0 <= likelihood <= 1:
                raise ValueError('Invalid binary probability for insufficient_evidence')
            chosen = 'yes' if likelihood >= 0.5 else 'no'
            dist = {'yes': likelihood, 'no': 1 - likelihood}
        else:
            chosen = answer['choice']
            dist = answer.get('probabilities')
        if chosen not in choices:
            raise ValueError(f'Invalid choice for {field}')
        predictions[field] = chosen
        if dist is not None:
            if not isinstance(dist, dict) or set(dist) != set(choices):
                raise ValueError(f'Incomplete distribution for {field}')
            if any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1 for p in dist.values()):
                raise ValueError(f'Invalid probability for {field}')
            total = sum(dist.values())
            # Jev emits two-decimal probabilities. Independent rounding can move
            # a valid multi-option distribution a few hundredths from one.
            two_decimals = all(abs(p * 100 - round(p * 100)) < 1e-8 for p in dist.values())
            tolerance = max(0.001, len(choices) * 0.005 + 1e-8) if two_decimals else 0.001
            if total <= 0 or abs(total - 1) > tolerance:
                raise ValueError(f'Distribution for {field} sums to {total:.4f}, outside rounding tolerance')
            probabilities[field] = {choice: dist[choice] / total for choice in choices}
        if 'confidence' in answer:
            value = answer['confidence']
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'Invalid confidence for {field}')
            confidence[field] = value
    return predictions, probabilities, confidence


def baseline(packet):
    """Deliberately simple keyword routing, plus exact structured priority rule."""
    text = ' '.join(o['detail'] for o in packet['observations']).lower()
    if packet['service_impact']['status'] == 'none':
        owner, check, uncertain = 'noc', 'monitor', 'no'
    elif packet['service_impact']['status'] == 'unknown' or any(w in text for w in ['75 minutes old', 'cannot yet', 'timing alone', 'do not establish']):
        owner, check, uncertain = 'noc', ('verify_change' if 'change' in text or 'maintenance' in text else 'gather_evidence'), 'yes'
    else:
        owner = 'noc'
        for domain, words in [('power', ['battery', 'batteries', 'rectifier', 'breaker', 'dc ', 'generator', 'transfer switch']),
                              ('core', ['core', 'authentication', 'resolver', 'session service', 'mobility service', 'user-plane', 'policy-control']),
                              ('transport', ['aggregation', 'optical', 'crc', 'backhaul', 'non-fragmenting']),
                              ('ran', ['radio', 'antenna', 'handover', 'uplink interference', 'mobility failures', 'receive sensitivity'])]:
            if any(word in text for word in words):
                owner = domain
                break
        check = 'inspect_' + ('radio' if owner == 'ran' else owner) if owner != 'noc' else 'gather_evidence'
        uncertain = 'yes' if owner == 'noc' else 'no'
    return dict(initial_owner=owner, next_check=check, insufficient_evidence=uncertain,
                priority=priority(packet['service_impact']))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Endpoint redirects are not accepted; configure the final URL.')


def fetch_json(opener, request, timeout, provider, stop_event=None):
    """Retry only transient LLM rate limits; preserve one scored record per incident."""
    retries = 0
    while True:
        try:
            with opener.open(request, timeout=timeout) as response:
                return json.load(response), retries
        except urllib.error.HTTPError as exc:
            if provider != 'llm' or exc.code != 429 or retries >= 4:
                raise
            retries += 1
            retry_after = exc.headers.get('Retry-After')
            try:
                delay = float(retry_after)
            except (TypeError, ValueError):
                delay = 5 * 2 ** (retries - 1)
            delay = min(120, max(1, delay))
            exc.close()
            if stop_event is None:
                time.sleep(delay)
            elif stop_event.wait(delay):
                raise InterruptedError('Cancelled during gateway rate-limit wait')


def run(inputs, output, provider='baseline', model=None, endpoint=None, key_env=None,
        limit=None, timeout=60, context_tokens=None, deployment=None,
        api_key=None, progress=None, stop_event=None, reasoning_effort='none',
        decision_workflow=None):
    records = read_jsonl(inputs)
    if limit is not None:
        if limit < 1:
            raise ValueError('limit must be positive')
        records = records[:limit]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.with_suffix('.meta.json').exists():
        raise ValueError('Choose a new output path; runs are immutable.')
    if provider != 'baseline':
        if not model or not endpoint or not context_tokens or not deployment:
            raise ValueError('Model runs require --model, --endpoint, --context-tokens and --deployment.')
        u = urllib.parse.urlparse(endpoint)
        if u.username or u.password or u.query or u.fragment:
            raise ValueError('Endpoint must not contain credentials, query parameters or fragments.')
        if u.scheme != 'https' and not (u.scheme == 'http' and u.hostname in {'localhost', '127.0.0.1', '::1'}):
            raise ValueError('Use HTTPS except for a loopback server.')
    api_key = api_key or (os.environ.get(key_env) if key_env else None)
    if key_env and not api_key:
        raise ValueError(f'Set the {key_env} environment variable before running.')
    meta = {'provider': provider, 'requested_model': model, 'endpoint': endpoint,
            'deployment': deployment, 'declared_context_tokens': context_tokens,
            'input_file': str(inputs), 'input_sha256': hashlib.sha256(Path(inputs).read_bytes()).hexdigest(),
            'started_at': datetime.now(timezone.utc).isoformat(), 'records': len(records),
            'execution': ('serial; no warmup; up to four HTTP 429 retries with backoff'
                          if provider == 'llm' else
                          'serial; first request cold/unknown, remaining requests warm/unknown; no warmup or retries'),
            'policy_sha256': hashlib.sha256(TEXT.encode()).hexdigest(),
            'question_schema_sha256': hashlib.sha256(json.dumps(questions(), sort_keys=True).encode()).hexdigest(),
            'benchmark_version': '0.1.0'}
    if provider == 'llm':
        meta['request_protocol'] = 'openai-compatible-chat-completions-v1'
        meta['prompt_sha256'] = hashlib.sha256(llm.system_prompt().encode()).hexdigest()
        meta['reasoning_effort'] = reasoning_effort
    if decision_workflow is not None:
        if provider != 'jev':
            raise ValueError('The decomposed workflow requires the Jev provider')
        meta.update(decision_workflow.metadata())
        meta['question_schema_sha256'] = meta['workflow_question_sha256']
    output.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    opener = urllib.request.build_opener(NoRedirect())
    started = time.perf_counter()
    failures = 0
    attempted = 0
    with output.open('x') as stream:
        for record in records:
            if stop_event is not None and stop_event.is_set():
                break
            attempted += 1
            row = {'id': record['id'], 'status': 'ok', 'predictions': {}, 'probabilities': {}}
            t = time.perf_counter()
            try:
                if provider == 'baseline':
                    row['predictions'] = baseline(record['input'])
                else:
                    if decision_workflow is not None:
                        body = decision_workflow.request_body(record, model)
                    else:
                        body = llm.request_body(record, model, reasoning_effort) if provider == 'llm' else request_body(record, model)
                    body_bytes = json.dumps(body, ensure_ascii=False).encode()
                    # UTF-8 bytes are a deliberately conservative preflight proxy, not a tokenizer.
                    # Require reserve for server-specific wrappers as well.
                    if len(body_bytes) + 512 > context_tokens:
                        raise ValueError('Context preflight failed: request byte bound plus 512 exceeds declared context. No request sent.')
                    headers = {'Content-Type': 'application/json'}
                    if provider == 'llm':
                        # Fuel iX's Cloudflare edge rejects urllib's default
                        # Python-urllib user agent with HTTP 403 / code 1010.
                        headers.update({'Accept': 'application/json',
                                        'User-Agent': 'NorthstarIncidentBench/0.1'})
                    if api_key:
                        headers['Authorization'] = 'Bearer ' + api_key
                    request_url = llm.chat_endpoint(endpoint) if provider == 'llm' else endpoint
                    req = urllib.request.Request(request_url, data=body_bytes, headers=headers, method='POST')
                    raw, retries = fetch_json(opener, req, timeout, provider, stop_event)
                    # Python accepts NaN/Infinity in JSON by default. Reject them anywhere in
                    # the provider response before saving raw data or returning it to the app.
                    json.dumps(raw, allow_nan=False)
                    raw = redact_secret(raw, api_key)
                    if provider == 'llm':
                        row['predictions'] = llm.normalize(raw)
                    elif decision_workflow is not None:
                        row['predictions'], row['probabilities'], row['provider_confidence'] = decision_workflow.normalize(raw, record['input'])
                    else:
                        row['predictions'], row['probabilities'], row['provider_confidence'] = normalize(raw)
                        original_sums = {}
                        for field in OPTIONS:
                            answer = raw['answers'][field]
                            if 'noul' not in answer and isinstance(answer.get('probabilities'), dict):
                                original_sum = sum(answer['probabilities'].values())
                                if abs(original_sum - 1) > 1e-9:
                                    original_sums[field] = original_sum
                        if original_sums:
                            row['probability_original_sums'] = original_sums
                    row['resolved_model'] = raw.get('model')
                    row['usage'] = raw.get('usage')
                    row['raw_response'] = raw
                    row['request_sha256'] = hashlib.sha256(body_bytes).hexdigest()
                    if retries:
                        row['rate_limit_retries'] = retries
            except urllib.error.HTTPError as exc:
                error = f'HTTP {exc.code}'
                try:
                    if provider == 'llm' and exc.code == 403 and b'error code: 1010' in exc.read(2048):
                        error += ' (Cloudflare blocked the HTTP client signature; restart the updated app server)'
                finally:
                    exc.close()
                row.update(status='error', error=error)
            except (ValueError, KeyError, IndexError, TypeError, OSError) as exc:
                message = str(exc)
                if api_key:
                    message = message.replace(api_key, '[redacted]')
                row.update(status='error', error=f'{type(exc).__name__}: {message}')
            failures += int(row['status'] != 'ok')
            row['latency_ms'] = (time.perf_counter() - t) * 1000
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
            stream.flush()
            if progress:
                progress(attempted, len(records), row)
    meta['failed_records'] = failures
    meta['attempted_records'] = attempted
    meta['cancelled'] = attempted < len(records)
    meta['successful_records'] = attempted - failures
    meta['wall_seconds'] = time.perf_counter() - started
    output.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    return meta
