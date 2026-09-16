"""Local Shimo feedback export adapter used before the live Shimo API is verified."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_feedback_export(path: Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=["lead_id", "lead_date", "is_valid", "is_contacted"])
    if not path.exists():
        raise FileNotFoundError(f"石墨反馈文件不存在: {path}")
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError("石墨反馈暂支持 CSV/XLSX 导出文件")
