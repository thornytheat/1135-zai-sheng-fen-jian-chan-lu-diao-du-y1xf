import pytest
from sortyield.weighbridge.contracts import TicketState
from sortyield.weighbridge.engine import instant, ledger, weight
from sortyield.weighbridge.service import evidence

CUT = instant("2026-11-24T20:00:00Z")


def ticket(**changes):
    return {
        "ticket": "T-009",
        "lot": "L10",
        "line": "人工线",
        "material": "PET",
        "gross": "5.125",
        "tare": "3.000",
        "unit": "t",
        "observed": "2026-11-24T08:00:00Z",
        "recorded": "2026-11-24T08:01:00Z",
        "edition": "1",
        **changes,
    }


def test_kg_and_t_are_the_same_integer_unit():
    # TRAP-15
    assert weight("5.125", "t") == weight("5125", "kg") == 5125


def test_ambiguous_correction_does_not_double_enter():
    # TRAP-14
    first = [ticket(), ticket(gross="5.100")]
    assert ledger(first, CUT) == ledger(first[::-1], CUT)
    assert ledger(first, CUT).decisions == (("T-009", TicketState.AMBIGUOUS),)


def test_late_correction_keeps_prior_as_of():
    # TRAP-42
    result = ledger(
        [ticket(), ticket(edition="2", recorded="2026-11-25T00:00:00Z")], CUT
    )
    assert result.total == 2125 and result.decisions[-1][1] == TicketState.LATE


def test_copies_do_not_create_another_ticket():
    result = ledger([ticket(), ticket()], CUT)
    assert result.total == 2125
    assert any(flag == TicketState.DUPLICATE for _, flag in result.decisions)


def test_mixed_feedstock_is_quarantined():
    result = ledger([ticket(), ticket(ticket="T-010", material="PP")], CUT)
    assert len(result.lots) == 0 and len(result.decisions) == 2


def test_net_weight_respects_tare():
    assert ledger([ticket(tare="5.200")], CUT).decisions[0][1] == TicketState.CORRUPT


def test_evidence_counts_processing_lines():
    result = ledger([ticket(), ticket(ticket="T-010", lot="L11")], CUT)
    assert evidence(result)["线别重量"] == {"人工线": 4250}


def test_invalid_units_require_row_quarantine():
    with pytest.raises(ValueError):
        weight("1.1", "kg")
    assert ledger([ticket(unit="lb")], CUT).total == 0
