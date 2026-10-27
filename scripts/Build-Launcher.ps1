[CmdletBinding()]
param([switch]$CreateDesktopShortcut, [switch]$TestBuild, [switch]$DiagnosticBuild, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (!(Test-Path -LiteralPath $compiler)) { throw '未找到 .NET Framework C# 编译器。' }
$outDir = Join-Path $projectRoot $(if ($DiagnosticBuild) { if ($TestBuild) { 'work\support-tests' } else { 'dist\DMC5远端诊断启动器' } } elseif ($TestBuild) { 'work\launcher-tests' } else { 'dist\DMC5切人启动器' })
if ($OutputDirectory) { $outDir = [IO.Path]::GetFullPath($OutputDirectory) }
if (($TestBuild -or $DiagnosticBuild) -and $CreateDesktopShortcut) { throw '测试构建不能创建正式桌面快捷方式。' }
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$exe = Join-Path $outDir 'DMC5SwitchLauncher.exe'
$source = Join-Path $projectRoot 'launcher\Dmc5SwitchLauncher.cs'
$installer = Join-Path $projectRoot 'launcher\ModInstaller.cs'
$tests = Join-Path $projectRoot 'launcher\InstallerTests.cs'
$manifest = Join-Path $projectRoot 'launcher\app.manifest'
$dependencyDir = Join-Path $projectRoot 'launcher\dependencies\REFramework'
$dll = Join-Path $dependencyDir 'dinput8.dll'
if ((Get-FileHash -LiteralPath $dll).Hash -ne 'CBA7C25F57D199E2FDFB73EB3BA8BA5BAF028D453D428498796E85FBDD75CB0F') { throw 'REFramework 文件与固定版本不符。' }
$compressed = Join-Path $outDir 'dinput8.dll.gz'
$inputStream = [IO.File]::OpenRead($dll)
$outputStream = [IO.File]::Create($compressed)
try {
    $zipStream = [IO.Compression.GZipStream]::new($outputStream, [IO.Compression.CompressionMode]::Compress)
    try { $inputStream.CopyTo($zipStream) } finally { $zipStream.Dispose() }
} finally { $inputStream.Dispose(); $outputStream.Dispose() }
$modules = @('dmc5_live_switch.lua','dmc5_party_hud.lua') + (@('core','hud','controller','keys','lifecycle','progression','regen','resources','voice','runtime','loader','input_menu','palace') | ForEach-Object { "dmc5_switch_$_.lua" })
$resources = @("/resource:$compressed,payload.dinput8.dll.gz", "/resource:$(Join-Path $dependencyDir 'LICENSE.txt'),payload.REFramework-LICENSE.txt")
foreach ($name in $modules) {
    $modulePath = Join-Path $projectRoot "outputs\DMC5CharacterSwitch\$name"
    # Keep development UI, samplers and filesystem bridges out of both payloads.
    if ((Get-Content -LiteralPath $modulePath -Raw) -match 'captureChargeInputs|nero_once|collision_probe|chain_readonly_profile|on_draw_ui|imgui\.|json\.dump_file|os\.clock|profiling|metrics|reload_core|runtime\.run|[A-Za-z]:[/\\]') {
        throw "正式脚本含开发入口：$name"
    }
    $resources += "/resource:$modulePath,payload.$name"
}
$sources = @($source, $installer)
$defines = @()
$extraReferences = @()
if ($DiagnosticBuild) {
    $defines += '/define:SUPPORT_DIAGNOSTICS'
    $sources += (Join-Path $projectRoot 'launcher\SupportDiagnostics.cs')
    $resources += "/resource:$(Join-Path $projectRoot 'support\zzz_dmc5_support_recorder.lua'),support.recorder.lua"
    $extraReferences += '/reference:System.IO.Compression.dll'
    $extraReferences += '/reference:System.Web.dll'
    if ($TestBuild) { $sources += (Join-Path $projectRoot 'launcher\SupportTests.cs') }
}
if ($TestBuild) { $sources += $tests; $defines += '/define:MOD_TESTS' }
& $compiler /nologo /target:winexe /platform:anycpu /optimize+ /codepage:65001 /utf8output "/out:$exe" "/win32manifest:$manifest" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll /reference:System.Core.dll $defines $extraReferences $resources $sources
if ($LASTEXITCODE -ne 0) { throw '启动器编译失败。' }
Copy-Item -LiteralPath (Join-Path $dependencyDir 'LICENSE.txt') -Destination (Join-Path $outDir 'REFramework-LICENSE.txt')
$readme = if ($DiagnosticBuild) { 'support\使用说明.txt' } else { 'launcher\使用说明.txt' }
Copy-Item -LiteralPath (Join-Path $projectRoot $readme) -Destination (Join-Path $outDir '使用说明.txt')
# Only remove the intermediate file created at this exact, checked output path.
Remove-Item -LiteralPath $compressed
if ($CreateDesktopShortcut) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktop '鬼泣5 切人启动器.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $exe
    $shortcut.WorkingDirectory = $outDir
    $shortcut.Description = '设置下一位 / 上一位按键后启动鬼泣5'
    $gameExe = 'C:\Program Files (x86)\Steam\steamapps\common\Devil May Cry 5\DevilMayCry5.exe'
    $shortcut.IconLocation = if (Test-Path -LiteralPath $gameExe) { "$gameExe,0" } else { "$exe,0" }
    $shortcut.Save()
}
Get-Item -LiteralPath $exe | Select-Object FullName,Length
