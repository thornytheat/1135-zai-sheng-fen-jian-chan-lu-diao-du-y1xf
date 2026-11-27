# 再生分拣产率调度的业务深度

AI/ML / 传统ML

## 功能模块

| 模块 | 职责 | 使用的计算或裁决 | 核心文件 | 独立测试 |
|---|---|---|---|---|
| M1 称重归批 | 称重归批 | 统一公斤和时点、同版冲突隔离 | `src/sortyield/weighbridge/contracts.py` `src/sortyield/weighbridge/engine.py` `src/sortyield/weighbridge/service.py` | `tests/test_weighbridge.py` |
| M2 杂质取样 | 杂质取样 | 分层平均与 Wilson 风险提示 | `src/sortyield/contamination_sample/contracts.py` `src/sortyield/contamination_sample/engine.py` `src/sortyield/contamination_sample/service.py` | `tests/test_contamination_sample.py` |
| M3 产率拟合 | 产率拟合 | 材质独立岭回归和留出残差区间 | `src/sortyield/yield_forecast/contracts.py` `src/sortyield/yield_forecast/engine.py` `src/sortyield/yield_forecast/service.py` | `tests/test_yield_forecast.py` |
| M4 分级验收 | 分级验收 | 样本完整性与合同界值优先 | `src/sortyield/grade_acceptance/contracts.py` `src/sortyield/grade_acceptance/engine.py` `src/sortyield/grade_acceptance/service.py` | `tests/test_grade_acceptance.py` |
| M5 仓位分派 | 仓位分派 | 整批最佳适配，与额度、预扫占位对账 | `src/sortyield/bunker_slots/contracts.py` `src/sortyield/bunker_slots/engine.py` `src/sortyield/bunker_slots/service.py` | `tests/test_bunker_slots.py` |
| M6 磅单结转 | 磅单结转 | 逐批守恒与材质产率漂移 | `src/sortyield/material_recovery/contracts.py` `src/sortyield/material_recovery/engine.py` `src/sortyield/material_recovery/service.py` | `tests/test_material_recovery.py` |

## 边界与证据

| 编号 | 触发条件 | 风险 | 处理规则 | 位置 | 验证 |
|---|---|---|---|---|---|
| TRAP-15 | 吨与公斤混用 | 产生错误的业务记录或评分 | 转换为整数公斤后运算 | `src/sortyield/weighbridge/engine.py` | `tests/test_weighbridge.py::test_kg_and_t_are_the_same_integer_unit` |
| TRAP-14 | 更正版本冲突 | 产生错误的业务记录或评分 | 同版异值整张隔离 | `src/sortyield/weighbridge/engine.py` | `tests/test_weighbridge.py::test_ambiguous_correction_does_not_double_enter` |
| TRAP-42 | 样本标签成熟晚于交易日 | 产生错误的业务记录或评分 | 只使用截点前成熟产率 | `src/sortyield/yield_forecast/engine.py` | `tests/test_yield_forecast.py::test_cutoff_discards_pending_labels` |
| TRAP-32 | 有常数列 | 产生错误的业务记录或评分 | 中心化并设尺度地板 | `src/sortyield/yield_forecast/engine.py` | `tests/test_yield_forecast.py::test_raw_scale_constant_columns_do_not_divide_by_zero` |
| TRAP-53 | 大小批一起推断 | 产生错误的业务记录或评分 | 冻结历史尺度 | `src/sortyield/yield_forecast/engine.py` | `tests/test_yield_forecast.py::test_per_lot_features_are_independent_of_batch_size` |
| TRAP-44 | 料批超出历史区间 | 产生错误的业务记录或评分 | 超支持距离拒绝出数 | `src/sortyield/yield_forecast/engine.py` | `tests/test_yield_forecast.py::test_out_of_support_skips_false_precision` |
| TRAP-19 | 覆盖缺失同时水分高 | 产生错误的业务记录或评分 | 先留样，保留所有原因 | `src/sortyield/grade_acceptance/engine.py` | `tests/test_grade_acceptance.py::test_evidence_gaps_precede_quality_thresholds` |
| TRAP-10 | 三路质量汇总 | 产生错误的业务记录或评分 | 整数公斤将余量留在残渣或未分配账 | `src/sortyield/material_recovery/engine.py` | `tests/test_material_recovery.py::test_exact_kg_conservation_tracks_unassigned_output_and_residue` |
