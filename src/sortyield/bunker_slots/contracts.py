from dataclasses import dataclass
from enum import StrEnum


class PlacementFlag(StrEnum):
    RESERVED = "仓位已预留"
    HOLD = "等待仓位"
    SORT = "等待再分选"
    SAMPLE = "等待抽检"


@dataclass(frozen=True, order=True)
class Bunker:
    tag: str
    feed: str
    total_kg: int
    occupied_kg: int
    changeover_loss: int = 0

    def __post_init__(self):
        if (
            not self.tag
            or not self.feed
            or not 0 <= self.occupied_kg <= self.total_kg
            or self.changeover_loss < 0
        ):
            raise ValueError("库存仓位字段无效")

    @property
    def spare(self):
        return max(0, self.total_kg - self.occupied_kg - self.changeover_loss)


@dataclass(frozen=True)
class Placement:
    lot: str
    target: str | None
    kg: int
    flag: PlacementFlag
    rule: str


@dataclass(frozen=True)
class Reservation:
    events: tuple[Placement, ...]
    remaining: dict[str, int]
    limit: int
    used: int

    def __post_init__(self):
        if (
            self.used != sum(row.kg for row in self.events)
            or not 0 <= self.used <= self.limit
        ):
            raise ValueError("出料预留超过班次限额")
