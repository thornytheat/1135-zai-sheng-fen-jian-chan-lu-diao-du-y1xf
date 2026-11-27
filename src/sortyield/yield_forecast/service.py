from csv import DictReader
from datetime import date
from .contracts import RunHistory
from .engine import model_vector, per_polymer, predict


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as source:
        rows = DictReader(source)
        return tuple(
            RunHistory(
                date.fromisoformat(row["handled"]),
                date.fromisoformat(row["closed"]),
                row["material"],
                model_vector(
                    int(row["kg"]),
                    float(row["impurity"]),
                    float(row["moisture"]),
                    row["line"],
                ),
                float(row["yield_rate"]),
            )
            for row in rows
        )


def evidence(curves, forecasts):
    return {
        "title": "产率拟合",
        "summary": f"拟合 {len(curves)} 个材质，{sum(row.rate is not None for row in forecasts)} 批有区间",
        "records": [
            {
                "料批": row.lot,
                "材质": row.fit_group,
                "产率": row.rate,
                "下界": row.lower,
                "上界": row.upper,
                "结果": row.notice,
            }
            for row in forecasts
        ],
        "拟合记录数": {
            key: {"训练": model.count, "校准": model.validation}
            for key, model in curves.items()
        },
    }
