import json
import threading

import pytest
from playwright.sync_api import sync_playwright

from scripts import serve_dashboard as dashboard


@pytest.fixture
def dashboard_url(tmp_path, monkeypatch):
    run = tmp_path / "model_shadow_2026-10-03_fixture"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({
        "report_date": "2026-10-03", "model": "deepseek-chat"
    }), encoding="utf-8")
    (run / "review.json").write_text(json.dumps({
        "structural_status": "pass", "operational_status": "partial",
        "model_calls": 18, "semantic_status": "pending_review",
        "issues": ["账户 2 单元与素材对账未通过"],
        "agent_coverage": {
            "supervisor": True, "data_analysis": True,
            "ads_diagnosis": True, "content_review": False, "strategy": True,
        },
    }), encoding="utf-8")
    (run / "state.json").write_text(json.dumps({
        "data_analysis_result": {
            "observations": [{"evidence": [{
                "source": "get_account_metrics", "object_type": "account",
                "time_range": "30d 2026-09-04~2026-10-03",
                "value": {"spend": 1234.56, "impressions": 10000, "clicks": 345,
                          "leads": 12, "cpl": 102.88, "ctr": 0.0345, "cvr": 0.02},
            }]}],
        },
    }), encoding="utf-8")
    (run / "report.md").write_text("""# 投放诊断日报｜2026-10-03
run_id：fixture

【账户总体】
账户消耗集中在一个计划，数据量偏低，暂不判断整体恶化。

【待处理计划】
- 计划 A：单日留资波动。
- 计划 B：素材消耗但无留资。
- 计划 C：样本不足。
- 计划 D：缺少设置快照。
- 计划 E：需要继续观察。

【问题更可能在哪】
- 计划设置和素材归属证据不足。

【今天具体做什么】
- 保持计划 A，补齐设置快照。
- 检查计划 B 的素材归属。

【下一次看什么】
- 明日复核留资和消耗变化。
""", encoding="utf-8")
    monkeypatch.setattr(dashboard, "RUNS_DIR", tmp_path)
    server = dashboard.DashboardServer(("127.0.0.1", 0), dashboard.Handler, model_store=object())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def test_dashboard_starts_without_private_agent_project(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "AGENT_DIR", tmp_path / "missing-agent")
    server = dashboard.DashboardServer(("127.0.0.1", 0), dashboard.Handler)
    try:
        settings = server.model_store.public()
        assert settings["settings_available"] is False
        assert settings["key_configured"] is False
    finally:
        server.server_close()


def test_report_is_rendered_as_scannable_dashboard(dashboard_url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(dashboard_url)
        page.get_by_text("账户消耗集中在一个计划").wait_for()

        assert page.locator(".metric-card").count() == 4
        assert page.get_by_text("¥1,234.56", exact=True).is_visible()
        assert page.get_by_text("102.88", exact=False).is_visible()
        assert page.locator(".report-card").count() == 5
        assert page.get_by_role("heading", name="今天具体做什么").is_visible()
        assert page.get_by_text("4 / 5 已完成", exact=True).is_visible()
        assert page.locator("#meta").get_by_text("需复核", exact=True).is_visible()
        assert page.locator("details.report-more").count() == 1
        assert page.get_by_text("展开其余 1 项").is_visible()

        page.set_viewport_size({"width": 375, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.get_by_role("heading", name="今天具体做什么").is_visible()
        browser.close()
