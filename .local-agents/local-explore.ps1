param(
    [Parameter(Mandatory = $true)]
    [string]$Task,

    [string]$Report
)

$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Runtime = Join-Path $PSScriptRoot "local-explore.py"
$ProjectPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $ProjectPython -PathType Leaf) {
    $Python = $ProjectPython
} else {
    $Python = "python.exe"
}

$Arguments = @($Runtime, "--task", $Task)
if ($Report) {
    $Arguments += @("--report", $Report)
}

& $Python @Arguments
$WorkerExitCode = $LASTEXITCODE

if ($WorkerExitCode -eq 0) {
    Write-Output "__LOCAL_EXPLORER_DONE__"
} elseif ($WorkerExitCode -eq 3) {
    Write-Output "__LOCAL_EXPLORER_BLOCKED__"
} elseif ($WorkerExitCode -eq 130) {
    Write-Output "__LOCAL_EXPLORER_INTERRUPTED__"
} else {
    Write-Output "__LOCAL_EXPLORER_FAILED__ exit_code=$WorkerExitCode"
}

exit $WorkerExitCode
