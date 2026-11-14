param()
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$native=Join-Path $root 'native\keyboard-input'
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vs=& $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if(!$vs){throw 'C++ compiler unavailable'}
New-Item -ItemType Directory -Force (Join-Path $native 'build') | Out-Null
$files=Get-ChildItem (Join-Path $native 'lua') -Filter '*.c' | Where-Object Name -NotIn @('lua.c','luac.c','onelua.c')
$args=($files | ForEach-Object {'lua\'+$_.Name}) -join ' '
$objects=($files | ForEach-Object {'build\'+$_.BaseName+'.obj'}) -join ' '
$commands=@('@echo off',('call "'+(Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat')+'"'), 'if errorlevel 1 exit /b 1',('cl /nologo /O2 /MT /c /Fobuild\ '+$args),'if errorlevel 1 exit /b 1',('lib /nologo /OUT:build\lua.lib '+$objects),'if errorlevel 1 exit /b 1','cl /nologo /O2 /MT /EHsc /W4 /LD keyboard_input.cpp build\lua.lib user32.lib /Fobuild\keyboard_input.obj /Fe:build\dmc5_keyboard.dll','if errorlevel 1 exit /b 1','cl /nologo /O2 /MT /EHsc test_host.cpp build\lua.lib /Fobuild\test_host.obj /Fe:build\test_host.exe','if errorlevel 1 exit /b 1','build\test_host.exe','if errorlevel 1 exit /b 1')
[IO.File]::WriteAllLines((Join-Path $native 'build\compile.cmd'),$commands,[Text.Encoding]::ASCII)
Push-Location $native
try{& $env:ComSpec /d /c build\compile.cmd;if($LASTEXITCODE){throw 'Keyboard build failed'}}finally{Pop-Location}
Copy-Item (Join-Path $native 'build\dmc5_keyboard.dll') (Join-Path $native 'dmc5_keyboard.dll')
