param(
    [Parameter(Mandatory = $true)]
    [string]$Packet,

    [string]$Report,

    [string]$Config
)

$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Runtime = Join-Path $PSScriptRoot "local-code.py"
$ProjectPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $ProjectPython -PathType Leaf) {
    $Python = $ProjectPython
} else {
    $Python = "python.exe"
}

$Arguments = @($Runtime, "--packet", $Packet)
if ($Config) {
    $Arguments += @("--config", $Config)
}
if ($Report) {
    $Arguments += @("--report", $Report)
}

& $Python @Arguments
$WorkerExitCode = $LASTEXITCODE

switch ($WorkerExitCode) {
    0 { Write-Output "__LOCAL_CODER_READY_FOR_REVIEW__" }
    3 { Write-Output "__LOCAL_CODER_BLOCKED__" }
    4 { Write-Output "__LOCAL_CODER_POLICY_VIOLATION__" }
    130 { Write-Output "__LOCAL_CODER_INTERRUPTED__" }
    default { Write-Output "__LOCAL_CODER_FAILED__ exit_code=$WorkerExitCode" }
}

exit $WorkerExitCode
