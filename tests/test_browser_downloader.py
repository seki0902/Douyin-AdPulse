from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from browser_downloader import BrowserDownloadConfig, ReportSpec, download_reports


class BrowserDownloaderTests(unittest.TestCase):
    def test_playwright_download_manifest(self) -> None:
        html = """
        <input id="start"><input id="end">
        <button id="query" type="button">查询</button>
        <div id="ready">数据已加载</div>
        <a id="export" download="unit.xlsx"
           href="data:application/octet-stream;base64,ZmFrZS1yZXBvcnQ=">导出</a>
        """
        spec = ReportSpec(
            kind="unit",
            name="测试报表",
            url="data:text/html," + quote(html),
            tab_selector=None,
            date_start_selector="#start",
            date_end_selector="#end",
            query_selector="#query",
            export_selector="#export",
            ready_selector="#ready",
            file_prefix="unit",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "profile").mkdir()
            manifest = download_reports(
                BrowserDownloadConfig(
                    profile_dir=root / "profile",
                    profile_name="Default",
                    output_dir=root / "downloads",
                    report_url=spec.url,
                    reports=(spec,),
                    browser_channel="msedge",
                    headless=True,
                )
            )
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["data_date"], manifest["date_end"])
            downloaded = Path(manifest["files"][0]["path"])
            self.assertTrue(downloaded.exists())
            self.assertGreater(downloaded.stat().st_size, 0)
