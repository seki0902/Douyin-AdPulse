"""Read the real report date-picker markup without changing report data."""
from __future__ import annotations

import json
from pathlib import Path

from browser_downloader import _import_playwright, load_browser_config


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = load_browser_config(ROOT / "browser_download_config_mtd_202609.json")
    spec = config.reports[0]
    with _import_playwright()() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.profile_dir), channel="chrome", headless=False,
            args=[f"--profile-directory={config.profile_name}"],
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(spec.url, wait_until="domcontentloaded", timeout=config.timeout_ms)
            page.locator(spec.tab_selector).click(timeout=config.timeout_ms)
            start = page.locator(spec.date_start_selector)
            start.click(timeout=config.timeout_ms)
            page.wait_for_timeout(800)
            destination = ROOT / "outputs" / "month_review" / "2026-09"
            destination.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(destination / "date-picker.png"), full_page=False)
            visible_inputs = page.locator("input:visible")
            details = []
            for index in range(visible_inputs.count()):
                node = visible_inputs.nth(index)
                details.append({
                    "index": index,
                    "placeholder": node.get_attribute("placeholder"),
                    "readonly": node.get_attribute("readonly"),
                    "value": node.input_value(),
                    "outer_html": node.evaluate("node => node.outerHTML"),
                })
            month_shortcut = page.get_by_text("本月", exact=True)
            payload = {"url": page.url, "visible_inputs": details, "body_text": page.locator("body").inner_text(),
                       "month_shortcut_count": month_shortcut.count()}
            if month_shortcut.count() == 1:
                month_shortcut.click()
                page.wait_for_timeout(500)
                payload["after_month"] = {
                    "start": page.locator(spec.date_start_selector).input_value(),
                    "end": page.locator(spec.date_end_selector).input_value(),
                }
                page.locator(spec.date_end_selector).click()
                page.wait_for_timeout(300)
                fifteens = page.get_by_text("15", exact=True)
                payload["fifteen_candidates"] = [
                    {"html": fifteens.nth(index).evaluate("node => node.outerHTML")}
                    for index in range(fifteens.count())
                ]
            (destination / "date-picker.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"status": "success", "artifact": str(destination / "date-picker.json")}, ensure_ascii=False))
        finally:
            context.close()


if __name__ == "__main__":
    main()
