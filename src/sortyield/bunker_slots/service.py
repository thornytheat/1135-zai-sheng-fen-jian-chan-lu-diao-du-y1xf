from csv import DictReader
from .contracts import Bunker, PlacementFlag
from .engine import allocate, tally


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return tuple(
            Bunker(
                row["bunker"],
                row["material"],
                int(row["capacity_kg"]),
                int(row["occupied_kg"]),
                int(row["sweep_loss_kg"]),
            )
            for row in DictReader(source)
        )


def evidence(book):
    records = [
        {"料批": row.lot, "去向": row.target, "预留（kg）": row.kg, "状态": row.flag}
        for row in book.events
    ]
    return {
        "title": "仓位分派",
        "summary": f"预留 {book.used:,}/{book.limit:,} 公斤",
        "records": records,
        "仓位剩余": book.remaining,
        "仓位预留": tally(book),
    }
