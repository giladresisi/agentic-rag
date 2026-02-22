# PowerShell script to start backend server after killing processes on port 8000

Write-Host "=== Starting Backend Server ===" -ForegroundColor Cyan
Write-Host ""

# Find processes using port 8000
Write-Host "Checking for existing processes on port 8000..." -ForegroundColor Yellow
$connections = netstat -ano | Select-String ":8000.*LISTENING"

if ($connections) {
    $pids = $connections | ForEach-Object {
        $_.ToString() -split '\s+' | Select-Object -Last 1
    } | Select-Object -Unique

    Write-Host "Found $($pids.Count) process(es) on port 8000" -ForegroundColor Yellow

    foreach ($pid in $pids) {
        Write-Host "  Killing PID $pid..." -ForegroundColor Yellow
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "    [OK] Killed PID $pid" -ForegroundColor Green
        } catch {
            Write-Host "    [WARN] Could not kill PID $pid (may have already exited)" -ForegroundColor DarkYellow
        }
    }

    Write-Host ""
    Write-Host "Waiting 2 seconds for processes to terminate..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
} else {
    Write-Host "[OK] No existing processes found on port 8000" -ForegroundColor Green
    Write-Host ""
}

# Verify port is clear
$remaining = netstat -ano | Select-String ":8000.*LISTENING"
if ($remaining) {
    Write-Host "[ERROR] Port 8000 still has active connections!" -ForegroundColor Red
    Write-Host "You may need to manually kill Python processes:" -ForegroundColor Red
    Write-Host "  Get-Process python* | Stop-Process -Force" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "[OK] Port 8000 is clear" -ForegroundColor Green
Write-Host ""

# Start backend server
Write-Host "Starting uvicorn server on port 8000..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Use venv's uvicorn directly — avoids relying on PATH after activation
# (system Python may shadow venv if activation doesn't propagate correctly)
& ".\venv\Scripts\uvicorn.exe" main:app --reload --port 8000
