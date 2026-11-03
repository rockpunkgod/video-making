<#
.SYNOPSIS
  EP01 V3 one-command Windows export of the 4K natural-Foley mix.
.DESCRIPTION
  Searches for the original pre-V2 MP4 in common local folders.
  Keeps the video stream untouched and mixes licensed Kenney CC0 Foley.
  Needs Python 3.10+ and ffmpeg/ffprobe on PATH.
  Optional -Preview720 makes a small phone-friendly copy AFTER the 4K master.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\ep01_v3_run_windows.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\ep01_v3_run_windows.ps1 -Original "D:\Video\EP01.mp4" -Preview720
#>
param(
    [string] $Original = "",
    [string] $OutputDir = "",
    [string] $CueSheet = "",
    [string] $FoleyZip = "",
    [switch] $Preview720
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script = Join-Path $PSScriptRoot "ep01_v3_soft_audio.py"
$name = "英语有画说_EP01_首发候选_4K24.mp4"
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw "V3 audio script is missing: $script"
}
$python = if (Get-Command python -ErrorAction SilentlyContinue) {
    "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    "py"
} else {
    throw "Python is not installed. Install Python 3.10+ and retry."
}
foreach ($executable in @("ffmpeg", "ffprobe")) {
    if (-not (Get-Command $executable -ErrorAction SilentlyContinue)) {
        throw "Missing $executable. Install FFmpeg and add its bin directory to PATH."
    }
}
if ([string]::IsNullOrWhiteSpace($Original)) {
    $possible = @(
        (Join-Path (Get-Location).Path $name),
        (Join-Path $repo $name),
        (Join-Path (Join-Path $repo "local-data") $name),
        (Join-Path (Join-Path $env:USERPROFILE "Downloads") $name),
        (Join-Path (Join-Path $env:USERPROFILE "Videos") $name)
    )
    $found = $possible | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ($null -eq $found) {
        throw "Original 4K file not found. Download '$name' from your ChatGPT Library, put it in Downloads, and re-run this script. The V2 MP4 must NOT be used."
    }
    $Original = $found
}
if (-not (Test-Path -LiteralPath $Original -PathType Leaf)) {
    throw "Original MP4 was not found: $Original"
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path (Join-Path $env:USERPROFILE "Videos") "EP01_V3"
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$out = Join-Path $OutputDir "英语有画说_EP01_V3_自然拟物_4K24.mp4"
if (Test-Path -LiteralPath $out) {
    throw "Output already exists: $out. Rename/move it first to avoid accidental overwrites."
}

$argsList = @($script, "--original", $Original, "--out", $out)
if (-not [string]::IsNullOrWhiteSpace($CueSheet)) { $argsList += @("--cues", $CueSheet) }
if (-not [string]::IsNullOrWhiteSpace($FoleyZip)) { $argsList += @("--foley-zip", $FoleyZip) }
Write-Host "Starting 4K V3: unaltered video + original base soundtrack + natural recorded Foley."
Write-Host "Input: $Original"
Write-Host "Output: $out"
& $python @argsList
if ($LASTEXITCODE -ne 0) { throw "V3 encoding failed: exit code $LASTEXITCODE" }

if ($Preview720) {
    $preview = Join-Path $OutputDir "英语有画说_EP01_V3_试听_720p.mp4"
    if (Test-Path -LiteralPath $preview) { throw "Preview already exists: $preview" }
    $ffargs = @("-hide_banner", "-nostdin", "-v", "error", "-n", "-i", $out, "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", $preview)
    & ffmpeg @ffargs
    if ($LASTEXITCODE -ne 0) { throw "4K output exists, but 720p preview failed." }
    Write-Host "720p preview: $preview"
}
Write-Host "4K V3: $out"
Write-Host "Receipt: $([IO.Path]::ChangeExtension($out, '.v3_receipt.json'))"
Write-Warning "The encoded film must be listened to and watched before release. Auto cues are only draft placement."
