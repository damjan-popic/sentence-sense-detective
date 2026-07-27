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

$partRoot = Join-Path $RepoRoot 'external\review\workbook-parts'
$resolvedReviewRoot = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot 'external\review'))
$resolvedPartRoot = [System.IO.Path]::GetFullPath($partRoot)
if (-not $resolvedPartRoot.StartsWith($resolvedReviewRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    throw 'The workbook-parts directory resolved outside external/review.'
}
if ($env:SSD_REUSE_WORKBOOK_PARTS -ne '1') {
    if (Test-Path -LiteralPath $resolvedPartRoot) {
        Remove-Item -LiteralPath $resolvedPartRoot -Recurse -Force
    }
    $env:SSD_ROOT = $RepoRoot
    & $node '--max-old-space-size=12288' '--expose-gc' (Join-Path $work 'export_review_pack.mjs')
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Copy-ZipEntry {
    param(
        [System.IO.Compression.ZipArchive]$Archive,
        [string]$EntryName,
        [string]$Destination
    )
    $entry = $Archive.GetEntry($EntryName)
    if ($null -eq $entry) {
        throw "Missing XLSX package entry: $EntryName"
    }
    $destinationDirectory = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $destinationDirectory)) {
        New-Item -ItemType Directory -Path $destinationDirectory | Out-Null
    }
    $inputStream = $entry.Open()
    $outputStream = [System.IO.File]::Create($Destination)
    try {
        $inputStream.CopyTo($outputStream)
    }
    finally {
        $outputStream.Dispose()
        $inputStream.Dispose()
    }
}

function Save-XmlDocument {
    param(
        [System.Xml.XmlDocument]$Document,
        [string]$Path
    )
    $settings = New-Object System.Xml.XmlWriterSettings
    $settings.Encoding = New-Object System.Text.UTF8Encoding($false)
    $settings.Indent = $false
    $writer = [System.Xml.XmlWriter]::Create($Path, $settings)
    try {
        $Document.Save($writer)
    }
    finally {
        $writer.Dispose()
    }
}

$parts = @(Get-ChildItem -LiteralPath $resolvedPartRoot -Filter 'review-pack-part-*.xlsx' | Sort-Object Name)
if ($parts.Count -lt 1) {
    throw 'No authored workbook parts were produced.'
}
$mergeRoot = Join-Path $work 'merged-xlsx'
[System.IO.Compression.ZipFile]::ExtractToDirectory($parts[0].FullName, $mergeRoot)

for ($index = 1; $index -lt $parts.Count; $index += 1) {
    $number = $index + 1
    $archive = [System.IO.Compression.ZipFile]::OpenRead($parts[$index].FullName)
    try {
        Copy-ZipEntry $archive 'xl/worksheets/sheet1.xml' (Join-Path $mergeRoot "xl\worksheets\sheet$number.xml")
        Copy-ZipEntry $archive 'xl/worksheets/_rels/sheet1.xml.rels' (Join-Path $mergeRoot "xl\worksheets\_rels\sheet$number.xml.rels")
        Copy-ZipEntry $archive 'xl/tables/table1.xml' (Join-Path $mergeRoot "xl\tables\table$number.xml")
    }
    finally {
        $archive.Dispose()
    }

    $sheetRelsPath = Join-Path $mergeRoot "xl\worksheets\_rels\sheet$number.xml.rels"
    [xml]$sheetRels = Get-Content -LiteralPath $sheetRelsPath -Raw
    $tableRelationship = $sheetRels.Relationships.Relationship |
        Where-Object { $_.Type -like '*/table' }
    $tableRelationship.Target = "/xl/tables/table$number.xml"
    Save-XmlDocument $sheetRels $sheetRelsPath

    $tablePath = Join-Path $mergeRoot "xl\tables\table$number.xml"
    [xml]$tableDocument = Get-Content -LiteralPath $tablePath -Raw
    $tableDocument.table.id = [string]$number
    Save-XmlDocument $tableDocument $tablePath
}

$workbookPath = Join-Path $mergeRoot 'xl\workbook.xml'
[xml]$workbook = Get-Content -LiteralPath $workbookPath -Raw
$workbookNamespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
$relationshipNamespace = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
$workbookNamespaces = New-Object System.Xml.XmlNamespaceManager($workbook.NameTable)
$workbookNamespaces.AddNamespace('x', $workbookNamespace)
$sheetsNode = $workbook.SelectSingleNode('/x:workbook/x:sheets', $workbookNamespaces)
if ($null -eq $sheetsNode) {
    throw 'The authored workbook has no sheets collection.'
}
$sheetsNode.RemoveAll()
for ($index = 0; $index -lt $parts.Count; $index += 1) {
    $number = $index + 1
    $sheet = $workbook.CreateElement('sheet', $workbookNamespace)
    $sheet.SetAttribute('name', "Review $($number.ToString('00'))")
    $sheet.SetAttribute('sheetId', [string]$number)
    [void]$sheet.SetAttribute('id', $relationshipNamespace, "RReviewSheet$number")
    [void]$sheetsNode.AppendChild($sheet)
}
Save-XmlDocument $workbook $workbookPath

