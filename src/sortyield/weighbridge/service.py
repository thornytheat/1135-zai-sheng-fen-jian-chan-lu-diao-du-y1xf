from csv import DictReader
from .engine import by_line, instant, ledger


def read(path, cutoff):
    with path.open(newline="", encoding="utf-8-sig") as source:
        return ledger(DictReader(source), cutoff)


def evidence(journal):
    return {
        "title": "称重归批",
        "summary": f"入料 {journal.total:,} 公斤，合计 {len(journal.lots)} 批",
        "records": [
            {
                "料批": lot.lot,
                "线别": lot.line,
                "品种": lot.material,
                "净重（kg）": lot.kg,
                "磅单": lot.tickets,
            }
            for lot in journal.lots
        ],
        "磅单结果": journal.decisions,
        "线别重量": by_line(journal),
    }
