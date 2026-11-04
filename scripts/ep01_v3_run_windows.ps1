<#
.SYNOPSIS
  Export EP01 V3 4K with genuine CC0 Foley. Windows PowerShell 5.1+.
.DESCRIPTION
  ASCII-only source: PowerShell 5.1 corrupts Chinese in BOM-less UTF-8 .ps1.
  The original pre-V2 film is required; never use V2 for this operation.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\scripts\ep01_v3_run_windows.ps1 -Original "C:\Users\ASUS\Downloads\EP01_original_4K24.mp4" -Preview720
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
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw "V3 audio script not found: $script"
}

$python = if (Get-Command python -ErrorAction SilentlyContinue) {
    "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    "py"
} else { throw "Python not found; install Python 3.10+." }

foreach ($exe in @("ffmpeg", "ffprobe")) {
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
        throw "Missing $exe; install FFmpeg and add its bin directory to PATH."
    }
}

if ([string]::IsNullOrWhiteSpace($Original)) {
    $paths = @(
        (Get-Location).Path,
        $repo,
        (Join-Path $repo "local-data"),
        (Join-Path $env:USERPROFILE "Downloads"),
        (Join-Path $env:USERPROFILE "Videos")
    )
    $candidates = @(
        foreach ($folder in $paths) {
            if (-not (Test-Path -LiteralPath $folder -PathType Container)) { continue }
            Get-ChildItem -LiteralPath $folder -File -Filter "*.mp4" -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.Name -match "(?i)EP01" -and
                    $_.Name -match "(?i)4K24" -and
                    $_.Name -notmatch "(?i)(V2|V3|preview|mix|soft)" -and
                    $_.Length -gt 100MB
                }
        }
    )
    $candidates = @($candidates | Sort-Object -Property FullName -Unique)
    if ($candidates.Count -ne 1) {
        Write-Host "Candidate MP4s in Downloads (top level only):"
        Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE "Downloads") -File -Filter "*.mp4" -ErrorAction SilentlyContinue |
            Select-Object Name,Length,FullName | Format-Table -AutoSize
        throw "Expected ONE original EP01 4K24 MP4, found $($candidates.Count). Download the original, not V2, or pass -Original FULL_PATH."
    }
    $Original = $candidates[0].FullName
}
if (-not (Test-Path -LiteralPath $Original -PathType Leaf)) {
    throw "Original 4K file not found: $Original"
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path (Join-Path $env:USERPROFILE "Videos") "EP01_V3"
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$out = Join-Path $OutputDir "EP01_V3_natural_4K24.mp4"
if (Test-Path -LiteralPath $out) {
    throw "Output already exists: $out. Rename or move it to preserve the existing file."
}

$argsList = @($script, "--original", $Original, "--out", $out)
if (-not [string]::IsNullOrWhiteSpace($CueSheet)) { $argsList += @("--cues", $CueSheet) }
if (-not [string]::IsNullOrWhiteSpace($FoleyZip)) { $argsList += @("--foley-zip", $FoleyZip) }
Write-Host "Input original: $Original"
Write-Host "Output 4K: $out"
& $python @argsList
if ($LASTEXITCODE -ne 0) { throw "V3 encode failed (exit code $LASTEXITCODE)." }

if ($Preview720) {
    $preview = Join-Path $OutputDir "EP01_V3_preview_720p.mp4"
    if (Test-Path -LiteralPath $preview) { throw "Preview already exists: $preview" }
    $ffargs = @(
        "-hide_banner","-nostdin","-v","error","-n","-i",$out,
        "-vf","scale=1280:720:flags=lanczos","-c:v","libx264",
        "-preset","fast","-crf","22","-pix_fmt","yuv420p",
        "-c:a","copy","-movflags","+faststart",$preview
    )
    & ffmpeg @ffargs
    if ($LASTEXITCODE -ne 0) { throw "4K was encoded, but the 720p preview failed." }
    Write-Host "720p preview: $preview"
}
Write-Host "4K output: $out"
Write-Host "Receipt: $([IO.Path]::ChangeExtension($out, '.v3_receipt.json'))"
Write-Warning "Automatic scene-change cues are a draft. Listen and verify before publishing."
