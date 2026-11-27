from __future__ import annotations

import argparse
import json
import re
from hashlib import sha256
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType

from .pipeline import run
from .batch_controls import annotate

MODULES = (
    ("weighbridge", "称重归批"),
    ("contamination_sample", "杂质取样"),
    ("yield_forecast", "产率拟合"),
    ("grade_acceptance", "分级验收"),
    ("bunker_slots", "仓位分派"),
    ("material_recovery", "磅单结转"),
)
application = Flask(
    __name__, static_folder="web/static", template_folder="web/templates"
)
application.config["MAX_CONTENT_LENGTH"] = 8192
application.json.sort_keys = False
application.json.sort_keys = False
_initial_snapshot = None
_initial_lock = Lock()


def snapshot(capacity=None):
    business_result = run(capacity)
    business_result["stages"] = annotate(business_result["stages"])
    if len(business_result["stages"]) != len(MODULES):
        raise RuntimeError("运行证据缺少业务环节")
    content = json.dumps(
        business_result, ensure_ascii=False, allow_nan=False, sort_keys=True
    )
    return {**business_result, "run_id": sha256(content.encode()).hexdigest()[:12]}


def initial_snapshot():
    global _initial_snapshot
    with _initial_lock:
        if _initial_snapshot is None:
            _initial_snapshot = snapshot()
    return _initial_snapshot


def parse_capacity(value):
    if type(value) is not int or not 1 <= value <= 100:
        raise ValueError("请输入 1 到 100 之间的整数")
    return value


@application.get("/")
def index():
    return render_template("index.html", modules=MODULES)


@application.get("/health")
def health():
    return jsonify(status="ok", service="sortyield")


@application.get("/api/overview")
def overview():
    return jsonify(initial_snapshot())


@application.post("/api/scenario")
def scenario():
    try:
        body = request.get_json()
        if not isinstance(body, dict) or set(body) != {"capacity"}:
            raise ValueError("请提交仅包含 capacity 的 JSON 对象")
        capacity = parse_capacity(body["capacity"])
    except (BadRequest, UnsupportedMediaType, ValueError):
        return jsonify(
            code="INVALID_SCENARIO", message="请输入 1 到 100 之间的整数"
        ), 400
    return jsonify(snapshot(capacity))


@application.get("/api/stages/<module>")
def stage_evidence(module):
    positions = {slug: index for index, (slug, _) in enumerate(MODULES)}
    if module not in positions or not re.fullmatch(r"[a-z_]+", module):
        return jsonify(code="UNKNOWN_STAGE", message="找不到该业务环节"), 404
    raw_capacity = request.args.get("capacity")
    try:
        result = (
            initial_snapshot()
            if raw_capacity is None
            else snapshot(parse_capacity(int(raw_capacity)))
        )
    except ValueError:
        return jsonify(
            code="INVALID_SCENARIO", message="请输入 1 到 100 之间的整数"
        ), 400
    return jsonify(run_id=result["run_id"], **result["stages"][positions[module]])


@application.errorhandler(RequestEntityTooLarge)
def request_too_large(_error):
    return jsonify(code="REQUEST_TOO_LARGE", message="请求内容超出 8 KiB"), 413


def main():
    parser = argparse.ArgumentParser(description="再生分拣产率调度")
    commands = parser.add_subparsers(dest="command", required=True)
    evaluate = commands.add_parser("evaluate", help="执行本地样例并输出业务证据")
    evaluate.add_argument("--capacity", type=int)
    evaluate.add_argument("--output", type=Path)
    serve = commands.add_parser("serve", help="启动浏览服务")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "serve":
        from waitress import serve as serve_wsgi

        initial_snapshot()
        serve_wsgi(application, host="0.0.0.0", port=args.port)
        return
    try:
        capacity = parse_capacity(args.capacity) if args.capacity is not None else None
    except ValueError as error:
        parser.error(str(error))
    output = json.dumps(
        snapshot(capacity), ensure_ascii=False, indent=2, allow_nan=False
    )
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
