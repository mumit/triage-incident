"""Input-only control: decomposed-workflow state with original Jev questions.

Question instructions, candidate criteria, and response normalization are
unchanged. Priority is the model's answer; policy replacement is an offline
diagnostic recorded separately.
"""

import hashlib
import json
from pathlib import Path

from . import workflow
from .policy import questions
from .runner import normalize as original_normalize


def request_body(record, model):
    body = workflow.request_body(record, model)
    body['questions'] = questions()
    return body


def normalize(response, packet):
    return original_normalize(response)


def metadata():
    return {
        'request_protocol': 'northstar-compact-original-jev-v1',
        'workflow_question_sha256': hashlib.sha256(json.dumps(questions(), sort_keys=True).encode()).hexdigest(),
        'workflow_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'input_renderer_source_sha256': hashlib.sha256(Path(workflow.__file__).read_bytes()).hexdigest(),
        'priority_source': 'model prediction; no priority replacement during inference',
        'no_autoregressive_calls': True,
    }
