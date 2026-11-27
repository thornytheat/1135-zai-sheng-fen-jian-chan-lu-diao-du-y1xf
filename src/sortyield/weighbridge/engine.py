from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from .contracts import Journal, Lot, Ticket, TicketState


def instant(raw):
    parsed = datetime.fromisoformat(raw)
    if parsed.utcoffset() is None:
        raise ValueError("地磅时间须附时区")
    return parsed.astimezone(timezone.utc)


def weight(raw, unit):
    try:
        quantity = Decimal(raw)
        if unit == "t":
            quantity *= 1000
        elif unit != "kg":
            raise ValueError("计量单位不支持")
        if not quantity.is_finite() or quantity != quantity.to_integral_value():
            raise ValueError("读数不是整数公斤")
        return int(quantity)
    except InvalidOperation as error:
        raise ValueError("读数无法解析") from error


def parse(record):
    unit = record["unit"]
    return Ticket(
        record["ticket"].strip(),
        record["lot"].strip(),
        record["line"].strip(),
        record["material"].strip(),
        weight(record["gross"], unit),
        weight(record["tare"], unit),
        instant(record["observed"]),
        instant(record["recorded"]),
        int(record["edition"]),
    )


def ledger(raw, cutoff):
    editions = defaultdict(set)
    decisions = []
    for entry in raw:
        token = entry.get("ticket", "")
        try:
            ticket = parse(entry)
        except (ValueError, AttributeError, TypeError, KeyError):
            decisions.append((token, TicketState.CORRUPT))
            continue
        if ticket.recorded > cutoff:
            decisions.append((token, TicketState.LATE))
        elif ticket in editions[token]:
            decisions.append((token, TicketState.DUPLICATE))
        else:
            editions[token].add(ticket)
    allocations = defaultdict(list)
    for key, group in sorted(editions.items()):
        highest = max(row.edition for row in group)
        latest = {row for row in group if row.edition == highest}
        if len(latest) > 1:
            decisions.append((key, TicketState.AMBIGUOUS))
            continue
        entry = next(iter(latest))
        allocations[entry.lot].append(entry)
    batches = []
    for batch, items in sorted(allocations.items()):
        if len({(t.line, t.material) for t in items}) != 1:
            decisions.extend((t.ticket, TicketState.AMBIGUOUS) for t in items)
            continue
        decisions.extend((t.ticket, TicketState.ACCEPTED) for t in items)
        batches.append(
            Lot(
                batch,
                items[0].line,
                items[0].material,
                sum(t.net for t in items),
                len(items),
                max(t.observed for t in items),
            )
        )
    return Journal(tuple(batches), tuple(sorted(decisions)))


def by_line(journal):
    totals = defaultdict(int)
    for lot in journal.lots:
        totals[lot.line] += lot.kg
    return dict(sorted(totals.items()))
