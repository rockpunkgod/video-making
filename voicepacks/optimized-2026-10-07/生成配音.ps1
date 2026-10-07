$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$workspaceRoot = Split-Path -Parent $projectRoot
$voicePython = $env:VOICE_PYTHON
if (-not $voicePython) { $voicePython = Join-Path $workspaceRoot 'voice-training\env\Scripts\python.exe' }
$voiceRuntime = $env:GPT_SOVITS_HOME
if (-not $voiceRuntime) { $voiceRuntime = Join-Path $workspaceRoot 'GPT-SoVITS' }
$voiceOutput = Join-Path $projectRoot ('local-data\voice-output\' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
& $voicePython (Join-Path $projectRoot 'voicepacks\tools\generate_gpt_sovits.py') --pack $PSScriptRoot --runtime $voiceRuntime --text-file (Join-Path $PSScriptRoot '文案.txt') --output $voiceOutput
if ($LASTEXITCODE -ne 0) { throw '生成未完成，请查看上方提示。' }
Write-Host "配音已保存：$voiceOutput"
