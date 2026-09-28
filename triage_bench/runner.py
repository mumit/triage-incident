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
from .policy import OPTIONS, TEXT, priority, questions


def request_body(record, model):
    # Explicit allowlist prevents metadata/labels from being sent accidentally.
    return {'model': model, 'state': TEXT + '\nIncident packet:\n' + json.dumps(record['input'], ensure_ascii=False, sort_keys=True),
            'questions': questions()}


def normalize(response):
    answers = response['answers']
    predictions, probabilities, confidence = {}, {}, {}
    for field, choices in OPTIONS.items():
        answer = answers[field]
        chosen = answer['choice']
        if chosen not in choices:
            raise ValueError(f'Invalid choice for {field}')
        predictions[field] = chosen
        dist = answer.get('probabilities')
        if dist is not None:
            if not isinstance(dist, dict) or set(dist) != set(choices):
                raise ValueError(f'Incomplete distribution for {field}')
            if any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1 for p in dist.values()):
                raise ValueError(f'Invalid probability for {field}')
            if abs(sum(dist.values()) - 1) > 0.001:
                raise ValueError(f'Distribution does not sum to one for {field}')
            probabilities[field] = dist
        if 'confidence' in answer:
            confidence[field] = answer['confidence']
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


def run(inputs, output, provider='baseline', model=None, endpoint=None, key_env=None,
        limit=None, timeout=60, context_tokens=None, deployment=None,
        api_key=None, progress=None, stop_event=None):
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
            'execution': 'serial; first request cold/unknown, remaining requests warm/unknown; no warmup or retries',
            'policy_sha256': hashlib.sha256(TEXT.encode()).hexdigest(), 'benchmark_version': '0.1.0'}
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
                    body = request_body(record, model)
                    body_bytes = json.dumps(body, ensure_ascii=False).encode()
                    # UTF-8 bytes are a deliberately conservative preflight proxy, not a tokenizer.
                    # Require reserve for server-specific wrappers as well.
                    if len(body_bytes) + 512 > context_tokens:
                        raise ValueError('Context preflight failed: request byte bound plus 512 exceeds declared context. No request sent.')
                    headers = {'Content-Type': 'application/json'}
                    if api_key:
                        headers['Authorization'] = 'Bearer ' + api_key
                    req = urllib.request.Request(endpoint, data=body_bytes, headers=headers, method='POST')
                    with opener.open(req, timeout=timeout) as resp:
                        raw = json.load(resp)
                    row['predictions'], row['probabilities'], row['provider_confidence'] = normalize(raw)
                    row['resolved_model'] = raw.get('model')
                    row['usage'] = raw.get('usage')
                    row['raw_response'] = raw
                    row['request_sha256'] = hashlib.sha256(body_bytes).hexdigest()
            except urllib.error.HTTPError as exc:
                row.update(status='error', error=f'HTTP {exc.code}')
            except (ValueError, KeyError, TypeError, OSError) as exc:
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
