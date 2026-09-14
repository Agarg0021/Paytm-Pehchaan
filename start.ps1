$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process powershell -WorkingDirectory "$root\backend" -ArgumentList "-NoExit", "-Command", "python -m uvicorn main:app --reload --port 8000"
Start-Process powershell -WorkingDirectory "$root\frontend" -ArgumentList "-NoExit", "-Command", "npm run dev"
Write-Host "Backend  http://127.0.0.1:8000"
Write-Host "Frontend http://localhost:5173"
Write-Host "1 counter  2 scoreboard  3 pruning  |  space = next payment  |  r = reset"
