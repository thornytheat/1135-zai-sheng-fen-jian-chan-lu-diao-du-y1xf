from csv import DictReader
from .engine import estimate, isolate


def from_file(path, lots):
    with path.open(newline="", encoding="utf-8-sig") as source:
        return isolate(DictReader(source), lots)


def evidence(results, orphans):
    report = []
    for audit in results.values():
        report.append(
            {
                "料批": audit.lot,
                "样本": audit.slices,
                "样重（g）": audit.mass,
                "覆盖": round(audit.coverage, 4),
                "杂质率": audit.impurity,
                "水分": audit.moisture,
                "上界": audit.upper_impurity,
                "隔离": audit.excluded,
            }
        )
    strata = [
        {
            "料批": audit.lot,
            "层位": layer.stratum,
            "样重（g）": layer.grams,
            "杂质率": layer.impurity,
            "水分": layer.moisture,
        }
        for audit in results.values()
        for layer in audit.strata
    ]
    count = sum(a.approved_samples for a in results.values())
    return {
        "title": "杂质取样",
        "summary": f"完整抽检 {count} 批，孤立单据 {len(orphans)} 张",
        "records": report,
        "分层实测": strata,
        "未匹配样本": orphans,
    }
