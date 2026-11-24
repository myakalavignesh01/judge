$ErrorActionPreference = 'Stop'
$Backend = $PSScriptRoot
$EnvPython = Join-Path $Backend '.venv\Scripts\python.exe'

if (-not (Test-Path $EnvPython)) {
    $PythonExe = $null
    $LocalPrograms = Join-Path $env:USERPROFILE 'AppData\Local\Programs\Python'
    $Candidates = @(
        (Join-Path $LocalPrograms 'Python314\python.exe'),
        (Join-Path $LocalPrograms 'Python313\python.exe'),
        (Join-Path $LocalPrograms 'Python312\python.exe'),
        (Join-Path $LocalPrograms 'Python311\python.exe')
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            try {
                & $Candidate --version *> $null
                if ($LASTEXITCODE -eq 0) { $PythonExe = $Candidate; break }
            } catch { }
        }
    }
    if (-not $PythonExe) {
        $Launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($Launcher) {
            try {
                & $Launcher.Source -3 --version *> $null
                if ($LASTEXITCODE -eq 0) { $PythonExe = $Launcher.Source; $PythonArgs = @('-3') }
            } catch { }
        }
    }
    if (-not $PythonExe) { throw 'Python 3.11 or newer was not found. Install Python and rerun this script.' }
    if ($PythonArgs) { & $PythonExe @PythonArgs -m venv (Join-Path $Backend '.venv') }
    else { & $PythonExe -m venv (Join-Path $Backend '.venv') }
    & $EnvPython -m pip install -r (Join-Path $Backend 'requirements.txt')
}

Push-Location $Backend
try {
    if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
    $Port = 0
    if ($env:JUDGEX_PORT) { $Port = [int]$env:JUDGEX_PORT }
    else {
        foreach ($CandidatePort in 8000..8010) {
            $Probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $CandidatePort)
            try { $Probe.Start(); $Probe.Stop(); $Port = $CandidatePort; break }
            catch { try { $Probe.Stop() } catch { } }
        }
    }
    if (-not $Port) { throw 'No available JudgeX port found between 8000 and 8010. Set JUDGEX_PORT to an available port and retry.' }
    $env:FRONTEND_ORIGINS = "http://localhost:$Port,http://127.0.0.1:$Port"
    $env:GOOGLE_REDIRECT_URI = "http://127.0.0.1:$Port/api/v1/auth/google/callback"
    Write-Host "JudgeX is starting at http://127.0.0.1:$Port"
    # Uvicorn's Windows file-watcher can fail in restricted desktop environments. Restart this script after backend edits.
    & $EnvPython -m uvicorn judgex.main:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
