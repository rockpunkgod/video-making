<# Install the pinned upstream server and register its stdio transport.
   Run from the repository root. Media and machine configuration stay local.
   This does not change Premiere preferences, installed presets, or global TEMP ACLs.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PremiereExe,
    [string]$CodexConfig,
    [switch]$Launch
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$exePath = (Resolve-Path -LiteralPath $PremiereExe).Path
if (-not $CodexConfig) {
    $codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
    $CodexConfig = Join-Path $codexRoot 'config.toml'
}
$runtime = Join-Path $repoRoot 'local-data\premiere\runtime'
$localConfig = Join-Path $repoRoot 'local-data\premiere\configuration'
$privateRoot = Join-Path $env:USERPROFILE '.premiere-video-os'
$bridge = Join-Path $privateRoot 'bridge'
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$trusted = @($identity.Value, 'S-1-5-18', 'S-1-5-32-544')
foreach ($directory in @($privateRoot, $bridge)) {
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
        $acl = New-Object System.Security.AccessControl.DirectorySecurity
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($sid in $trusted) {
            $principal = New-Object System.Security.Principal.SecurityIdentifier($sid)
            $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                $principal, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
            $acl.AddAccessRule($rule)
        }
        Set-Acl -LiteralPath $directory -AclObject $acl
    }
    $acl = Get-Acl -LiteralPath $directory
    if ((Get-Item -LiteralPath $directory).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Bridge directory must not be a junction or symbolic link: $directory"
    }
    foreach ($rule in $acl.Access) {
        $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        $writeRights = [System.Security.AccessControl.FileSystemRights]'Write,Delete,DeleteSubdirectoriesAndFiles,ChangePermissions,TakeOwnership'
        if ($rule.AccessControlType -eq 'Allow' -and ($rule.FileSystemRights -band $writeRights) -and $sid -notin $trusted) {
            throw "Untrusted write permission in $directory; existing permissions were not changed."
        }
    }
}
New-Item -ItemType Directory -Path $runtime, $localConfig -Force | Out-Null
& npm install --prefix $runtime --no-audit --no-fund 'premiere-pro-mcp@1.19.1'
if ($LASTEXITCODE) { throw 'Upstream package installation failed' }
$entry = Join-Path $runtime 'node_modules\premiere-pro-mcp\dist\index.js'
& node $entry --install-cep
if ($LASTEXITCODE) { throw 'Official CEP installation failed' }
& codex mcp add premiere-pro --env "PREMIERE_TEMP_DIR=$bridge" --env 'PREMIERE_TIMEOUT_MS=120000' --env 'MCP_PROTOCOL_MODE=legacy' -- node $entry
if ($LASTEXITCODE) { throw 'Codex MCP registration failed' }
Push-Location $repoRoot
try {
    & python -m premiere_production.configuration $CodexConfig --backup (Join-Path $localConfig 'codex-config-before.toml')
    if ($LASTEXITCODE) { throw 'Codex configuration failed' }
} finally { Pop-Location }
$shortcutPath = Join-Path $localConfig 'Premiere Video OS.lnk'
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = Split-Path -Parent $exePath
$shortcut.Save()
Write-Output "In Premiere: Window > Extensions > MCP for Adobe Premiere Pro. Set Bridge directory to $bridge, Save, then Start."
Write-Output 'Reload the Codex chat to load newly registered MCP tools. Run verify_premiere_connection before editing.'
if ($Launch) {
    Start-Process explorer.exe -ArgumentList ('"' + $shortcutPath + '"') -WindowStyle Hidden
}
