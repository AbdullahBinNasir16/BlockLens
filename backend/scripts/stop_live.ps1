# Stop the BlockLens API (the live scorer and resolver). PostgreSQL is left
# running; stop it with: .local\pgsql\bin\pg_ctl.exe -D .local\pgdata stop
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match 'blocklens\.api\.app' }
foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -Confirm:$false }
"stopped $(@($procs).Count) process(es)"
