param(
    [Parameter(Mandatory = $true)]
    [string]$Packet,

    [string]$Config,

    [string]$CoderReport,

    [string]$ReviewReport
)

$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Runtime = Join-Path $PSScriptRoot "local-unit.py"
$ProjectPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $ProjectPython -PathType Leaf) {
    $Python = $ProjectPython
} else {
    $Python = "python.exe"
}
$Arguments = @($Runtime, "--packet", $Packet)
if ($Config) { $Arguments += @("--config", $Config) }
if ($CoderReport) { $Arguments += @("--coder-report", $CoderReport) }
if ($ReviewReport) { $Arguments += @("--review-report", $ReviewReport) }
& $Python @Arguments
exit $LASTEXITCODE
