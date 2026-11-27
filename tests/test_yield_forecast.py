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
from sortyield.contamination_sample.contracts import Audit, StratumReading

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


def layered_audit(*layers):
    impurity = sum(layer.impurity for layer in layers) / len(layers)
    moisture = sum(layer.moisture for layer in layers) / len(layers)
    return Audit(
        "P111",
        len(layers),
        3000,
        impurity,
        moisture,
        min(0.2, impurity),
        0,
        len(layers) / 3,
        tuple(layers),
    )


def varied_sample(days=40):
    rows = []
    for i in range(days):
        impurity = 0.05 + (i % 6) * 0.025
        moisture = 0.03 + (i % 4) * 0.02
        rows.append(
            RunHistory(
                DAY + timedelta(days=i % 10),
                DAY + timedelta(days=i % 10 + 1),
                "PP",
                model_vector(1000 + (i % 20) * 10, impurity, moisture, "光选线"),
                0.9 - impurity * 1.2 - moisture * 0.8,
            )
        )
    return rows


def varied_curve():
    rows = varied_sample()
    return fit_curve("PP", rows[:30], rows[30:])


def test_each_layer_uses_its_own_measured_pair_not_the_average():
    curve = varied_curve()
    layers = layered_audit(
        StratumReading("上", 1000, 0.05, 0.04),
        StratumReading("中", 1000, 0.13, 0.04),
        StratumReading("下", 1000, 0.18, 0.11),
    )
    estimate = predict(lot(1050), layers, curve)
    scored = {layer.stratum: layer for layer in estimate.layers}
    assert set(scored) == {"上", "中", "下"}
    # The worst layer's measured pair is scored directly, not the mean pair.
    worst = scored["下"]
    direct = predict(
        lot(1050),
        SimpleNamespace(approved_samples=True, impurity=0.18, moisture=0.11),
        curve,
    )
    assert worst.rate == pytest.approx(direct.rate)
    assert estimate.lower == pytest.approx(
        min(layer.lower for layer in estimate.layers)
    )


def test_worst_layer_lower_bound_governs_the_lot():
    curve = varied_curve()
    layers = layered_audit(
        StratumReading("上", 1000, 0.05, 0.04),
        StratumReading("中", 1000, 0.13, 0.04),
        StratumReading("下", 1000, 0.18, 0.11),
    )
    estimate = predict(lot(1050), layers, curve)
    mean_pair = predict(
        lot(1050),
        SimpleNamespace(approved_samples=True, impurity=0.12, moisture=0.0633),
        curve,
    )
    assert estimate.lower < mean_pair.lower


def test_out_of_support_layer_holds_the_whole_lot():
    curve = varied_curve()
    layers = layered_audit(
        StratumReading("上", 1000, 0.05, 0.04),
        StratumReading("中", 1000, 0.13, 0.04),
        StratumReading("下", 1000, 0.95, 0.04),
    )
    estimate = predict(lot(1050), layers, curve)
    assert estimate.rate is None and estimate.lower is None
    assert estimate.notice == "料批超出训练支撑"
    scored = {layer.stratum: layer for layer in estimate.layers}
    assert scored["下"].rate is None
    assert scored["上"].rate is not None


def test_missing_layer_is_not_scored_from_a_partial_average():
    # A layer gap fails approval, so the lot is never scored on an averaged pair
    # that was never measured.
    curve = varied_curve()
    layers = Audit(
        "P111",
        2,
        2000,
        0.09,
        0.04,
        0.09,
        0,
        2 / 3,
        (
            StratumReading("上", 1000, 0.05, 0.04),
            StratumReading("中", 1000, 0.13, 0.04),
        ),
    )
    assert not layers.approved_samples and not layers.full_coverage
    estimate = predict(lot(1050), layers, curve)
    assert estimate.rate is None and estimate.layers == ()
