<#
.SYNOPSIS
  EP01 V3 clean-audio 4K exporter for Windows PowerShell 5.1+.
.DESCRIPTION
  ASCII-only source to prevent Windows PowerShell 5.1 UTF-8 mojibake.
  Strict default: V2 video only + independent voice stem + optional music + Kenney Foley.
  Original premixed MP4 is UNSAFE and only allowed as an explicitly marked draft.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\ep01_v3_run_windows.ps1 -CleanVoice "D:\EP01_clean_voice.flac" -Music "D:\licensed_music.flac" -Preview720
#>
param(
    [string] $Picture = "",
    [string] $CleanVoice = "",
    [string] $Music = "",
    [string] $Original = "",
    [switch] $DraftUseOriginalAudio,
    [string] $OutputDir = "",
    [string] $CueSheet = "",
    [string] $FoleyZip = "",
    [switch] $Preview720
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script = Join-Path $PSScriptRoot "ep01_v3_soft_audio.py"
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw "V3 Python audio script missing: $script"
}

$python = if (Get-Command python -ErrorAction SilentlyContinue) {
    "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    "py"
} else { throw "Python 3.10+ not found." }
foreach ($exe in @("ffmpeg", "ffprobe")) {
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
        throw "Missing $exe. Install FFmpeg and add its bin directory to PATH."
    }
}

if ([string]::IsNullOrWhiteSpace($Picture)) {
    $v2Candidates = @(
        Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE "Downloads") -File -Filter "*.mp4" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "(?i)EP01.*V2.*4K24" } |
        Sort-Object FullName
    )
    if ($v2Candidates.Count -eq 1) { $Picture = $v2Candidates[0].FullName }
    else { throw "Expected exactly one V2 MP4 in Downloads. Pass -Picture FULL_PATH." }
}
if (-not (Test-Path -LiteralPath $Picture -PathType Leaf)) {
    throw "V2 picture MP4 not found: $Picture"
}
if (-not [string]::IsNullOrWhiteSpace($CleanVoice) -and $DraftUseOriginalAudio) {
    throw "Use EITHER -CleanVoice (strict) OR -DraftUseOriginalAudio (unverified), not both."
}
if ([string]::IsNullOrWhiteSpace($CleanVoice) -and -not $DraftUseOriginalAudio) {
    throw "To replace ALL OPUS sound effects, supply independent, full-length voice-only -CleanVoice PATH. A mixed video soundtrack is not clean. For an UNVERIFIED preview only, use -DraftUseOriginalAudio -Original PATH."
}
$draft = $DraftUseOriginalAudio.IsPresent
if ($draft) {
    if ([string]::IsNullOrWhiteSpace($Original)) {
        $possible = @(
            (Join-Path $env:USERPROFILE "Downloads"),
            (Get-Location).Path,
            $repo
        )
        $found = @(
            foreach ($folder in $possible) {
                if (-not (Test-Path -LiteralPath $folder -PathType Container)) { continue }
                Get-ChildItem -LiteralPath $folder -File -Filter "*.mp4" -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match "(?i)EP01.*4K24" -and $_.Name -notmatch "(?i)(V2|V3|preview|soft)" }
            }
        )
        if ($found.Count -ne 1) { throw "Original premixed MP4 not found. Pass -Original FULL_PATH (only for unsafe draft)." }
        $Original = $found[0].FullName
    }
    if (-not (Test-Path -LiteralPath $Original -PathType Leaf)) {
        throw "Draft premixed MP4 not found: $Original"
    }
} elseif (-not (Test-Path -LiteralPath $CleanVoice -PathType Leaf)) {
    throw "Independent clean voice track not found: $CleanVoice"
}

if (-not [string]::IsNullOrWhiteSpace($Music)) {
    if (-not (Test-Path -LiteralPath $Music -PathType Leaf)) {
        throw "Independently licensed music file not found: $Music"
    }
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path (Join-Path $env:USERPROFILE "Videos") "EP01_V3"
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$baseName = if ($draft) { "EP01_V3_DRAFT_unverified_audio" } else { "EP01_V3_clean_source" }
$out = Join-Path $OutputDir ($baseName + "_4K24.mp4")
if (Test-Path -LiteralPath $out) {
    throw "Output already exists: $out. Rename/move old candidate first."
}

$argsList = @($script, "--picture", $Picture, "--out", $out)
if ($draft) {
    $argsList += @("--draft-use-original-audio", "--original", $Original)
    Write-Warning "This is an UNVERIFIED audio preview. Some old OPUS effects may remain!"
} else {
    $argsList += @("--clean-voice", $CleanVoice)
}
if (-not [string]::IsNullOrWhiteSpace($Music)) { $argsList += @("--music", $Music) }
if (-not [string]::IsNullOrWhiteSpace($CueSheet)) { $argsList += @("--cues", $CueSheet) }
if (-not [string]::IsNullOrWhiteSpace($FoleyZip)) { $argsList += @("--foley-zip", $FoleyZip) }
Write-Host "V2 video-only source: $Picture"
Write-Host "4K target: $out"
& $python @argsList
if ($LASTEXITCODE -ne 0) { throw "V3 encoding failed (exit code $LASTEXITCODE)." }

if ($Preview720) {
    $preview = Join-Path $OutputDir ($baseName + "_preview_720p.mp4")
    if (Test-Path -LiteralPath $preview) { throw "Preview already exists: $preview" }
    & ffmpeg -hide_banner -nostdin -v error -n -i $out -vf "scale=1280:720:flags=lanczos" -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p -c:a copy -movflags +faststart $preview
    if ($LASTEXITCODE -ne 0) { throw "4K completed, 720p preview failed." }
    Write-Host "720p preview: $preview"
}
Write-Host "4K output: $out"
Write-Host "Receipt: $([IO.Path]::ChangeExtension($out, '.v3_receipt.json'))"
Write-Warning "Actual film/audio rights and full listening/sync check are still required for release."
