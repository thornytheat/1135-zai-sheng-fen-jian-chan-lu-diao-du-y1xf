from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TicketState(StrEnum):
    ACCEPTED = "已归批"
    CORRUPT = "计量无效"
    AMBIGUOUS = "更正歧义"
    LATE = "晚到未入账"
    DUPLICATE = "重复扫描"


@dataclass(frozen=True, order=True)
class Ticket:
    ticket: str
    lot: str
    line: str
    material: str
    gross: int
    tare: int
    observed: datetime
    recorded: datetime
    edition: int

    def __post_init__(self):
        if not all((self.ticket, self.lot, self.line, self.material)):
            raise ValueError("地磅编号、料批、线别或材质缺失")
        if self.gross <= self.tare or self.tare < 0 or self.edition < 1:
            raise ValueError("毛重、皮重或更正版本越界")
        if self.recorded < self.observed or self.observed.utcoffset() is None:
            raise ValueError("过磅时序无效")

    @property
    def net(self):
        return self.gross - self.tare


@dataclass(frozen=True)
class Lot:
    lot: str
    line: str
    material: str
    kg: int
    tickets: int
    last_weight: datetime


@dataclass(frozen=True)
class Journal:
    lots: tuple[Lot, ...]
    decisions: tuple[tuple[str, TicketState], ...]

    @property
    def total(self):
        return sum(batch.kg for batch in self.lots)
