$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
function Test-LocalPort([int]$Port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync('127.0.0.1', $Port)
        [void]$task.Wait(600)
        return $client.Connected
    } catch { return $false } finally { $client.Dispose() }
}
$pgBin = Join-Path $projectRoot 'build/postgres-runtime/pgsql/bin'
$pgData = Join-Path $projectRoot 'build/postgres-data'
if (!(Test-Path (Join-Path $pgData 'PG_VERSION'))) { throw 'This legacy launcher requires Andrew''s private build/postgres-data database. For a fresh Windows or Mac install, follow docs/team-local-setup.md and use Run-LocalApp.py.' }
& (Join-Path $pgBin 'pg_ctl.exe') -D $pgData status *> $null
if ($LASTEXITCODE -ne 0) {
    $pgArgs = @('-D', "`"$pgData`"", '-l', "`"$(Join-Path $projectRoot 'build/postgres.log')`"", '-o', '"-h 127.0.0.1 -p 5432"', '-w', 'start')
    $pg = Start-Process (Join-Path $pgBin 'pg_ctl.exe') -ArgumentList $pgArgs -WindowStyle Hidden -Wait -PassThru
    if ($pg.ExitCode -ne 0) { throw 'Database startup failed; see build/postgres.log.' }
}
if (!(Test-LocalPort 8000)) {
    $previousModel = $env:MODEL_DIRECTORY
    $previousHelper = $env:PREDICTION_MODEL_DIR
    try {
        $env:MODEL_DIRECTORY = Join-Path $projectRoot 'build/live-models-expanded'
        $env:PREDICTION_MODEL_DIR = $env:MODEL_DIRECTORY
        Start-Process (Get-Command python).Source -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'build/backend-output.log') -RedirectStandardError (Join-Path $projectRoot 'build/backend-error.log')
    } finally { $env:MODEL_DIRECTORY=$previousModel; $env:PREDICTION_MODEL_DIR=$previousHelper }
} else { Write-Host 'Port 8000 is already in use; existing process preserved.' }
if (!(Test-LocalPort 5173)) {
    $vite = Join-Path $projectRoot 'frontend/node_modules/vite/bin/vite.js'
    Start-Process (Get-Command node).Source -ArgumentList @("`"$vite`"",'--host','127.0.0.1','--port','5173','--strictPort') -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'build/frontend-output.log') -RedirectStandardError (Join-Path $projectRoot 'build/frontend-error.log')
} else { Write-Host 'Port 5173 is already in use; existing process preserved.' }
Write-Host 'Open http://127.0.0.1:5173/dashboard after startup completes.'
