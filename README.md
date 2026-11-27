# 再生分拣产率调度

面向产线调度的本地工作台。内置业务样例覆盖再生分拣线产率回归、杂质风险与仓位分派。样例采用确定性构造，适合复现实验和核查边界行为。

## 启动

```sh
docker compose up --build -d
```

打开 `http://127.0.0.1:18214/` 查看产率与入仓单。左侧六个入口可展开运行证据。调整「仓位分配限额（吨）」，点击「重排仓位」比较处置结果。结束后执行 `docker compose down --remove-orphans`。

## 独立业务模块

- 称重归批 `weighbridge`
- 杂质取样 `contamination_sample`
- 产率拟合 `yield_forecast`
- 分级验收 `grade_acceptance`
- 仓位分派 `bunker_slots`
- 磅单结转 `material_recovery`

## 查看运行结果

- `GET /api/overview` 返回默认运行及其指纹。
- `POST /api/scenario` 接收 `{"capacity": 3}`。入口接受 1–100 的整数，应用样例时使用该业务额度。
- `GET /api/stages/material_recovery` 查看该环节的独立证据，支持 `?capacity=3`。

```sh
docker compose exec -T app python -m sortyield.delivery evaluate --capacity 3
docker compose exec -T app pytest -q
```

数据和模型约定见 [业务契约](docs/SPEC.md)。模块、例外规则与验证入口见 [业务深度](docs/DEPTH.md)。
