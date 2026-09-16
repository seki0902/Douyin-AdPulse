"""Environment-backed configuration for the read-only daily pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value.strip() if value else None


@dataclass(frozen=True)
class Settings:
    oceanengine_base_url: str = "https://api.oceanengine.com"
    oceanengine_token_url: str | None = None
    oceanengine_app_id: str | None = None
    oceanengine_app_secret: str | None = None
    oceanengine_refresh_token: str | None = None
    oceanengine_access_token: str | None = None
    oceanengine_local_account_id: str | None = None
    oceanengine_project_list_path: str = "/open_api/v3.0/local/project/list/"
    oceanengine_report_path: str | None = None
    oceanengine_report_method: str | None = None
    shimo_feedback_export: Path | None = None
    database_url: str | None = None
    pipeline_version: str = "p1-readonly-v1"
    timezone: str = "Asia/Shanghai"

    @classmethod
    def from_env(cls) -> "Settings":
        feedback = _env("SHIMO_FEEDBACK_EXPORT")
        return cls(
            oceanengine_base_url=_env("OCEANENGINE_BASE_URL", cls.oceanengine_base_url) or cls.oceanengine_base_url,
            oceanengine_token_url=_env("OCEANENGINE_TOKEN_URL"),
            oceanengine_app_id=_env("OCEANENGINE_APP_ID"),
            oceanengine_app_secret=_env("OCEANENGINE_APP_SECRET"),
            oceanengine_refresh_token=_env("OCEANENGINE_REFRESH_TOKEN"),
            oceanengine_access_token=_env("OCEANENGINE_ACCESS_TOKEN"),
            oceanengine_local_account_id=_env("OCEANENGINE_LOCAL_ACCOUNT_ID"),
            oceanengine_project_list_path=_env("OCEANENGINE_PROJECT_LIST_PATH", cls.oceanengine_project_list_path) or cls.oceanengine_project_list_path,
            oceanengine_report_path=_env("OCEANENGINE_REPORT_PATH"),
            oceanengine_report_method=_env("OCEANENGINE_REPORT_METHOD"),
            shimo_feedback_export=Path(feedback) if feedback else None,
            database_url=_env("DATABASE_URL"),
            pipeline_version=_env("PIPELINE_VERSION", cls.pipeline_version) or cls.pipeline_version,
            timezone=_env("TIMEZONE", cls.timezone) or cls.timezone,
        )

    def missing_for_project_probe(self) -> list[str]:
        missing = []
        if not self.oceanengine_local_account_id:
            missing.append("OCEANENGINE_LOCAL_ACCOUNT_ID")
        if not (self.oceanengine_access_token or self.oceanengine_refresh_token):
            missing.append("OCEANENGINE_ACCESS_TOKEN 或 OCEANENGINE_REFRESH_TOKEN")
        return missing

    def missing_for_token_refresh(self) -> list[str]:
        fields = {
            "OCEANENGINE_TOKEN_URL": self.oceanengine_token_url,
            "OCEANENGINE_APP_ID": self.oceanengine_app_id,
            "OCEANENGINE_APP_SECRET": self.oceanengine_app_secret,
            "OCEANENGINE_REFRESH_TOKEN": self.oceanengine_refresh_token,
        }
        return [name for name, value in fields.items() if not value]
