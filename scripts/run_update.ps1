# Soccer Model - Weekly Automation
# Two scheduled runs use this one script:
#   Tuesday 12:00  ->  run_update.ps1              (Mode settle:  update, then results)
#   Friday  12:00  ->  run_update.ps1 -Mode predict (Mode predict: update, then predict)
# A failed update skips the next step (no predictions on stale ratings).
# Predict console output is saved to output\predict_latest.txt (and a dated copy).
# Session 17: each mode also runs scripts\luck_paper_big5.py (paper only) -> output\luck_big5_latest.txt

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
    # --- Step 3a: Big-5 luck paper log settle (paper only; failure never affects the steps above) ---
    try {
        & $Python scripts\luck_paper_big5.py settle 2>&1 | Out-File "$ProjectDir\output\luck_big5_latest.txt" -Encoding utf8
        Log "luck_paper_big5 settle complete (exit code: $LASTEXITCODE)"
    } catch { Log "luck_paper_big5 settle FAILED: $_" }
} else {
    # --- Step 2b: Predict and log this round's paper bets ---
    $stamp = Get-Date -Format 'yyyy-MM-dd'
    New-Item -ItemType Directory -Force "$ProjectDir\output\predictions" | Out-Null
    # Capture once, write both copies as UTF-8 (Tee-Object in PowerShell 5.1 writes UTF-16)
    $predictOut  = & $Python run.py predict 2>&1
    $predictCode = $LASTEXITCODE
    $predictOut | Out-File "$ProjectDir\output\predictions\predict_$stamp.txt" -Encoding utf8
    $predictOut | Out-File "$ProjectDir\output\predict_latest.txt" -Encoding utf8
    Log "run.py predict complete (exit code: $predictCode) - output in output\predict_latest.txt"
    # --- Step 3b: Big-5 luck paper log (paper only, ~8 Odds API credits; failure never affects the steps above) ---
    try {
        & $Python scripts\luck_paper_big5.py log 2>&1 | Out-File "$ProjectDir\output\luck_big5_latest.txt" -Encoding utf8
        Log "luck_paper_big5 log complete (exit code: $LASTEXITCODE)"
    } catch { Log "luck_paper_big5 log FAILED: $_" }
}

Log "Task finished"