$workbookRelsPath = Join-Path $mergeRoot 'xl\_rels\workbook.xml.rels'
[xml]$workbookRels = Get-Content -LiteralPath $workbookRelsPath -Raw
$packageRelationshipNamespace = 'http://schemas.openxmlformats.org/package/2006/relationships'
$worksheetType = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet'
@($workbookRels.Relationships.Relationship | Where-Object { $_.Type -eq $worksheetType }) |
    ForEach-Object { [void]$workbookRels.Relationships.RemoveChild($_) }
for ($index = 0; $index -lt $parts.Count; $index += 1) {
    $number = $index + 1
    $relationship = $workbookRels.CreateElement('Relationship', $packageRelationshipNamespace)
    $relationship.SetAttribute('Type', $worksheetType)
    $relationship.SetAttribute('Target', "/xl/worksheets/sheet$number.xml")
    $relationship.SetAttribute('Id', "RReviewSheet$number")
    [void]$workbookRels.Relationships.AppendChild($relationship)
}
Save-XmlDocument $workbookRels $workbookRelsPath

$contentTypesPath = Join-Path $mergeRoot '[Content_Types].xml'
[xml]$contentTypes = Get-Content -LiteralPath $contentTypesPath -Raw
$contentTypeNamespace = 'http://schemas.openxmlformats.org/package/2006/content-types'
$worksheetContentType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'
$tableContentType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml'
@(
    $contentTypes.Types.Override |
        Where-Object {
            $_.ContentType -in @($worksheetContentType, $tableContentType)
        }
) | ForEach-Object { [void]$contentTypes.Types.RemoveChild($_) }
for ($index = 0; $index -lt $parts.Count; $index += 1) {
    $number = $index + 1
    $sheetOverride = $contentTypes.CreateElement('Override', $contentTypeNamespace)
    $sheetOverride.SetAttribute('PartName', "/xl/worksheets/sheet$number.xml")
    $sheetOverride.SetAttribute('ContentType', $worksheetContentType)
    [void]$contentTypes.Types.AppendChild($sheetOverride)
    $tableOverride = $contentTypes.CreateElement('Override', $contentTypeNamespace)
    $tableOverride.SetAttribute('PartName', "/xl/tables/table$number.xml")
    $tableOverride.SetAttribute('ContentType', $tableContentType)
    [void]$contentTypes.Types.AppendChild($tableOverride)
}
Save-XmlDocument $contentTypes $contentTypesPath

$fullOutput = Join-Path $RepoRoot 'data\review\review_pack.xlsx'
$fullOutputDirectory = Split-Path -Parent $fullOutput
if (-not (Test-Path -LiteralPath $fullOutputDirectory)) {
    New-Item -ItemType Directory -Path $fullOutputDirectory | Out-Null
}
if (Test-Path -LiteralPath $fullOutput) {
    Remove-Item -LiteralPath $fullOutput -Force
}
$outputArchive = [System.IO.Compression.ZipFile]::Open(
    $fullOutput,
    [System.IO.Compression.ZipArchiveMode]::Create
)
try {
    Get-ChildItem -LiteralPath $mergeRoot -Recurse -File | ForEach-Object {
        $relativeName = $_.FullName.Substring($mergeRoot.Length + 1).Replace('\', '/')
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $outputArchive,
            $_.FullName,
            $relativeName,
            [System.IO.Compression.CompressionLevel]::Optimal
        )
    }
}
finally {
    $outputArchive.Dispose()
}

$outputRoot = Join-Path $RepoRoot 'outputs\20260727-formal-remap-engine'
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
Copy-Item -LiteralPath $fullOutput -Destination (Join-Path $outputRoot 'review_pack.xlsx') -Force
Copy-Item -LiteralPath (Join-Path $RepoRoot 'reports\remap_manual_review_sample.xlsx') -Destination (Join-Path $outputRoot 'remap_manual_review_sample.xlsx') -Force

Write-Output "Assembled $($parts.Count) verified sheets into $fullOutput."
