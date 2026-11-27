import pytest
from types import SimpleNamespace
from sortyield.contamination_sample.engine import estimate, isolate, wilson_upper
from sortyield.contamination_sample.service import evidence


def cut(key="S-1", level="上", grams=500, unwanted=50, water=30):
    return {
        "sample": key,
        "stratum": level,
        "grams": grams,
        "unwanted": unwanted,
        "water": water,
    }


def test_stratum_weights_do_not_favor_deeper_sampling():
    rows = [cut(), cut("S-2", "中", 5000, 3000), cut("S-3", "下")]
    summary = estimate("P1", rows)
    assert (
        summary.impurity == pytest.approx((0.1 + 0.6 + 0.1) / 3)
        and summary.approved_samples
    )


def test_empty_sample_does_not_claim_purity():
    assert estimate("P1", []).impurity is None
    assert wilson_upper(0.1, 0) is None


def test_partial_coverage_needs_recheck():
    report = estimate("P1", [cut(), cut("S-2"), cut("S-3")])
    assert report.slices == 3 and not report.approved_samples


def test_contradictory_sample_is_dropped():
    report = estimate("P1", [cut(), cut(unwanted=60)])
    assert report.excluded == 1 and report.slices == 0


def test_zero_observed_impurity_still_has_upper_risk():
    assert wilson_upper(0, 100) > 0
    assert wilson_upper(1, 100) == pytest.approx(1)


def test_sample_mass_must_balance():
    report = estimate("P1", [cut(water=480)])
    assert report.excluded == 1 and report.mass == 0


def test_unknown_lot_is_kept_in_evidence():
    passed, held = isolate([{**cut(), "lot": "P2"}], [SimpleNamespace(lot="P1")])
    assert held == ("S-1",)
    assert evidence(passed, held)["未匹配样本"] == held
