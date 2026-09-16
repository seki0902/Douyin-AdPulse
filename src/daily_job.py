"""Daily Local Growth Agent runner.

The production path is browser download -> validation -> deterministic import
-> state update -> recommendations -> report output. ``--input-dir`` is kept
as a controlled replay mode for testing the same downstream pipeline with
already downloaded files.
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from browser_downloader import BrowserDownloadError, load_browser_config, download_reports, resolve_date_range
from recommendation_engine import build_recommendations, render_recommendations_markdown
from run_import import discover_exports, run_import
from state_store import StateStore
from history_context import enrich_with_history
from replay_core import render_markdown
from execution_feedback import build_execution_feedback_context
from execution_policy import build_pending_execution_actions, load_execution_policy
from clawbot_pusher import push_daily_report
from shimo_web_sheet import (
    read_execution_feedback,
    read_manual_quality,
    write_platform_metrics,
    write_recommendations,
)


class DailyJobError(RuntimeError):
    """Raised when the daily pipeline cannot produce a trustworthy report."""


def _account_id() -> str | None:
    return (os.getenv("LOCAL_PUSH_ACCOUNT_ID") or os.getenv("OCEANENGINE_LOCAL_ACCOUNT_ID") or "").strip() or None


def _file_manifest(input_dir: Path) -> dict[str, Any]:
    discovered = discover_exports(input_dir)
    files: list[dict[str, Any]] = []
    for kind, path in discovered.items():
        if path is None:
            continue
        if not path.exists() or path.stat().st_size <= 0:
            raise DailyJobError(f"{kind} 输入文件不存在或为空: {path}")
        files.append({"kind": kind, "path": str(path), "size": path.stat().st_size})
    if not discovered["unit"] or not discovered["material"]:
        raise DailyJobError("单元/计划报表和视频/素材报表必须同时存在")
    return {"files": files, "input_dir": str(input_dir)}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_key(account_id: str | None, data_date: str) -> str:
    return f"{account_id or 'default'}:{data_date}"


def _persist_completed_feedback(store: StateStore, feedback: dict[str, Any]) -> dict[str, Any]:
    """Store only unambiguous line-for-line human feedback from Shimo."""
    recommendation_ids = [item.strip() for item in str(feedback.get("recommendation_ids") or "").splitlines() if item.strip()]
    statuses = [item.strip() for item in str(feedback.get("execution_status") or "").splitlines() if item.strip()]
    if not recommendation_ids or not statuses:
        return {"status": "skipped_empty", "recorded": 0}
    if len(recommendation_ids) != len(statuses):
        return {
            "status": "skipped_ambiguous", "recorded": 0,
            "reason": "建议ID与执行状态的非空行数不一致",
        }
    common = {
        "data_date": feedback.get("data_date"),
        "result_after_1d": feedback.get("result_after_1d"),
        "result_after_3d": feedback.get("result_after_3d"),
        "notes": feedback.get("notes"),
    }
    feedback_id_list = []
    for recommendation_id, status in zip(recommendation_ids, statuses):
        feedback_id = store.record_feedback_if_new(
            recommendation_id, status,
            actual_action=feedback.get("actual_action") or None,
            actual_value=feedback.get("executed_at") or None,
            operator="shimo",
            observed_result=common,
        )
        if feedback_id:
            feedback_id_list.append(feedback_id)
    return {"status": "success", "recorded": len(feedback_id_list), "feedback_ids": feedback_id_list}


def run_daily(*, browser_config_path: Path | None = None, input_dir: Path | None = None,
              output_root: Path | None = None, state_db: Path | None = None,
              force: bool = False) -> dict[str, Any]:
    if browser_config_path is None and input_dir is None:
        raise DailyJobError("必须提供 --browser-config，或使用 --input-dir 运行已有文件")
    if browser_config_path is not None and input_dir is not None:
        raise DailyJobError("--browser-config 与 --input-dir 只能二选一")

    output_root = output_root or Path(__file__).resolve().parents[1] / "outputs" / "daily_reports"
    state_db = state_db or Path(__file__).resolve().parents[1] / "state" / "local_growth_agent.sqlite3"
    output_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any]
    expected_date: str | None = None
    account_id = _account_id()
    if browser_config_path is not None:
        config = load_browser_config(browser_config_path)
        account_id = account_id or parse_qs(urlparse(config.report_url).query).get("advid", [None])[0]
        _, report_end = resolve_date_range(config.date_mode, timezone=config.timezone)
        expected_date = report_end.isoformat()
        run_key = _run_key(account_id, expected_date)
        run_output = output_root / expected_date
        with StateStore(state_db) as store:
            run_id, completed, current_status = store.begin_run(run_key, expected_date, account_id, "v3-browser-daily")
            if completed and not force:
                return {"status": "skipped_duplicate", "run_id": run_id, "run_key": run_key, "data_date": expected_date}
            try:
                manifest = download_reports(config)
                manifest.update({"run_id": run_id, "run_key": run_key})
                input_dir = config.output_dir
                manifest.update(_file_manifest(input_dir))
                report = run_import(input_dir, run_output)
                if report["data_date"] != expected_date:
                    raise DailyJobError(
                        f"报表统计日期不符：期望 {expected_date}，实际 {report['data_date']}；不生成正常日报"
                    )
                result = _finalize_success(store, run_id, run_key, manifest, report, run_output)
                return result
            except Exception as exc:
                store.finish_run(run_id, "failed", error_summary=str(exc), metadata={"manifest": manifest if "manifest" in locals() else {}})
                failure = {
                    "run_id": run_id,
                    "run_key": run_key,
                    "data_date": expected_date,
                    "status": "failed",
                    "errors": [str(exc)],
                }
                run_output.mkdir(parents=True, exist_ok=True)
                _write_json(run_output / "run_manifest.json", failure)
                if isinstance(exc, BrowserDownloadError):
                    raise DailyJobError(str(exc)) from exc
                raise

    manual_manifest = _file_manifest(input_dir)
    manual_output = output_root if output_root.name != "daily_reports" else output_root / "manual_latest"
    report = run_import(input_dir, manual_output)
    expected_date = report["data_date"]
    run_key = _run_key(account_id, expected_date)
    with StateStore(state_db) as store:
        run_id, completed, current_status = store.begin_run(run_key, expected_date, account_id, "v3-manual-input")
        if completed and not force:
            return {"status": "skipped_duplicate", "run_id": run_id, "run_key": run_key, "data_date": expected_date}
        manifest = {
            "run_id": run_id,
            "run_key": run_key,
            "account_id": account_id,
            "data_date": expected_date,
            "fetched_at": datetime.now().astimezone().isoformat(),
            "sources": [f"manual_input_{item['kind']}" for item in manual_manifest["files"]],
            "status": "manual_input",
            **manual_manifest,
        }
        result = _finalize_success(store, run_id, run_key, manifest, report, manual_output)
        return result


def _finalize_success(store: StateStore, run_id: str, run_key: str, manifest: dict[str, Any],
                      report: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    current_report = report
    account_id = manifest.get("account_id") or run_key.rsplit(":", 1)[0]
    if account_id == "default":
        raise DailyJobError("历史诊断需要明确的账户 ID")
    try:
        prior_date = (datetime.fromisoformat(report["data_date"]).date() - timedelta(days=1)).isoformat()
        execution_feedback = read_execution_feedback(prior_date)
        execution_feedback["local_persistence"] = _persist_completed_feedback(store, execution_feedback)
    except Exception as exc:
        execution_feedback = {"status": "unavailable", "error": str(exc)}
    previous_feedback = store.list_feedback()
    report["execution_feedback_context"] = build_execution_feedback_context(previous_feedback)
    try:
        manual_quality = read_manual_quality(report["data_date"])
        report["yesterday"] = {**(report.get("yesterday") or {}), **manual_quality}
        spend = report["yesterday"].get("spend")
        valid = manual_quality["valid_leads"]
        contacted = manual_quality["contacted_leads"]
        report["yesterday"]["valid_lead_cost"] = None if valid in (None, 0) else round(spend / valid, 2)
        report["yesterday"]["contact_cost"] = None if contacted in (None, 0) else round(spend / contacted, 2)
        report["manual_quality_source"] = "shimo_web"
    except Exception as exc:
        report["manual_quality_source"] = "unavailable"
        report.setdefault("notes", []).append(f"石墨人工质量数据未合并：{exc}")
    report = enrich_with_history(report, store.load_history(account_id, report["data_date"]))
    report["account_id"] = account_id
    recommendations = build_recommendations(report, run_key)
    execution_policy = load_execution_policy()
    pending_execution_actions = build_pending_execution_actions(report, recommendations, execution_policy)
    report["pending_execution_actions"] = pending_execution_actions
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "run_manifest.json", {**manifest, "status": "success"})
    _write_json(output_dir / "recommendations.json", {"run_key": run_key, "recommendations": recommendations})
    _write_json(output_dir / "pending_execution_actions.json", {
        "run_key": run_key, "policy": execution_policy, "actions": pending_execution_actions,
    })
    _write_json(output_dir / "previous_feedback.json", {"feedback": previous_feedback})
    _write_json(output_dir / "daily_report.json", report)
    daily_report = output_dir / "daily_report.md"
    daily_report.write_text(
        render_markdown(report)
        + "\n" + render_recommendations_markdown(recommendations),
        encoding="utf-8",
    )
    store.save_report(run_id, current_report)
    store.save_recommendations(run_id, recommendations)
    try:
        shimo_result = write_platform_metrics(report)
    except Exception as exc:
        shimo_result = {"status": "failed", "error": str(exc)}
    _write_json(output_dir / "shimo_sync.json", shimo_result)
    try:
        recommendation_sync = write_recommendations(report["data_date"], recommendations)
    except Exception as exc:
        recommendation_sync = {"status": "failed", "error": str(exc)}
    _write_json(output_dir / "shimo_recommendation_sync.json", recommendation_sync)
    _write_json(output_dir / "shimo_execution_feedback.json", execution_feedback)
    try:
        clawbot_push = push_daily_report(report, recommendations)
    except Exception as exc:
        clawbot_push = {"status": "failed", "error": str(exc)}
    _write_json(output_dir / "clawbot_push.json", clawbot_push)
    store.finish_run(
        run_id,
        "success",
        data_completeness=report.get("data_completeness"),
        metadata={"data_date": report["data_date"], "recommendation_count": len(recommendations),
                  "shimo_sync": shimo_result,
                  "shimo_recommendation_sync": recommendation_sync,
                  "shimo_execution_feedback": execution_feedback,
                  "clawbot_push": clawbot_push,
                  "pending_execution_action_count": len(pending_execution_actions),
                  "reconciliation_pass": report["reconciliation"]["all_pass"]},
    )
    return {
        "status": "success",
        "run_id": run_id,
        "run_key": run_key,
        "data_date": report["data_date"],
        "report": str(daily_report),
        "recommendations": str(output_dir / "recommendations.json"),
        "recommendation_count": len(recommendations),
        "previous_feedback_count": len(previous_feedback),
        "shimo_recommendation_sync": recommendation_sync,
        "shimo_execution_feedback": execution_feedback,
        "clawbot_push": clawbot_push,
        "pending_execution_action_count": len(pending_execution_actions),
        "reconciliation_pass": report["reconciliation"]["all_pass"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 Local Growth Agent 每日下载、分析和建议流程")
    parser.add_argument("--browser-config", type=Path, help="浏览器下载配置 JSON")
    parser.add_argument("--input-dir", type=Path, help="调试/回放模式：使用已下载文件目录")
    parser.add_argument("--output-root", type=Path, help="日报输出根目录")
    parser.add_argument("--state-db", type=Path, help="本地状态 SQLite 文件")
    parser.add_argument("--force", action="store_true", help="允许重跑已成功的同一统计日")
    args = parser.parse_args()
    result = run_daily(
        browser_config_path=args.browser_config,
        input_dir=args.input_dir,
        output_root=args.output_root,
        state_db=args.state_db,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
