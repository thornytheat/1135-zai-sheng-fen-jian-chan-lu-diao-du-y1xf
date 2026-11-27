from math import inf, nan
from sortyield.grade_acceptance.diagnostics import (
    GROUP,
    MEASURE,
    MODE,
    REFERENCE,
    THRESHOLD,
    report,
    summarize,
)


def observations(values, group="组一"):
    records = []
    for index, value in enumerate(values):
        record = {REFERENCE: f"凭证-{index}", GROUP: group, MEASURE: value}
        records.append(record)
    return records


def test_grade_acceptance_empty_stage_has_explicit_total():
    result = report({"records": []})
    assert result["有效"] == 0
    assert result["未知"] == 0
    assert result["明细"] == []


def test_grade_acceptance_unknown_does_not_become_zero():
    result = report({"records": observations([None, inf, nan, True, "4.1"])})
    assert result["有效"] == 0
    assert result["未知"] == 5
    assert result["明细"][0]["median"] is None


def test_grade_acceptance_uses_closed_range_for_threshold():
    below = THRESHOLD - 1
    above = THRESHOLD + 1
    cohort = summarize(observations([below, THRESHOLD, above]))[0]
    assert cohort.median == THRESHOLD
    assert cohort.at_risk == 1
    expected = "组一" if GROUP == REFERENCE else "凭证-0" if MODE == "low" else "凭证-2"
    assert cohort.critical_references == (expected,)


def test_grade_acceptance_permutation_preserves_counts_and_order():
    source = observations([2, 8, 9], "西") + observations([3, None, 6], "东")
    initial = summarize(source)
    assert len(initial) == 2
    assert sum(row.observations for row in initial) == 5
    assert summarize(list(reversed(source))) == initial


def test_grade_acceptance_missing_group_keeps_original_evidence():
    row = {MEASURE: 7, REFERENCE: "已知编号"}
    row.pop(GROUP, None)
    result = summarize([row])[0]
    assert result.cohort == "未分组"
    assert result.total == 7
