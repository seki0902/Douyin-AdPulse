param(
    [string]$TaskName = "Local Growth Agent Daily",
    [string]$StartTime = "09:00",
    [string]$BrowserConfig = "$PSScriptRoot\..\browser_download_config.json"
)

$ErrorActionPreference = 'Stop'
$runner = (Resolve-Path "$PSScriptRoot\run_daily.ps1").Path
$BrowserConfig = (Resolve-Path -LiteralPath $BrowserConfig).Path
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -BrowserConfig `"$BrowserConfig`""
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument $arguments -WorkingDirectory (Split-Path $BrowserConfig)
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($StartTime, "HH:mm", $null))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Local Growth Agent daily browser download and report" -Force
Write-Output "已注册任务：$TaskName，执行时间：$StartTime"
