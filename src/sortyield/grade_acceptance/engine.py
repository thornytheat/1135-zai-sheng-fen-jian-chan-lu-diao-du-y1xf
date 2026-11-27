from collections import Counter
from math import floor
from .contracts import Grade, GradeResult, QualityRules


def classify(lot, audit, estimate, rules=QualityRules()):
    reasons = []
    if not audit.approved_samples:
        reasons.append("抽检覆盖不足")
    if estimate.rate is None:
        reasons.append(estimate.notice)
    elif estimate.lower < rules.min_yield:
        reasons.append("出料区间下界不足")
    if audit.upper_impurity is not None and audit.upper_impurity > rules.impurity_upper:
        reasons.append("杂质上界超过合同")
    if audit.moisture is not None and audit.moisture > rules.max_moisture:
        reasons.append("水分超过入仓线")
    if not audit.approved_samples or estimate.rate is None:
        kind = Grade.HOLD
    elif reasons:
        kind = Grade.MIXED
    else:
        kind = Grade.CLEAN
    forecast = floor(lot.kg * (estimate.rate or 0))
    reserve = floor(lot.kg * (estimate.lower or 0)) if kind == Grade.CLEAN else 0
    return GradeResult(
        lot.lot,
        kind,
        tuple(reasons or ["检验放行"]),
        forecast,
        reserve,
        lot.kg,
        lot.material,
    )


def grade_batch(lots, audits, forecasts, rules=QualityRules()):
    predicted = {item.lot: item for item in forecasts}
    actual = {lot.lot for lot in lots}
    if (
        len(actual) != len(lots)
        or len(predicted) != len(forecasts)
        or actual != set(predicted)
        or actual != set(audits)
    ):
        raise ValueError("取样、估算与地磅料批无法对照")
    return tuple(
        classify(lot, audits[lot.lot], predicted[lot.lot], rules) for lot in lots
    )


def causes(grades):
    flags = Counter(cause for result in grades for cause in result.reasons)
    return dict(sorted(flags.items(), key=lambda item: (-item[1], item[0])))
