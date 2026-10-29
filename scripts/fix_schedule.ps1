# Cowork session 18 (2026-10-29). Report + fix the settings of every "Soccer Model*" Windows task.
# Why: tasks made with schtasks /create (Status, Push, Telegram) do NOT run if the PC is asleep or off at the
# start time, and do not catch up later. This turns on "Run as soon as possible after a missed start" and
# "Wake the computer to run this task" on each one. It changes nothing else (times, actions stay the same).
# Output: output\schedule_check.txt
$Out = "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer\output\schedule_check.txt"
function Report($title) {
    Add-Content $Out "`r`n=== $title  $(Get-Date -Format 'yyyy-MM-dd HH:mm') ==="
    Get-ScheduledTask | Where-Object { $_.TaskName -like 'Soccer Model*' } | ForEach-Object {
        $i = $_ | Get-ScheduledTaskInfo
        Add-Content $Out ("{0,-30} state={1,-8} catch-up={2,-5} wake={3,-5} next={4}  last={5} result={6}" -f `
            $_.TaskName, $_.State, $_.Settings.StartWhenAvailable, $_.Settings.WakeToRun, $i.NextRunTime, $i.LastRunTime, $i.LastTaskResult)
    }
}
Set-Content $Out "Soccer Model schedule check"
Report "BEFORE"
Get-ScheduledTask | Where-Object { $_.TaskName -like 'Soccer Model*' } | ForEach-Object {
    $t = $_
    try {
        $t.Settings.StartWhenAvailable = $true
        $t.Settings.WakeToRun = $true
        $t.Settings.DisallowStartIfOnBatteries = $false
        $t.Settings.StopIfGoingOnBatteries = $false
        Set-ScheduledTask -InputObject $t -ErrorAction Stop | Out-Null
    } catch { Add-Content $Out "FAILED to update $($t.TaskName): $_" }
}
Report "AFTER"
Get-Content $Out
