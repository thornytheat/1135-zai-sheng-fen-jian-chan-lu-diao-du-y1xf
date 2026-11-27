from collections import defaultdict
from dataclasses import asdict, dataclass
from math import fsum, isfinite
from statistics import median

MEASURE = "上界"
GROUP = "覆盖"
REFERENCE = "料批"
THRESHOLD = 0.22
MODE = "high"


@dataclass(frozen=True)
class Cohort:
    cohort: str
    observations: int
    excluded: int
    total: float | None
    median: float | None
    at_risk: int
    critical_references: tuple[str, ...]


def _is_observation(value):
    return type(value) in (int, float) and isfinite(value)


def _group_key(value):
    if value is None or value == "":
        return "未分组"
    if isinstance(value, (str, int, float)):
        return str(value)
    raise ValueError("无效的诊断分组字段")


def _lower(value):
    return value < THRESHOLD


def _upper(value):
    return value > THRESHOLD


def summarize(records):
    buckets = defaultdict(list)
    excluded = defaultdict(int)
    for row in records:
        group = _group_key(row.get(GROUP))
        value = row.get(MEASURE)
        if not _is_observation(value):
            excluded[group] += 1
            continue
        reference = str(row.get(REFERENCE) or "未标识记录")
        buckets[group].append((value, reference))
    output = []
    is_critical = _lower if MODE == "low" else _upper
    for group in sorted(buckets.keys() | excluded.keys()):
        observations = buckets[group]
        values = [value for value, _ in observations]
        flags = [reference for value, reference in observations if is_critical(value)]
        output.append(
            Cohort(
                cohort=group,
                observations=len(values),
                excluded=excluded[group],
                total=round(fsum(values), 8) if values else None,
                median=median(values) if values else None,
                at_risk=len(flags),
                critical_references=tuple(sorted(set(flags))),
            )
        )
    return tuple(output)


def report(stage):
    cohorts = summarize(stage["records"])
    available = sum(group.observations for group in cohorts)
    omitted = sum(group.excluded for group in cohorts)
    if available + omitted != len(stage["records"]):
        raise RuntimeError("分组有效行与忽略行数未守恒")
    return {
        "字段": MEASURE,
        "分组": GROUP,
        "阈值": THRESHOLD,
        "方向": "偏低" if MODE == "low" else "偏高",
        "关注": sum(group.at_risk for group in cohorts),
        "有效": available,
        "未知": omitted,
        "明细": [asdict(group) for group in cohorts],
    }
