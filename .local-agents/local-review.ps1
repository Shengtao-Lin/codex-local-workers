param(
    [Parameter(Mandatory = $true)]
    [string]$Request,

    [string]$Report,

    [string]$Config
)

$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Runtime = Join-Path $PSScriptRoot "local-review.py"
$ProjectPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $ProjectPython -PathType Leaf) {
    $Python = $ProjectPython
} else {
    $Python = "python.exe"
}

$Arguments = @($Runtime, "--request", $Request)
if ($Config) {
    $Arguments += @("--config", $Config)
}
if ($Report) {
    $Arguments += @("--report", $Report)
}

& $Python @Arguments
$ReviewerExitCode = $LASTEXITCODE

if ($ReviewerExitCode -eq 0) {
    Write-Output "__LOCAL_REVIEW_COMPLETE__"
} else {
    Write-Output "__LOCAL_REVIEW_FAILED__ exit_code=$ReviewerExitCode"
}

exit $ReviewerExitCode
