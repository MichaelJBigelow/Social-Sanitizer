<#
.SYNOPSIS
  Creates Windows shortcuts that start Social Sanitizer with no console window.

.DESCRIPTION
  Makes "Social Sanitizer" shortcuts in the Start Menu and in this repository folder
  (and on the Desktop with -Desktop). They run the project's venv with pythonw.exe,
  which never opens a console. App output goes to
  %LOCALAPPDATA%\Social Sanitizer\Logs\app.log. Re-run this script if you move the
  repository.

  Run it from the repository folder:
    powershell -ExecutionPolicy Bypass -File scripts\make-windows-launcher.ps1 [-Desktop]
#>
param([switch]$Desktop)

$ErrorActionPreference = 'Stop'

$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $Repo '.venv\Scripts\python.exe'
$Pythonw = Join-Path $Repo '.venv\Scripts\pythonw.exe'
if (-not (Test-Path $Pythonw)) {
    Write-Error "No virtualenv at $Repo\.venv. Set it up first (see README), then re-run."
    exit 1
}

# Windows shortcuts need an .ico file; draw one next to the app's other data.
$DataDir = Join-Path $env:LOCALAPPDATA 'Social Sanitizer'
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$Icon = Join-Path $DataDir 'icon.ico'
& $Python (Join-Path $Repo 'scripts\make_icon.py') $Icon
if ($LASTEXITCODE -ne 0) { throw "Couldn't create the icon." }

$Shortcuts = @(
    (Join-Path ([Environment]::GetFolderPath('Programs')) 'Social Sanitizer.lnk'),
    (Join-Path $Repo 'Social Sanitizer.lnk')
)
if ($Desktop) {
    $Shortcuts += (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Social Sanitizer.lnk')
}

$Shell = New-Object -ComObject WScript.Shell
foreach ($Path in $Shortcuts) {
    $Link = $Shell.CreateShortcut($Path)
    $Link.TargetPath = $Pythonw
    $Link.Arguments = '-m social_sanitizer'
    $Link.WorkingDirectory = $Repo
    $Link.IconLocation = "$Icon,0"
    $Link.Description = 'Find and report creepy comments on Instagram posts'
    $Link.Save()
    Write-Host "Created $Path"
}
