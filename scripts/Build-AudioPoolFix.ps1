[CmdletBinding()]
param([switch]$NoDeploy)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$native = Join-Path $project 'native\audio-pool-fix'
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (!(Test-Path -LiteralPath $vswhere)) { throw 'Visual Studio C++ build tools were not found.' }
$installation = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (!$installation) { throw 'Visual Studio x64 C++ compiler was not found.' }
$vcvars = Join-Path $installation 'VC\Auxiliary\Build\vcvars64.bat'
$build = Join-Path $native 'build'
New-Item -ItemType Directory -Path $build -Force | Out-Null
$commands = @(
    '@echo off',
    ('call "' + $vcvars + '"'),
    'if errorlevel 1 exit /b 1',
    'cl /nologo /O2 /MT /c /Fobuild\ deps\minhook-1.3.4\src\buffer.c deps\minhook-1.3.4\src\hook.c deps\minhook-1.3.4\src\trampoline.c deps\minhook-1.3.4\src\hde\hde64.c',
    'if errorlevel 1 exit /b 1',
    'ml64 /nologo /c /Fobuild\forwarders.obj forwarders.asm',
    'if errorlevel 1 exit /b 1',
    'cl /nologo /O2 /MT /EHsc /W4 /LD /Fobuild\audio_pool_fix.obj audio_pool_fix.cpp build\forwarders.obj build\buffer.obj build\hook.obj build\trampoline.obj build\hde64.obj /Fe:build\winmm.dll /link /DEF:winmm.def',
    'if errorlevel 1 exit /b 1',
    'cl /nologo /O2 /MT /EHsc /W4 /DPOOL_FIX_TEST /Fobuild\audio_pool_fix_test.obj audio_pool_fix.cpp /Fe:build\audio_pool_fix_test.exe',
    'if errorlevel 1 exit /b 1',
    'pushd build',
    'audio_pool_fix_test.exe --forwarder-test',
    'if errorlevel 1 exit /b 1',
    'popd'
)
[IO.File]::WriteAllLines((Join-Path $build 'compile.cmd'), $commands, [Text.Encoding]::ASCII)
Push-Location -LiteralPath $native
try {
    & $env:ComSpec /d /c 'build\compile.cmd'
    if ($LASTEXITCODE -ne 0) { throw 'Native audio fix build or forwarding tests failed.' }
} finally { Pop-Location }
if (!$NoDeploy) { Copy-Item -LiteralPath (Join-Path $build 'winmm.dll') -Destination (Join-Path $native 'winmm.dll') }
Get-FileHash -LiteralPath (Join-Path $build 'winmm.dll')
