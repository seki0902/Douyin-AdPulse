"""Probe the verified local-push project-list endpoint.

This command is deliberately read-only. It requires a locally injected
Access-Token and local account ID, and never prints the response body.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:  # Support both PYTHONPATH=agent/src and package-style imports.
    from .config import Settings
except ImportError:  # pragma: no cover - exercised when run as a file.
    from config import Settings


def _count_items(payload: dict) -> int | None:
    for key in ("data", "list", "projects", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for nested_key in ("list", "projects", "rows"):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return len(nested)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only local-push project probe")
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    args = parser.parse_args()

    settings = Settings.from_env()
    missing = settings.missing_for_project_probe()
    if missing:
        print(f"配置不完整，未发起请求：{','.join(missing)}")
        return 2

    try:
        try:
            from .skills.oceanengine_client import OceanEngineApiError, OceanEngineClient
            from .skills.token_store import EnvTokenStore
        except ImportError:
            from skills.oceanengine_client import OceanEngineApiError, OceanEngineClient
            from skills.token_store import EnvTokenStore
    except ModuleNotFoundError as exc:
        print(f"缺少 P1 依赖，未发起请求：{exc.name}")
        print("请先安装 agent/requirements-p1.txt")
        return 3

    client = OceanEngineClient(settings, EnvTokenStore(settings.oceanengine_refresh_token))
    try:
        payload = client.get_local_projects()
    except (OceanEngineApiError, OSError) as exc:
        print(f"项目列表探测失败：{exc}")
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    count = _count_items(payload)
    print("项目列表探测成功")
    print(f"items={count if count is not None else 'unknown'}")
    if args.output:
        print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
