[CmdletBinding()]
param([switch]$VerifyInstalled,
      [string]$GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\Devil May Cry 5')
$ErrorActionPreference = 'Stop'
if ($PSEdition -eq 'Core') {
    $desktopShell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $verifyArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath,'-GameRoot',$GameRoot)
    if ($VerifyInstalled) { $verifyArgs += '-VerifyInstalled' }
    & $desktopShell $verifyArgs
    if ($LASTEXITCODE -ne 0) { throw 'Release verification failed.' }
    return
}
$project = Split-Path $PSScriptRoot -Parent
$folder = Join-Path $project 'dist\DMC5切人启动器'
$expected = @('DMC5SwitchLauncher.exe','使用说明.txt','REFramework-LICENSE.txt')
if (Compare-Object $expected @(Get-ChildItem -LiteralPath $folder | Select-Object -ExpandProperty Name)) {
    throw '正式目录含额外或缺失文件。'
}
$assembly = [Reflection.Assembly]::LoadFile((Join-Path $folder 'DMC5SwitchLauncher.exe'))
$flags = [Reflection.BindingFlags]'NonPublic,Public,Static,Instance'
if ($assembly.GetType('Dmc5SwitchLauncher.InstallerTests') -or
    $assembly.GetType('Dmc5SwitchLauncher.Program').GetMethod('SelfTest',$flags) -or
    $assembly.GetType('Dmc5SwitchLauncher.ModInstaller').GetField('FailAfter',$flags)) {
    throw '正式启动器混入了测试代码。'
}
function ReadResource($owner,$name) {
    $stream = $owner.GetManifestResourceStream($name)
    if (!$stream) { throw "资源缺失：$name" }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','') }
    finally { $stream.Dispose(); $sha.Dispose() }
}
$test = [Reflection.Assembly]::LoadFile((Join-Path $project 'work\launcher-tests\DMC5SwitchLauncher.exe'))
$names = @($assembly.GetManifestResourceNames())
if ($names.Count -ne 17 -or (Compare-Object $names @($test.GetManifestResourceNames()))) { throw '嵌入资源列表不符。' }
foreach ($name in $names) {
    if ((ReadResource $assembly $name) -ne (ReadResource $test $name)) { throw "测试包与正式包内容不同：$name" }
}
$manifest = $null
if ($VerifyInstalled) { $manifest = Get-Content -LiteralPath (Join-Path $GameRoot '.dmc5-character-switch\installed.json') -Raw | ConvertFrom-Json }
$rows = @()
foreach ($name in $names | Where-Object { $_ -like 'payload.*.lua' }) {
    $file = $name.Substring(8)
    $source = Join-Path $project "outputs\DMC5CharacterSwitch\$file"
    $hash = (Get-FileHash -LiteralPath $source).Hash
    if ($hash -ne (ReadResource $assembly $name)) { throw "源码与正式包不同：$file" }
    $contents = Get-Content -LiteralPath $source -Raw
    if ($contents -match 'captureChargeInputs|nero_once|collision_probe|chain_readonly_profile|on_draw_ui|imgui\.|json\.dump_file|os\.clock|profiling|metrics|reload_core|runtime\.run|[A-Za-z]:[/\\]') { throw "混入开发入口：$file" }
    if ($VerifyInstalled) {
        $area = if ($file -eq 'dmc5_live_switch.lua') { 'autorun' } else { 'data' }
        $relative = "reframework/$area/$file"
        $record = @($manifest.Files | Where-Object { $_.Path -eq $relative })
        if ($record.Count -ne 1 -or $record[0].InstalledHash -ne $hash -or
            (Get-FileHash -LiteralPath (Join-Path $GameRoot $relative)).Hash -ne $hash) { throw "安装或归属记录不一致：$file" }
    }
    $rows += [pscustomobject]@{File=$file;Hash=$hash}
}
if ($rows.Count -ne 15) { throw '正式脚本数量不是15。' }
$sourceFiles = @($rows | Select-Object -ExpandProperty File) + 'README.txt'
if (Compare-Object $sourceFiles @(Get-ChildItem -LiteralPath (Join-Path $project 'outputs\DMC5CharacterSwitch') | Select-Object -ExpandProperty Name)) {
    throw '正式脚本目录混入了非发布文件。'
}
$result = [pscustomobject]@{Build='release-47-scripted-movement-guard';Passed=$true;Files=$expected;InstalledVerified=[bool]$VerifyInstalled;TestCodeExcluded=$true;TestAndReleasePayloadsMatch=$true;Modules=$rows}
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $project 'work\performance-release-verification.json') -Encoding UTF8
$result | Select-Object Build,Passed,InstalledVerified,TestCodeExcluded,TestAndReleasePayloadsMatch
