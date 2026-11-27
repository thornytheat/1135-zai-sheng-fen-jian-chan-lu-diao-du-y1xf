from .contracts import Grade
from .engine import causes, grade_batch


def evidence(grades):
    passed = sum(result.grade == Grade.CLEAN for result in grades)
    return {
        "title": "分级验收",
        "summary": f"符合入仓线 {passed}/{len(grades)} 批",
        "records": [
            {
                "料批": row.lot,
                "等级": row.grade,
                "依据": row.reasons,
                "保守排仓（kg）": row.reserve_kg,
                "预测出料（kg）": row.forecast_kg,
            }
            for row in grades
        ],
        "原因汇总": causes(grades),
    }
