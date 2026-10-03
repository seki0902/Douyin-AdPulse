# Local report dashboard

This branch adds a local-only report dashboard to the existing AdPulse project. It presents business metrics, agent coverage, and expandable evidence without uploading report data.

Run it with:

```powershell
py -3 scripts/serve_dashboard.py
```

Then open `http://127.0.0.1:8765/`. Reports remain local under `artifacts/model-shadow/`, which is ignored by Git. The model settings page stores configuration through the local Agent integration when that private integration is available; no API key is committed by this branch.

On Windows, double-click `open_dashboard.cmd` to start the service and open the dashboard automatically.

The browser test uses synthetic data only:

```powershell
python -m pytest tests/test_dashboard_report_ui.py -q
```
