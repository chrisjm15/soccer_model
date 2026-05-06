# Soccer Model — Weekly Update Script
# Called by Windows Task Scheduler every Tuesday 12:00 AEST
# Runs: python run.py update
# When CLI Task 2 is built, add the second line below (currently commented out)

$ProjectDir = "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
$Python     = "C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
$LogFile    = "$ProjectDir\output\scheduler_log.txt"

# --- Log start ---
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content $LogFile "[$timestamp] Task started"

Set-Location $ProjectDir

# --- Step 1: Update data from Understat + football-data ---
& $Python run.py update
Add-Content $LogFile "[$timestamp] run.py update complete (exit code: $LASTEXITCODE)"

# --- Step 2: Settle paper trading results (uncomment once CLI Task 2 is built) ---
# & $Python run.py results
# Add-Content $LogFile "[$timestamp] run.py results complete (exit code: $LASTEXITCODE)"

# --- Step 3: Sleep the machine ---
# Only reached if the script ran successfully.
# If you don't want the PC to sleep after running, comment out the line below.
Add-Content $LogFile "[$timestamp] Initiating sleep"
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::SetSuspendState(
    [System.Windows.Forms.PowerState]::Suspend, $false, $false
)
