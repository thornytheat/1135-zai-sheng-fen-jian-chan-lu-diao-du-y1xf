from dataclasses import dataclass
from enum import StrEnum


class Grade(StrEnum):
    CLEAN = "清洁颗粒"
    MIXED = "待再分选"
    HOLD = "留样复检"


@dataclass(frozen=True)
class QualityRules:
    impurity_upper: float = 0.22
    min_yield: float = 0.54
    max_moisture: float = 0.13

    def __post_init__(self):
        if not all(
            0 < x < 1 for x in (self.impurity_upper, self.min_yield, self.max_moisture)
        ):
            raise ValueError("验收阈值须在 0 与 1 之间")


@dataclass(frozen=True)
class GradeResult:
    lot: str
    grade: Grade
    reasons: tuple[str, ...]
    forecast_kg: int
    reserve_kg: int
    input_kg: int
    feed: str

    def __post_init__(self):
        if not 0 <= self.reserve_kg <= self.forecast_kg <= self.input_kg:
            raise ValueError("验收重量未守恒")
