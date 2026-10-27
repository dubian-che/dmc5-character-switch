[CmdletBinding()]
param(
    [string]$GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Devil May Cry 5',
    [Parameter(Mandatory=$true)][string]$LauncherExe
)
$ErrorActionPreference = 'Stop'
# The launcher targets .NET Framework; PowerShell 7's System.Web shim cannot
# deserialize its ownership manifest. Use Windows PowerShell's native CLR.
if ($PSEdition -eq 'Core') {
    $desktopShell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    & $desktopShell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -GameRoot $GameRoot -LauncherExe $LauncherExe
    if ($LASTEXITCODE -ne 0) { throw 'Managed Mod installation failed.' }
    return
}
$exePath = (Resolve-Path -LiteralPath $LauncherExe).Path
[Reflection.Assembly]::LoadFile($exePath) | Out-Null
$installer = New-Object Dmc5SwitchLauncher.ModInstaller -ArgumentList $GameRoot, $null
$installer.Run($true)
