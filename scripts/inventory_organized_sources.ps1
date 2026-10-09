param(
    [string]$SourceRoot = 'D:\英语资料（已整理）',
    [string]$OutputPath = 'E:\自媒体\video-making\local-data\organized-pdfs\source-manifest.json'
)

$ErrorActionPreference = 'Stop'

function Get-SourceFingerprint {
    param([string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-', '').ToLowerInvariant()
    } finally { $stream.Dispose(); $hasher.Dispose() }
}

if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) {
    throw "Source directory not found: $SourceRoot"
}

$pathSeparators = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
$resolvedRoot = (Resolve-Path -LiteralPath $SourceRoot).Path.TrimEnd($pathSeparators)
$resolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$pathComparison = if ([IO.Path]::DirectorySeparatorChar -eq '\') { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
$sourcePrefix = $resolvedRoot + [IO.Path]::DirectorySeparatorChar
if ($resolvedOutputPath.Equals($resolvedRoot, $pathComparison) -or
    $resolvedOutputPath.StartsWith($sourcePrefix, $pathComparison)) {
    throw 'Inventory output must be outside the supplied source directory'
}
$existingManifest = $null
if (Test-Path -LiteralPath $resolvedOutputPath -PathType Leaf) {
    $existingManifest = Get-Content -LiteralPath $resolvedOutputPath -Raw -Encoding UTF8 | ConvertFrom-Json
}
$outputDirectory = Split-Path -Parent $resolvedOutputPath
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$items = @(
    Get-ChildItem -LiteralPath $resolvedRoot -File -Recurse -Force | ForEach-Object {
        $file = $_
        $relativePath = $file.FullName.Substring($resolvedRoot.Length).TrimStart($pathSeparators)
        $title = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)

        $claimsAnswers = $title -match '(解析|答案|参考答案|答题卡|answer|solution)'
        $claimsQuestions = $title -match '(空白卷|试题|真题|题目|questions?|exam|paper)'
        if ($claimsAnswers -and $claimsQuestions) {
            $filenameClaim = 'mixed'
        } elseif ($claimsAnswers) {
            $filenameClaim = 'answers_only'
        } elseif ($claimsQuestions) {
            $filenameClaim = 'questions_only'
        } else {
            $filenameClaim = 'unknown'
        }

        $yearMatch = [regex]::Match($title, '(?:19|20)\d{2}')
        $claimedYear = if ($yearMatch.Success) { $yearMatch.Value } else { 'unknown' }

        $volumeMatch = [regex]::Match($title, '(全国\s*[ⅠⅡⅢIVX一二三四五六七八九]+\s*卷|新课标\s*[ⅠⅡⅢIVX一二三四五六七八九]*\s*卷|[一二三四五六七八九十]+模|[春秋]季卷)')
        $claimedVolume = if ($volumeMatch.Success) { $volumeMatch.Value } else { $null }

        [pscustomobject]@{
            relative_path = $relativePath
            extension = $file.Extension.ToLowerInvariant()
            bytes = [long]$file.Length
            sha256 = Get-SourceFingerprint $file.FullName
            filename_claim = $filenameClaim
            claimed_year = $claimedYear
            claimed_volume = $claimedVolume
            source_authenticity = 'unverified'
            content_exposure = 'not_read'
        }
    }
)

$duplicateGroups = @(
    $items | Group-Object -Property sha256 | Where-Object Count -gt 1 | ForEach-Object {
        [pscustomobject]@{
            sha256 = $_.Name
            count = $_.Count
            relative_paths = @($_.Group | ForEach-Object relative_path | Sort-Object)
        }
    }
)
$duplicateFileCount = 0
if ($duplicateGroups.Count -gt 0) {
    $duplicateFileCount = ($duplicateGroups | Measure-Object -Property count -Sum).Sum
}

function Get-CountMap {
    param([object[]]$Rows, [string]$Property)
    $map = [ordered]@{}
    foreach ($group in ($Rows | Group-Object -Property $Property | Sort-Object Name)) {
        $map[$group.Name] = $group.Count
    }
    return $map
}

$manifest = [ordered]@{
    schema_version = 1
    source_root = $resolvedRoot
    generated_at_utc = if ($null -ne $existingManifest) { $existingManifest.generated_at_utc } else { [DateTime]::UtcNow.ToString('o') }
    scope_note = 'Filename, file size, and SHA256 only. File contents were not read or classified.'
    totals = [ordered]@{
        file_count = $items.Count
        unique_sha256_count = @($items.sha256 | Sort-Object -Unique).Count
        duplicate_hash_group_count = $duplicateGroups.Count
        duplicate_file_count = $duplicateFileCount
    }
    counts = [ordered]@{
        by_extension = Get-CountMap -Rows $items -Property extension
        by_filename_claim = Get-CountMap -Rows $items -Property filename_claim
        by_claimed_year = Get-CountMap -Rows $items -Property claimed_year
    }
    duplicate_hash_groups = $duplicateGroups
    files = $items
}

$json = $manifest | ConvertTo-Json -Depth 8
if ($null -ne $existingManifest) {
    $existingJson = $existingManifest | ConvertTo-Json -Depth 8
    if ($existingJson -cne $json) {
        throw 'Frozen inventory differs; choose a new output path for a new source intake'
    }
} else {
    [System.IO.File]::WriteAllText($resolvedOutputPath, $json, [System.Text.UTF8Encoding]::new($false))
}
Write-Output "Verified immutable manifest: $resolvedOutputPath"
Write-Output "Files: $($manifest.totals.file_count); unique SHA256: $($manifest.totals.unique_sha256_count); duplicate hash groups: $($manifest.totals.duplicate_hash_group_count)"
