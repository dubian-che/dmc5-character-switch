[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$GameRoot, [switch]$Rollback)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$artifact = Join-Path $project 'work\reframework-window-fix'
$info = Get-Content -LiteralPath (Join-Path $artifact 'runtime-artifact.json') -Raw | ConvertFrom-Json
$GameRoot = (Resolve-Path -LiteralPath $GameRoot).Path
if (!(Test-Path -LiteralPath (Join-Path $GameRoot 'DevilMayCry5.exe'))) { throw 'Not a DMC5 game directory.' }
function RequireClosed {
    if (Get-Process DevilMayCry5 -ErrorAction SilentlyContinue) { throw 'Exit DMC5 before changing the loader.' }
}
function Hash([string]$path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
function WriteJson([string]$path, $value) {
    [IO.File]::WriteAllText($path, ($value | ConvertTo-Json -Depth 50), [Text.UTF8Encoding]::new($false))
}
RequireClosed
$store = Join-Path $GameRoot '.dmc5-character-switch'
$manifest = Join-Path $store 'installed.json'
if (!(Test-Path -LiteralPath $manifest)) { throw 'Install the party Mod first.' }
$lease = [IO.File]::Open((Join-Path $store 'operation.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
$staged = $null; $stagedManifest = $null
try {
    $dll = Join-Path $GameRoot 'dinput8.dll'
    $state = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
    $owned = @($state.Files | Where-Object Path -eq 'dinput8.dll')
    if ($owned.Count -gt 1) { throw 'Ambiguous runtime ownership record.' }
    $fixed = Join-Path $artifact 'dinput8.dll'
    if ((Hash $fixed) -ne $info.FixedHash) { throw 'Fixed runtime artifact hash mismatch.' }
    $expected = if ($Rollback) { $info.FixedHash } else { $info.PriorHash }
    $desired = if ($Rollback) { $info.PriorHash } else { $info.FixedHash }
    $current = Hash $dll
    if ($owned.Count -eq 1 -and $owned[0].InstalledHash -ne $current) { throw 'Runtime ownership hash mismatch.' }
    if ($current -eq $desired) { Write-Output 'Runtime already matches requested version.'; return }
    if ($current -ne $expected) { throw 'Unknown loader: refusing to replace it.' }
    $fixStore = Join-Path $store 'window-hook-fix'
    $reportPath = Join-Path $fixStore 'installed.json'
    $source = $fixed
    if ($Rollback) {
        $previous = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
        $source = $previous.BackupDll
        if ((Hash $source) -ne $desired) { throw 'Original runtime backup hash mismatch.' }
    }
    $operation = Join-Path $fixStore ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $operation -Force | Out-Null
    $backupDll = Join-Path $operation 'dinput8.dll.backup'
    $backupManifest = Join-Path $operation 'installed.json.backup'
    Copy-Item -LiteralPath $dll -Destination $backupDll
    Copy-Item -LiteralPath $manifest -Destination $backupManifest
    if ((Hash $backupDll) -ne $expected) { throw 'Runtime backup verification failed.' }
    $token = [guid]::NewGuid().ToString('N')
    $staged = Join-Path $GameRoot ('dinput8.dll.' + $token + '.staged')
    $stagedManifest = Join-Path $store ('installed.' + $token + '.staged')
    Copy-Item -LiteralPath $source -Destination $staged
    if ((Hash $staged) -ne $desired) { throw 'Staged runtime verification failed.' }
    if ($owned.Count -eq 1) { $owned[0].InstalledHash = $desired }
    WriteJson $stagedManifest $state
    RequireClosed
    try {
        [IO.File]::Replace($staged, $dll, [NullString]::Value)
        [IO.File]::Replace($stagedManifest, $manifest, [NullString]::Value)
        if ((Hash $dll) -ne $desired) { throw 'Installed runtime verification failed.' }
        $report = [pscustomobject]@{
            Build=$info.Build; Installed=(!$Rollback); RolledBack=[bool]$Rollback
            FixedHash=$info.FixedHash; PriorHash=$info.PriorHash
            BackupDll=($backupDll); Operation=$operation
            CreatedUtc=[DateTime]::UtcNow.ToString('o'); RuntimeVerified=$false
        }
        if ($Rollback) { $report.BackupDll = $previous.BackupDll }
        WriteJson $reportPath $report
    } catch {
        Copy-Item -LiteralPath $backupDll -Destination $staged -Force
        [IO.File]::Replace($staged, $dll, [NullString]::Value)
        Copy-Item -LiteralPath $backupManifest -Destination $stagedManifest -Force
        [IO.File]::Replace($stagedManifest, $manifest, [NullString]::Value)
        throw
    }
    $report | Select-Object Build,Installed,RolledBack,BackupDll
} finally {
    foreach ($path in @($staged,$stagedManifest)) {
        if ($path -and (Test-Path -LiteralPath $path)) { Remove-Item -LiteralPath $path }
    }
    $lease.Dispose()
}
