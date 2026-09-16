"""Read September's human-owned quality fields from Shimo without editing cells."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from browser_downloader import _import_playwright, load_browser_config
from shimo_web_sheet import ROOT, _load_config, _number_or_none, _ready, _select, _date_value


def main() -> None:
    config = _load_config()
    browser = load_browser_config(ROOT / "browser_download_config.json")
    wanted = {date(2026, 9, day).isoformat() for day in range(1, 16)}
    rows: list[dict] = []
    with _import_playwright()() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(browser.profile_dir), channel="chrome", headless=False,
            args=[f"--profile-directory={browser.profile_name}"],
        )
        try:
            page = context.new_page()
            page.goto(config["url"], wait_until="domcontentloaded", timeout=60000)
            _ready(page, config["selectors"], config["sheet_name"])
            for row in range(int(config["first_daily_row"]), 401):
                raw_date = _select(page, config["selectors"], f"{config['columns']['date']}{row}")
                normal_date = _date_value(raw_date).replace("/", "-")
                if normal_date in wanted:
                    rows.append({
                        "data_date": normal_date, "row": row,
                        "spend": _number_or_none(_select(page, config["selectors"], f"B{row}")),
                        "platform_leads": _number_or_none(_select(page, config["selectors"], f"C{row}")),
                        "valid_leads": _number_or_none(_select(page, config["selectors"], f"E{row}")),
                        "contacted_leads": _number_or_none(_select(page, config["selectors"], f"M{row}")),
                    })
                if raw_date and normal_date > "2026-09-15":
                    break
        finally:
            context.close()
    output = ROOT / "outputs" / "month_review" / "2026-09" / "shimo_quality.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"period": "2026-09-01 to 2026-09-15", "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "success", "count": len(rows), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
