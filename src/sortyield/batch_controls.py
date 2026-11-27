from .weighbridge import diagnostics as weighbridge
from .contamination_sample import diagnostics as contamination_sample
from .yield_forecast import diagnostics as yield_forecast
from .grade_acceptance import diagnostics as grade_acceptance
from .bunker_slots import diagnostics as bunker_slots
from .material_recovery import diagnostics as material_recovery

PROJECTIONS = (
    weighbridge,
    contamination_sample,
    yield_forecast,
    grade_acceptance,
    bunker_slots,
    material_recovery,
)
TITLES = (
    "产线入料量",
    "抽检风险上界",
    "预测产量下界",
    "分等级出料",
    "仓位保留量",
    "残料集中度",
)


def annotate(stages):
    if len(stages) != len(PROJECTIONS):
        raise ValueError("业务诊断与运行阶段数量不一致")
    enriched = []
    for stage, implementation, title in zip(stages, PROJECTIONS, TITLES, strict=True):
        diagnostics = implementation.report(stage)
        enriched.append({**stage, "诊断": {**diagnostics, "标题": title}})
    return enriched
