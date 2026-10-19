# Start the BlockLens live stack: the portable PostgreSQL, then the API with
# its live scorer and forward-validation resolver. Safe to run twice: each
# part is started only if it is not already up.
#
#   powershell -ExecutionPolicy Bypass -File backend\scripts\start_live.ps1
#
# Logs: backend\data\live_api.log. Stop: backend\scripts\stop_live.ps1

$ErrorActionPreference = 'Stop'
$backend = Split-Path -Parent $PSScriptRoot
Set-Location $backend

$pg = Join-Path $backend '.local\pgsql\bin'
& "$pg\pg_isready.exe" -h 127.0.0.1 -p 5433 -U blocklens *> $null
if ($LASTEXITCODE -ne 0) {
    Start-Process -FilePath "$pg\pg_ctl.exe" -WindowStyle Hidden -ArgumentList @(
        '-D', (Join-Path $backend '.local\pgdata'), '-l', (Join-Path $backend '.local\pg.log'),
        '-o', '"-p 5433"', 'start')
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        & "$pg\pg_isready.exe" -h 127.0.0.1 -p 5433 -U blocklens *> $null
        if ($LASTEXITCODE -eq 0) { break }
    }
}
"postgres: up"

$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match 'blocklens\.api\.app' }
if ($running) { "api: already running (pid $($running[0].ProcessId))"; exit 0 }

$env:DATABASE_URL = 'postgresql+psycopg://blocklens@127.0.0.1:5433/blocklens'
$env:RPC_PER_SEC = '40'
$log = Join-Path $backend 'data\live_api.log'
$py = Join-Path $backend '.venv\Scripts\python.exe'
Start-Process -FilePath $py -WindowStyle Hidden -WorkingDirectory $backend `
    -RedirectStandardOutput $log -RedirectStandardError "$log.err" -ArgumentList @(
        '-m', 'uvicorn', 'blocklens.api.app:app', '--port', '8000', '--log-level', 'warning')
"api: started on http://127.0.0.1:8000 (log: $log)"
