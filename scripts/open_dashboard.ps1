$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$python = Join-Path $workspace '.venv-acceptance\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Python environment is missing: .venv-acceptance' }
$url = 'http://127.0.0.1:8765/settings'
$ready = $false
try { $ready = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch {}
if (-not $ready) {
    $script = Join-Path $workspace 'scripts\serve_dashboard.py'
    Start-Process -FilePath $python -ArgumentList @('"' + $script + '"') -WindowStyle Hidden
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        try { $ready = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1).StatusCode -eq 200 } catch {}
        if ($ready) { break }
    }
}
if (-not $ready) { throw 'Could not start the local dashboard on port 8765.' }
Start-Process $url
