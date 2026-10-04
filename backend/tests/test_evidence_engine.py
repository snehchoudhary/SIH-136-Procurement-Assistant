import io

import pandas as pd

from app.services.evidence_engine import (
    compute_sha256,
    generate_demo_datasets,
    get_claimed_values_for_demo,
    recalculate_kpis,
    run_quality_checks,
)


def _analyse(name):
    csv_text = generate_demo_datasets()[name]
    frame = pd.read_csv(io.StringIO(csv_text))
    return frame, recalculate_kpis(frame, get_claimed_values_for_demo(name)), run_quality_checks(frame)


def test_demo_datasets_are_reproducible_and_cover_expected_outcomes():
    first = generate_demo_datasets()
    assert first == generate_demo_datasets()
    assert compute_sha256(io.BytesIO(first['hero_problematic'].encode())) == compute_sha256(io.BytesIO(first['hero_problematic'].encode()))
    _, clean_kpis, clean_findings = _analyse('clean_pass')
    _, hero_kpis, hero_findings = _analyse('hero_problematic')
    _, corrected_kpis, corrected_findings = _analyse('corrected_resubmission')
    assert all(k['outcome'] == 'passed' for k in clean_kpis)
    assert not clean_findings
    hero = {k['kpi_key']: k for k in hero_kpis}
    assert hero['reduction_pct']['claimed_value'] == 40.0
    assert hero['reduction_pct']['recomputed_value'] < 30
    assert hero['marathi_accuracy_pct']['outcome'] == 'missing_evidence'
    assert {'excluded_failed_cases', 'sample_size_adequacy', 'duplicate_rows', 'missing_periods'} <= {f['check_name'] for f in hero_findings}
    assert all(k['outcome'] == 'passed' for k in corrected_kpis)
    assert not any(f['severity'] == 'critical' for f in corrected_findings)


def test_processing_time_reduction_keeps_failed_attempts_in_denominator():
    frame = pd.DataFrame({
        'processing_time_before': [10.0] * 10,
        'processing_time_after': [5.0] * 6 + [15.0] * 4,
        'outcome': ['success'] * 6 + ['failed'] * 4,
        'error_flag': [0] * 10,
        'language': ['Marathi'] * 10,
        'low_bandwidth': [True] * 10,
    })
    reduction = recalculate_kpis(frame, {})[0]
    assert reduction['recomputed_value'] == 50.0
    assert reduction['rows_used'] == 10


def test_missing_and_failed_are_distinct_outcomes():
    frame = pd.DataFrame({
        'processing_time_before': [10.0] * 10,
        'processing_time_after': [10.0] * 10,
        'outcome': ['success'] * 10,
        'error_flag': [0] * 10,
        'language': ['Hindi'] * 10,
        'low_bandwidth': [False] * 10,
    })
    outcomes = {k['kpi_key']: k['outcome'] for k in recalculate_kpis(frame, {})}
    assert outcomes['reduction_pct'] == 'failed'
    assert outcomes['marathi_accuracy_pct'] == 'missing_evidence'
    assert outcomes['low_bandwidth_pct'] == 'missing_evidence'


def test_each_quality_check_returns_structured_findings():
    base = pd.DataFrame({
        'case_id': ['1', '1', '3', '4'],
        'language': ['Marathi', 'Marathi', 'Hindi', 'Hindi'],
        'processing_time_before': [10, 10, 0, 10],
        'processing_time_after': [5, 5, 5, 1000],
        'error_flag': [0, 0, 0, 0],
        'low_bandwidth': [True, True, False, False],
        'outcome': ['success', 'failed', 'success', 'success'],
        'period': [1, 1, 3, None],
    })
    findings = run_quality_checks(base, pd.DataFrame({'older_column': [1]}), 'old-definition', 'new-definition',
                                  {'min_total_observations': 10, 'min_marathi_samples': 4, 'min_segment_samples': 3})
    names = {finding['check_name'] for finding in findings}
    assert {'missing_periods', 'duplicate_rows', 'unsupported_denominators', 'changed_metric_definition',
            'excluded_failed_cases', 'sample_size_adequacy', 'outliers'} <= names
    for finding in findings:
        assert finding['severity'] in {'critical', 'major', 'minor', 'info'}
        assert isinstance(finding['rows_affected'], int)
        assert isinstance(finding['explanation'], str) and finding['explanation']
        assert isinstance(finding['row_indices'], list)


def test_required_column_omission_and_bad_values_are_missing_evidence():
    frame = pd.DataFrame({'processing_time_before': ['bad'] * 2, 'processing_time_after': [4, 3]})
    findings = run_quality_checks(frame)
    assert any(item['check_name'] == 'missing_required_columns' for item in findings)
    kpis = recalculate_kpis(frame, {}, {'min_total_observations': 1})
    assert kpis[0]['outcome'] == 'missing_evidence'
    assert kpis[0]['recomputed_value'] is None
    assert kpis[1]['outcome'] == 'missing_evidence'
    assert kpis[1]['recomputed_value'] is None


def test_low_bandwidth_minimum_is_taken_from_measurement_plan():
    frame = pd.DataFrame({'processing_time_before': [10] * 10, 'processing_time_after': [8] * 10,
        'error_flag': [0] * 10, 'language': ['Marathi'] * 10, 'outcome': ['success'] * 10,
        'low_bandwidth': [True] + [False] * 9})
    result = recalculate_kpis(frame, {}, {'min_total_observations': 1, 'min_marathi_samples': 1,
                                         'min_low_bandwidth_samples': 2})
    assert result[3]['outcome'] == 'missing_evidence'
