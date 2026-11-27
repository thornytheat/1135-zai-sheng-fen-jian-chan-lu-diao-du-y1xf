from datetime import date, timedelta
from types import SimpleNamespace
from dataclasses import replace
import pytest
from sortyield.yield_forecast.contracts import RunHistory
from sortyield.yield_forecast.engine import (
    center_fit,
    fit_curve,
    model_vector,
    per_polymer,
    predict,
)

DAY = date(2026, 11, 12)


def sample():
    return [
        RunHistory(
            DAY + timedelta(days=i),
            DAY + timedelta(days=i + 1),
            "PP",
            model_vector(1000 + i * 9, 0.13, 0.04, "光选线"),
            0.5 + i * 0.02,
        )
        for i in range(12)
    ]


def lot(kg):
    return SimpleNamespace(lot="P111", material="PP", line="光选线", kg=kg)


def audit():
    return SimpleNamespace(approved_samples=True, impurity=0.13, moisture=0.04)


def test_cutoff_discards_pending_labels():
    # TRAP-42
    fold = DAY + timedelta(days=8)
    cut = DAY + timedelta(days=12)
    original = per_polymer(sample(), fold, cut)
    assert (
        per_polymer(
            [
                *sample(),
                replace(sample()[-1], closed=cut + timedelta(days=2), yield_rate=0),
            ],
            fold,
            cut,
        )
        == original
    )


def test_raw_scale_constant_columns_do_not_divide_by_zero():
    # TRAP-32
    point = center_fit(sample())
    assert min(point[1]) == 1e-6 and point[1][0] > 0


def test_per_lot_features_are_independent_of_batch_size():
    # TRAP-53
    curve = fit_curve("PP", sample()[:8], sample()[8:])
    a = predict(lot(1050), audit(), curve)
    assert [predict(lot(size), audit(), curve) for size in (1000, 1050, 1007)][1] == a


def test_out_of_support_skips_false_precision():
    # TRAP-44
    curve = fit_curve("PP", sample()[:8], sample()[8:])
    assert predict(lot(1000000), audit(), curve).rate is None


def test_interval_has_consistent_endpoints():
    curve = fit_curve("PP", sample()[:8], sample()[8:])
    estimate = predict(lot(1050), audit(), curve)
    assert 0 <= estimate.lower <= estimate.rate <= estimate.upper <= 1


def test_known_feature_slope_has_correct_direction():
    curve = fit_curve("PP", sample()[:8], sample()[8:])
    assert (
        predict(lot(1030), audit(), curve).rate
        > predict(lot(1002), audit(), curve).rate
    )


def test_insufficient_records_reject_fit():
    with pytest.raises(ValueError):
        fit_curve("PP", sample()[:2], [])


def test_no_valid_sampling_skips_curve_execution():
    assert predict(lot(1050), audit(), None).lower is None
