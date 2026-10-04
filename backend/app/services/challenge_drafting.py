"""Provider-neutral challenge drafting with a deterministic offline fallback."""

import json
import os
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def _fallback(problem: str, language: str) -> dict[str, Any]:
    # The fallback deliberately contains no invented baseline or target values.
    if language == 'mr':
        return {
            'outcomes': ['सेवा वितरणातील अडथळे कमी करणे (पडताळणी आवश्यक)'],
            'metrics': ['निर्धारित कालावधीत पूर्ण झालेल्या सेवा विनंत्या; मोजमाप पद्धत अधिकाऱ्याने निश्चित करावी'],
            'baseline': 'Baseline unavailable',
            'test_duration_days': None,
            'acceptance_criteria': ['मूलभूत स्थिती आणि नमुना पद्धत मंजूर झाल्यानंतरच परिणाम स्वीकारा', 'प्रत्येक मोजमापासाठी स्रोत पुरावा नोंदवा'],
            'test_plan': 'Pilot duration: not specified. Officer review required before publishing.',
            'draft_notice': 'AI-Drafted, needs review',
        }
    clean_problem = problem.strip() or 'the stated public-service problem'
    return {
        'outcomes': [f'Reduce the service-delivery friction described in: {clean_problem} (validate with stakeholders)'],
        'metrics': ['Share of eligible service requests completed within the agreed service window; officer must define the window'],
        'baseline': 'Baseline unavailable',
        'test_duration_days': None,
        'acceptance_criteria': ['Approve the measurement method and sample plan before the pilot begins', 'Attach source evidence for each reported measurement'],
        'test_plan': 'Pilot duration: not specified. Officer review required before publishing.',
        'draft_notice': 'AI-Drafted, needs review',
    }


def _provider_draft(problem: str, language: str) -> dict[str, Any] | None:
    api_key = os.getenv('LLM_API_KEY')
    if not api_key:
        return None
    endpoint = os.getenv('LLM_API_URL', 'https://api.openai.com/v1/chat/completions')
    model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
    prompt = (
        'Return only JSON keys outcomes (array of strings), metrics (array), baseline (string), '
        'test_duration_days (number or null), acceptance_criteria (array), test_plan (string). '
        'Never invent baseline measurements, numeric targets, or durations. If no measured baseline '
        'was supplied, baseline must exactly be "Baseline unavailable"; use null for duration when '
        'not justified. Label proposed content for human review. Input language: ' + language + '\nProblem: ' + problem
    )
    payload = json.dumps({
        'model': model,
        'temperature': 0.1,
        'response_format': {'type': 'json_object'},
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode('utf-8')
    request = Request(endpoint, data=payload, headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    })
    try:
        with urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode('utf-8'))
        content = body['choices'][0]['message']['content']
        result = json.loads(content)
        if not isinstance(result, dict):
            return None
        result['draft_notice'] = 'AI-Drafted, needs review'
        if not problem.strip() or result.get('baseline') in (None, ''):
            result['baseline'] = 'Baseline unavailable'
        return result
    except (URLError, TimeoutError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None


def draft_challenge(problem: str, language: str = 'en') -> dict[str, Any]:
    """Use configured provider when available; always return a usable mock draft on failure."""
    proposal = _provider_draft(problem, language) or _fallback(problem, language)
    # The endpoint intentionally accepts no baseline evidence, so neither a real
    # provider nor the fallback may make one up.
    proposal['baseline'] = 'Baseline unavailable'
    proposal['draft_notice'] = 'AI-Drafted, needs review'
    return proposal
