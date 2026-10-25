# Soccer Model - Weekly Automation
# Two scheduled runs use this one script:
#   Tuesday 12:00  ->  run_update.ps1              (Mode settle:  update, then results)
#   Friday  12:00  ->  run_update.ps1 -Mode predict (Mode predict: update, then predict)
# A failed update skips the next step (no predictions on stale ratings).
# Predict console output is saved to output\predict_latest.txt (and a dated copy).

param([ValidateSet('settle','predict')][string]$Mode = 'settle')

$ProjectDir = "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
$Python     = "C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
$LogFile    = "$ProjectDir\output\scheduler_log.txt"

function Log($msg) { Add-Content $LogFile "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg" }

Set-Location $ProjectDir
$env:PYTHONIOENCODING = "utf-8"
Log "Task started (mode: $Mode)"

# --- Step 1: Update data from Understat + football-data ---
& $Python run.py update
$updateCode = $LASTEXITCODE
Log "run.py update complete (exit code: $updateCode)"

if ($updateCode -ne 0) {
    Log "Update failed - skipping $Mode step"
} elseif ($Mode -eq 'settle') {
    # --- Step 2a: Settle paper trades ---
    & $Python run.py results
    Log "run.py results complete (exit code: $LASTEXITCODE)"
} else {
    # --- Step 2b: Predict and log this round's paper bets ---
    $stamp = Get-Date -Format 'yyyy-MM-dd'
    New-Item -ItemType Directory -Force "$ProjectDir\output\predictions" | Out-Null
    & $Python run.py predict 2>&1 | Tee-Object -FilePath "$ProjectDir\output\predictions\predict_$stamp.txt" | Out-File "$ProjectDir\output\predict_latest.txt" -Encoding utf8
    Log "run.py predict complete (exit code: $LASTEXITCODE) - output in output\predict_latest.txt"
}

Log "Task finished"
