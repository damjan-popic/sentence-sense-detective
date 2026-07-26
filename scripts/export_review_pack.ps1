param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$runtimeRoot = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies'
$node = Join-Path $runtimeRoot 'node\bin\node.exe'
$nodeModules = Join-Path $runtimeRoot 'node\node_modules'
if (-not (Test-Path -LiteralPath $node) -or -not (Test-Path -LiteralPath $nodeModules)) {
    throw 'The bundled spreadsheet runtime is unavailable.'
}

$work = Join-Path $env:TEMP ('sentence-sense-detective-artifact-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
New-Item -ItemType Junction -Path (Join-Path $work 'node_modules') -Target $nodeModules | Out-Null
Copy-Item -LiteralPath (Join-Path $RepoRoot 'scripts\export_review_pack.mjs') -Destination (Join-Path $work 'export_review_pack.mjs')

$env:SSD_ROOT = $RepoRoot
& $node (Join-Path $work 'export_review_pack.mjs')
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
