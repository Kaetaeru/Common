$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Requirements = Join-Path $ProjectDir 'requirements.txt'
$PythonVersion = '3.13.15'

function Test-PythonExe([string]$Exe) {
    if (-not $Exe) { return $false }
    try {
        & $Exe -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-Python {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $resolved = (& $py.Source -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1).Trim()
            if (Test-PythonExe $resolved) { return $resolved }
        } catch {}
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python -and (Test-PythonExe $python.Source)) { return $python.Source }

    $patterns = @(
        "$env:LocalAppData\Programs\Python\Python*\python.exe",
        "$env:ProgramFiles\Python*\python.exe"
    )
    foreach ($pattern in $patterns) {
        $candidate = Get-Item $pattern -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate -and (Test-PythonExe $candidate.FullName)) { return $candidate.FullName }
    }

    return $null
}

Write-Host 'APU Schedule Builder - Windows dependency installer' -ForegroundColor Cyan
Write-Host ''

$PythonExe = Find-Python
if (-not $PythonExe) {
    Write-Host "Python not found. Installing Python $PythonVersion..." -ForegroundColor Yellow

    $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
    $installer = Join-Path $env:TEMP "python-$PythonVersion-$arch.exe"
    $url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-$arch.exe"

    Write-Host "Downloading from $url"
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

    $args = '/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 Include_test=0'
    $process = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Python installer failed with exit code $($process.ExitCode)."
    }

    Remove-Item $installer -Force -ErrorAction SilentlyContinue
    $PythonExe = Find-Python
    if (-not $PythonExe) {
        throw 'Python was installed but could not be located. Restart PowerShell and run this script again.'
    }
} else {
    Write-Host "Python found: $PythonExe" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Preparing pip...'
& $PythonExe -m ensurepip --upgrade
if ($LASTEXITCODE -ne 0) { throw 'Failed to prepare pip.' }

& $PythonExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Failed to update pip.' }

if (-not (Test-Path $Requirements)) {
    throw "requirements.txt was not found at $Requirements"
}

Write-Host ''
Write-Host 'Installing Python packages...'
& $PythonExe -m pip install -r $Requirements
if ($LASTEXITCODE -ne 0) { throw 'Failed to install Python packages.' }

Write-Host ''
Write-Host 'Verifying installation...'
& $PythonExe -c "import sys, openpyxl, selenium; print('Python', sys.version.split()[0]); print('openpyxl', openpyxl.__version__); print('selenium', selenium.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }

Write-Host ''
Write-Host 'READY. Double-click run_windows.bat to start APU Schedule Builder.' -ForegroundColor Green
Read-Host 'Press Enter to close'
