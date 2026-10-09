param(
    [string]$ManifestPath = '',
    [string]$SourceSha = '',
    [string]$OutputRoot = ''
)

$ErrorActionPreference = 'Stop'
if (-not $ManifestPath) { $ManifestPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'local-data\organized-pdfs\source-manifest.json' }
[void][Reflection.Assembly]::LoadWithPartialName('System.Runtime.WindowsRuntime')
[void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
[void][Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
[void][Windows.Storage.FileAccessMode, Windows.Storage, ContentType = WindowsRuntime]
[void][Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
[void][Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime]

function Wait-WinRt {
    param($Operation, [Type]$ResultType)
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and
                       $_.GetParameters().Count -eq 1 -and
                       $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } |
        Select-Object -First 1
    if ($null -eq $method) { throw 'Windows Runtime AsTask adapter unavailable' }
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    return $task.GetAwaiter().GetResult()
}

function Get-Hash {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-TextHash {
    param([string]$Text)
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
        return ([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally { $hasher.Dispose() }
}

function Get-Box {
    param($Rectangle)
    return [ordered]@{
        x = [double]$Rectangle.X
        y = [double]$Rectangle.Y
        width = [double]$Rectangle.Width
        height = [double]$Rectangle.Height
    }
}

function Read-PngOcr {
    param([string]$Path, $Engine)
    $file = Wait-WinRt ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Path)) ([Windows.Storage.StorageFile])
    $stream = Wait-WinRt ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    try {
        $decoder = Wait-WinRt ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Wait-WinRt ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        try {
            $result = Wait-WinRt ($Engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            $lines = @(
                foreach ($line in $result.Lines) {
                    $words = @(
                        foreach ($word in $line.Words) {
                            [ordered]@{ text = [string]$word.Text; box = Get-Box $word.BoundingRect }
                        }
                    )
                    $box = $null
                    if ($words.Count -gt 0) {
                        $left = ($words | ForEach-Object { $_.box.x } | Measure-Object -Minimum).Minimum
                        $top = ($words | ForEach-Object { $_.box.y } | Measure-Object -Minimum).Minimum
                        $right = ($words | ForEach-Object { $_.box.x + $_.box.width } | Measure-Object -Maximum).Maximum
                        $bottom = ($words | ForEach-Object { $_.box.y + $_.box.height } | Measure-Object -Maximum).Maximum
                        $box = [ordered]@{ x = $left; y = $top; width = $right - $left; height = $bottom - $top }
                    }
                    [ordered]@{ text = [string]$line.Text; box = $box; words = $words }
                }
            )
            return [ordered]@{
                text = [string]$result.Text
                text_sha256 = $null
                lines = $lines
                image_width = [int]$bitmap.PixelWidth
                image_height = [int]$bitmap.PixelHeight
            }
        } finally { if ($null -ne $bitmap) { $bitmap.Dispose() } }
    } finally { if ($null -ne $stream) { $stream.Dispose() } }
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$sourceRoot = (Resolve-Path -LiteralPath $manifest.source_root).Path
$localRoot = Split-Path -Parent (Resolve-Path -LiteralPath $ManifestPath).Path
if (-not $OutputRoot) { $OutputRoot = Join-Path $localRoot 'ocr' }
$resolvedOutputRoot = [IO.Path]::GetFullPath($OutputRoot)
if ($resolvedOutputRoot.Equals($sourceRoot, [StringComparison]::OrdinalIgnoreCase) -or
    $resolvedOutputRoot.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'OCR output must be outside source directory'
}
$pdftoppm = (Get-Command pdftoppm.exe -ErrorAction Stop).Source
$languages = @([Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages)
if ($languages.Count -eq 0) { throw 'No Windows OCR recognizer language installed' }
$language = $languages | Where-Object LanguageTag -eq 'en-US' | Select-Object -First 1
if ($null -eq $language) { $language = $languages[0] }
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if ($null -eq $engine) { throw "Windows OCR engine unavailable for $($language.LanguageTag)" }

$rows = @($manifest.files | Where-Object {
    $_.extension -eq '.pdf' -and $_.filename_claim -in @('questions_only', 'unknown') -and
    [IO.Path]::GetFileNameWithoutExtension($_.relative_path) -notmatch '(答案|解析|参考答案|答题卡|answer|solution)'
})
$byHash = @{}
foreach ($row in $rows) { $byHash[$row.sha256.ToLowerInvariant()] = $row }
$results = @()
foreach ($frozenFile in (Get-ChildItem -LiteralPath (Join-Path $localRoot 'pages') -File -Filter '*.json' | Sort-Object Name)) {
    $sha = $frozenFile.BaseName.ToLowerInvariant()
    if ($SourceSha -and $sha -ne $SourceSha.ToLowerInvariant()) { continue }
    if (-not $byHash.ContainsKey($sha)) { continue }
    $frozen = Get-Content -LiteralPath $frozenFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $pending = @($frozen.pages | Where-Object requires_ocr)
    if ($pending.Count -eq 0) { continue }
    if ($frozen.source_sha256 -ne $sha) { throw "Frozen source SHA mismatch: $sha" }
    $row = $byHash[$sha]
    $source = [IO.Path]::GetFullPath((Join-Path $sourceRoot $row.relative_path))
    if (-not $source.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe source path: $($row.relative_path)"
    }
    if ((Get-Hash $source) -ne $sha) { throw "Source changed before OCR: $($row.relative_path)" }
    $scratch = Join-Path ([IO.Path]::GetTempPath()) ('organized-pdf-ocr-' + [guid]::NewGuid().ToString('N'))
    [void](New-Item -ItemType Directory -Path $scratch)
    try {
        $pages = @(
            foreach ($page in $pending) {
                $number = [int]$page.page_number
                $prefix = Join-Path $scratch ('page-' + $number)
                & $pdftoppm -f $number -l $number -r 150 -png -singlefile $source $prefix
                if ($LASTEXITCODE -ne 0) { throw "PDF render failed for $sha page $number" }
                $png = $prefix + '.png'
                $renderSha = Get-Hash $png
                $ocr = Read-PngOcr $png $engine
                $ocr.text_sha256 = Get-TextHash $ocr.text
                [ordered]@{
                    page_number = $number
                    render_sha256 = $renderSha
                    render_dpi = 150
                    image_width = $ocr.image_width
                    image_height = $ocr.image_height
                    text = $ocr.text
                    text_sha256 = $ocr.text_sha256
                    lines = $ocr.lines
                    status = 'transcription_pending_visual_review'
                }
            }
        )
        if ((Get-Hash $source) -ne $sha) { throw "Source changed during OCR: $($row.relative_path)" }
        $record = [ordered]@{
            version = 1
            source_sha256 = $sha
            source_paths = @($frozen.source_paths)
            engine = 'Windows.Media.Ocr'
            language = [string]$language.LanguageTag
            status = 'transcription_pending_visual_review'
            pages = $pages
        }
        $target = Join-Path $resolvedOutputRoot ($sha + '.json')
        $json = ConvertTo-Json -InputObject $record -Depth 30
        if (Test-Path -LiteralPath $target) {
            if ((Get-Content -LiteralPath $target -Raw -Encoding UTF8) -ne $json) {
                throw "Frozen OCR artifact differs: $target"
            }
        } else {
            [void](New-Item -ItemType Directory -Path $resolvedOutputRoot -Force)
            [IO.File]::WriteAllText($target, $json, [Text.UTF8Encoding]::new($false))
        }
        $results += [ordered]@{ source_sha256 = $sha; page_count = $pages.Count; output = $target }
    } finally {
        $resolvedScratch = [IO.Path]::GetFullPath($scratch)
        if ($resolvedScratch.StartsWith([IO.Path]::GetTempPath(), [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedScratch -Recurse -Force
        }
    }
}
ConvertTo-Json -InputObject ([ordered]@{ language = $language.LanguageTag; sources = $results.Count;
    pages = (@($results | ForEach-Object page_count | Measure-Object -Sum)[0].Sum); results = $results }) -Depth 5
