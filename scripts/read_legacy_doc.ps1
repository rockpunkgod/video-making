param([Parameter(Mandatory=$true)][string]$InputPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$resolved = (Resolve-Path -LiteralPath $InputPath).Path
function SourceHash([string]$Path) {
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hasher.ComputeHash([System.IO.File]::ReadAllBytes($Path))) }
    finally { $hasher.Dispose() }
}
$before = SourceHash $resolved
$wordReader = $null
$documentReader = $null
$confirmConversion = $false
$readOnly = $true
$addToRecent = $false
$discardChanges = 0
try {
    $wordReader = New-Object -ComObject Word.Application
    $wordReader.Visible = $false
    $wordReader.DisplayAlerts = 0
    $wordReader.AutomationSecurity = 3
    $wordReader.Options.UpdateLinksAtOpen = $false
    $documentReader = $wordReader.Documents.Open([ref]$resolved, [ref]$confirmConversion, [ref]$readOnly, [ref]$addToRecent)
    $text = $documentReader.Content.Text
    $numbered = 0
    foreach ($paragraph in $documentReader.Paragraphs) {
        if ($paragraph.Range.ListFormat.ListType -ne 0) { $numbered++ }
    }
    @{text=$text; automatic_numbered_paragraphs=$numbered; extractor='Word read-only Content.Text'} | ConvertTo-Json -Depth 4 -Compress
} finally {
    if ($null -ne $documentReader) { $documentReader.Close([ref]$discardChanges) }
    if ($null -ne $wordReader) { $wordReader.Quit([ref]$discardChanges) }
    if ((SourceHash $resolved) -ne $before) {
        throw 'Source changed during read-only extraction'
    }
}
