from types import SimpleNamespace as Obj
import pytest
from sortyield.grade_acceptance.contracts import Grade, QualityRules
from sortyield.grade_acceptance.engine import classify, grade_batch
from sortyield.grade_acceptance.service import evidence


def inputs():
    return (
        Obj(lot="A", kg=3000, material="PET"),
        Obj(approved_samples=True, upper_impurity=0.15, moisture=0.07),
        Obj(lot="A", rate=0.8, lower=0.7, notice="支持"),
    )


def test_clean_output_uses_conservative_lower_endpoint():
    result = classify(*inputs())
    assert (
        result.grade == Grade.CLEAN
        and result.reserve_kg == 2100
        and result.forecast_kg == 2400
    )


def test_evidence_gaps_precede_quality_thresholds():
    # TRAP-19
    lot, audit, estimate = inputs()
    audit.approved_samples = False
    audit.moisture = 0.28
    assert classify(lot, audit, estimate).reasons == ("抽检覆盖不足", "水分超过入仓线")
    assert classify(lot, audit, estimate).grade == Grade.HOLD


def test_below_minimum_yield_waits_for_resorting():
    lot, audit, estimate = inputs()
    estimate.lower = 0.48
    result = classify(lot, audit, estimate)
    assert result.grade == Grade.MIXED and result.reserve_kg == 0


def test_single_layer_below_minimum_blocks_the_clean_bunker():
    from sortyield.yield_forecast.contracts import Estimate, LayerEstimate

    lot, audit, estimate = inputs()
    estimate = Estimate(
        "A",
        0.8,
        0.6,
        0.9,
        "PET",
        "已估算",
        (
            LayerEstimate("上", 0.85, 0.75, 0.95, "已估算"),
            LayerEstimate("中", 0.82, 0.72, 0.92, "已估算"),
            LayerEstimate("下", 0.55, 0.48, 0.62, "已估算"),
        ),
    )
    result = classify(lot, audit, estimate)
    assert result.grade == Grade.MIXED and result.reserve_kg == 0
    assert result.reasons == ("分层出料区间下界不足：下",)


def test_cohort_cannot_be_silently_dropped():
    lot, audit, estimate = inputs()
    with pytest.raises(ValueError, match="无法对照"):
        grade_batch([lot], {"A": audit}, [])


def test_duplicate_predictions_cannot_overwrite():
    lot, audit, estimate = inputs()
    with pytest.raises(ValueError, match="无法对照"):
        grade_batch([lot], {"A": audit}, [estimate, estimate])


def test_contract_equality_is_accepted():
    lot, audit, estimate = inputs()
    audit.moisture = 0.13
    assert classify(lot, audit, estimate).grade == Grade.CLEAN


def test_cause_totals_do_not_replace_raw_grades():
    result = evidence([classify(*inputs())])
    assert result["原因汇总"] == {"检验放行": 1} and result["records"][0]["料批"] == "A"
