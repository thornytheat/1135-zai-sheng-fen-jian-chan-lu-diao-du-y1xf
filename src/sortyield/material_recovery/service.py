from .engine import close, compare_bunkers, material_shift


def evidence(shift, drift, signed):
    records = [
        {
            "料批": row.lot,
            "来料（kg）": row.net_kg,
            "预留（kg）": row.warehoused,
            "未分配预计出料（kg）": row.forecast_unassigned,
            "预计残渣（kg）": row.expected_residue,
        }
        for row in shift.lines
    ]
    cohorts = [
        {
            "品种": row.material,
            "历史中位": row.past_median,
            "本次中位": row.present_median,
            "差值": row.shift,
            "历史样本": row.past_count,
            "本次样本": row.present_count,
        }
        for row in drift
    ]
    return {
        "title": "磅单结转",
        "summary": f"来料 {shift.net_kg:,} 公斤，凭证 {shift.receipt}",
        "records": records,
        "材质产率漂移": cohorts,
        "已对账仓位": signed,
    }
