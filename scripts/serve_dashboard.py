"""Serve local reports and model settings.

Stdlib only.  Point a browser at http://127.0.0.1:8765 after running:

    py -3 scripts/serve_dashboard.py

Report routes remain read-only. Model configuration is local to this computer.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import secrets
import sys
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
RUNS_DIR = ROOT / "artifacts" / "model-shadow"
_LEGACY_AGENT_DIR = ROOT.parent / "Juliang-benditui-Agent-MVP" / "agent"
AGENT_DIR = Path(os.environ.get(
    "DOUYIN_ADPULSE_AGENT_DIR",
    _LEGACY_AGENT_DIR if _LEGACY_AGENT_DIR.is_dir() else ROOT / "agent",
))

_RUN_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_CONTENT = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def list_runs() -> list[dict]:
    runs = []
    if not RUNS_DIR.is_dir():
        return runs
    for folder in sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not folder.is_dir():
            continue
        review = _read_json(folder / "review.json")
        manifest = _read_json(folder / "manifest.json")
        runs.append({
            "id": folder.name,
            "report_date": manifest.get("report_date"),
            "model": manifest.get("model"),
            "status": review.get("operational_status") or review.get("structural_status"),
            "model_calls": review.get("model_calls"),
        })
    return runs


_SUMMARY_METRIC_FIELDS = ("spend", "impressions", "clicks", "leads", "cpl", "ctr", "cvr")


def run_summary(folder: Path) -> dict:
    """Return only the scalar account metrics needed by the report dashboard."""
    analysis = _read_json(folder / "state.json").get("data_analysis_result")
    observations = analysis.get("observations", []) if isinstance(analysis, dict) else []
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        for evidence in observation.get("evidence", []):
            if not isinstance(evidence, dict):
                continue
            if evidence.get("source") != "get_account_metrics" or evidence.get("object_type") != "account":
                continue
            values = evidence.get("value")
            if not isinstance(values, dict):
                continue
            metrics = {
                name: value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                else None
                for name, value in ((name, values.get(name)) for name in _SUMMARY_METRIC_FIELDS)
            }
            if any(value is not None for value in metrics.values()):
                time_range = evidence.get("time_range")
                return {"metrics": metrics, "time_range": time_range if isinstance(time_range, str) else None}
    return {"metrics": None, "time_range": None}


class UnavailableModelStore:
    """Keeps the public dashboard runnable when no private Agent project is present."""

    message = "Model settings require a local Agent project."

    def public(self) -> dict:
        return {
            "provider": "deepseek",
            "model": "",
            "key_configured": False,
            "environment_override": False,
            "settings_available": False,
            "message": self.message,
        }

    def save(self, _payload: dict) -> dict:
        raise ValueError(self.message)

    def test(self, _payload: dict) -> dict:
        raise ValueError(self.message)


class DashboardServer(ThreadingHTTPServer):
    def __init__(self, address, handler, *, model_store=None):
        super().__init__(address, handler)
        self.local_token = secrets.token_hex(32)
        if model_store is None:
            # This module uses only stdlib; avoid the eager services package
            # importing the whole Agent dependency tree for a settings page.
            config_module = AGENT_DIR / "services" / "local_model_config.py"
            if config_module.is_file():
                spec = importlib.util.spec_from_file_location("dashboard_model_config", config_module)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                model_store = module.ModelConfigStore(AGENT_DIR)
            else:
                model_store = UnavailableModelStore()
        self.model_store = model_store


class Handler(BaseHTTPRequestHandler):
    server_version = "ShadowDashboard/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, text: str, content_type: str) -> None:
        self._send(status, text.encode("utf-8"), content_type)

    def _json(self, status, value):
        return self._send_text(status, json.dumps(value, ensure_ascii=False), _CONTENT[".json"])

    def _local_request(self):
        return self.client_address[0] in {"127.0.0.1", "::1"} and self.headers.get("Host") in {
            f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_POST(self):  # noqa: N802
        if not self._local_request() or not secrets.compare_digest(
                self.headers.get("X-Local-Token", ""), self.server.local_token):
            return self._json(403, {"message": "请从本机页面打开设置后重试。"})
        path = self.path.split("?", 1)[0]
        if path not in {"/api/settings/save", "/api/settings/test"}:
            return self._json(404, {"message": "页面不存在。"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192 or self.headers.get_content_type() != "application/json":
                return self._json(400, {"message": "配置请求格式不正确。"})
            payload = json.loads(self.rfile.read(length))
            action = self.server.model_store.save if path.endswith("save") else self.server.model_store.test
            return self._json(200, action(payload))
        except (ValueError, UnicodeError) as exc:
            message = str(exc) if not isinstance(exc, json.JSONDecodeError) else "配置请求格式不正确。"
            return self._json(400, {"message": message})
        except OSError:
            return self._json(500, {"message": "本地配置无法读写，请检查目录权限。"})

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]

        if path == "/api/settings":
            if not self._local_request():
                return self._json(403, {"message": "设置仅可在本机访问。"})
            try:
                return self._json(200, {**self.server.model_store.public(), "token": self.server.local_token})
            except (OSError, ValueError):
                return self._json(500, {"message": "本地配置无法读取，请检查配置文件。"})

        if path in {"/settings", "/settings.html", "/settings.js"}:
            name = "settings.js" if path.endswith(".js") else "settings.html"
            return self._send_text(200, (WEB_DIR / name).read_text(encoding="utf-8"),
                                   _CONTENT[Path(name).suffix])

        if path in ("/", "/index.html"):
            page = WEB_DIR / "index.html"
            return self._send_text(200, page.read_text(encoding="utf-8"), _CONTENT[".html"])

        if path.startswith("/dashboard."):
            name = path.lstrip("/")
            if name in ("dashboard.css", "dashboard.js") and "/" not in name:
                return self._send_text(200, (WEB_DIR / name).read_text(encoding="utf-8"), _CONTENT[name[name.rfind("."):]])

        if path == "/api/runs":
            return self._send_text(200, json.dumps(list_runs(), ensure_ascii=False), _CONTENT[".json"])

        m = re.match(r"^/api/run/([^/]+)/(report|review|summary)$", path)
        if m:
            run_id, kind = m.group(1), m.group(2)
            if not _RUN_ID.match(run_id):
                return self._send_text(400, "bad run id", "text/plain; charset=utf-8")
            folder = (RUNS_DIR / run_id).resolve()
            if not str(folder).startswith(str(RUNS_DIR.resolve()) + "\\") and not str(folder).startswith(str(RUNS_DIR.resolve()) + "/"):
                return self._send_text(404, "not found", "text/plain; charset=utf-8")
            if kind == "summary":
                return self._json(200, run_summary(folder))
            if kind == "report":
                report = folder / "report.md"
                if not report.is_file():
                    return self._send_text(404, "no report", "text/plain; charset=utf-8")
                return self._send_text(200, report.read_text(encoding="utf-8"), "text/plain; charset=utf-8")
            review = folder / "review.json"
            if not review.is_file():
                return self._send_text(404, "no review", "text/plain; charset=utf-8")
            return self._send_text(200, review.read_text(encoding="utf-8"), _CONTENT[".json"])

        return self._send_text(404, "not found", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):  # quiet
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = DashboardServer((args.host, args.port), Handler)
    print(f"Shadow 查看器已启动： http://{args.host}:{args.port}")
    print(f"运行目录：{RUNS_DIR}")
    print("Ctrl+C 退出。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
