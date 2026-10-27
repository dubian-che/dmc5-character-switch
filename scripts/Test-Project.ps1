[CmdletBinding()]
param([string]$Python = 'python', [switch]$SkipTestBuild)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$oldEncoding = $env:PYTHONIOENCODING
$oldUtf8 = $env:PYTHONUTF8
$rows = @()
Push-Location $project
try {
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONUTF8 = '1'
    if (!$SkipTestBuild) { & (Join-Path $PSScriptRoot 'Build-Launcher.ps1') -TestBuild }
    if (!(Test-Path -LiteralPath (Join-Path $project 'dist\DMC5切人启动器\DMC5SwitchLauncher.exe'))) {
        & (Join-Path $PSScriptRoot 'Build-Launcher.ps1')
    }
    $testExe = Join-Path $project 'work\launcher-tests\DMC5SwitchLauncher.exe'
    if (!(Test-Path -LiteralPath $testExe)) { throw 'Build the test launcher first.' }
    foreach ($kind in @('self-test','installer-test')) {
        $name = if ($kind -eq 'self-test') { 'launcher-self-test.json' } else { 'installer-self-test.json' }
        $report = Join-Path $project "work\$name"
        $child = Start-Process -FilePath $testExe -ArgumentList @("--$kind", ('"{0}"' -f $report)) -WindowStyle Hidden -Wait -PassThru
        if ($child.ExitCode -ne 0) { throw "Launcher $kind failed: $($child.ExitCode)" }
        $data = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
        if (!$data.passed) { throw "Launcher $kind did not pass." }
        $rows += [pscustomobject]@{Test="launcher-$kind";Passed=$true}
    }
    $checks = @('work\check_switch_lua.py') + @(Get-ChildItem -LiteralPath (Join-Path $project 'work') -Filter 'test_*.py' -File | Sort-Object Name | ForEach-Object { $_.FullName })
    foreach ($check in $checks) {
        & $Python $check
        if ($LASTEXITCODE -ne 0) { throw "Python check failed: $check" }
        $rows += [pscustomobject]@{Test=(Split-Path $check -Leaf);Passed=$true}
    }
    & (Join-Path $PSScriptRoot 'Verify-Release.ps1')
    if (!$?) { throw 'Release verification failed.' }
    $result = [pscustomobject]@{
        Build='release-47-scripted-movement-guard';Passed=$true
        CreatedUtc=[DateTime]::UtcNow.ToString('o')
        LaunchedGame=$false;ChangedGameInstallation=$false;Checks=$rows
    }
    $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $project 'work\project-test-results.json') -Encoding UTF8
    $result | Select-Object Build,Passed,LaunchedGame,ChangedGameInstallation
} finally {
    Pop-Location
    $env:PYTHONIOENCODING = $oldEncoding
    $env:PYTHONUTF8 = $oldUtf8
}
