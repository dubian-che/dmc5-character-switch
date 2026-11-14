param([string]$OutputDirectory)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if(!$OutputDirectory){$OutputDirectory=Join-Path $root 'dist/DesktopLauncher'}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$compiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$exe=Join-Path $OutputDirectory 'DMC5SwitchLauncher.exe'
$sources=@('DesktopLauncher.cs','Dmc5SwitchLauncher.cs','ModInstaller.cs')|ForEach-Object {Join-Path $root ('launcher/'+$_)}
& $compiler /nologo /target:winexe /platform:anycpu /optimize+ /codepage:65001 /utf8output /define:DESKTOP_GUI /main:Dmc5SwitchLauncher.DesktopProgram "/out:$exe" "/win32manifest:$(Join-Path $root 'launcher/app.manifest')" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll /reference:System.Core.dll $sources
if($LASTEXITCODE){throw 'Desktop launcher compilation failed'}
Get-Item -LiteralPath $exe | Select-Object FullName,Length
