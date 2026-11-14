param([Parameter(Mandatory=$true)][string]$Launcher)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$test=Join-Path ([IO.Path]::GetTempPath()) ('dmc5-desktop-test-'+[guid]::NewGuid().ToString('N'))
$package=Join-Path $test 'package';$game=Join-Path $test 'game 中文 path'
New-Item -ItemType Directory -Path $package,$game,(Join-Path $package 'payload') -Force|Out-Null
Copy-Item -Path (Join-Path $root 'installer/*.ps1') -Destination $package
[IO.File]::WriteAllText((Join-Path $game 'DevilMayCry5.exe'),'test fixture; never executed')
[IO.File]::WriteAllText((Join-Path $game 'sample.txt'),'original')
[IO.File]::WriteAllText((Join-Path $package 'payload/sample.txt'),'replacement')
$m=@{version='1.0.0';gameExeSha256=(Get-FileHash (Join-Path $game 'DevilMayCry5.exe')).Hash;files=@(@{path='sample.txt';sha256=(Get-FileHash (Join-Path $package 'payload/sample.txt')).Hash;preserveExisting=$false})}
$m|ConvertTo-Json -Depth 5|Set-Content (Join-Path $package 'manifest.json') -Encoding UTF8
$null=[Reflection.Assembly]::LoadFrom([IO.Path]::GetFullPath($Launcher))
foreach($en in @($false,$true)){
 $null=[Dmc5SwitchLauncher.DesktopLauncher]::InvokeEngine($package,$game,'Install',$en)
 if([IO.File]::ReadAllText((Join-Path $game 'sample.txt')) -ne 'replacement'){throw 'Installation failed'}
 $null=[Dmc5SwitchLauncher.DesktopLauncher]::InvokeEngine($package,$game,'Restore',$en)
 if([IO.File]::ReadAllText((Join-Path $game 'sample.txt')) -ne 'original'){throw 'Restoration failed'}
}
$m.gameExeSha256='INVALID';$m|ConvertTo-Json -Depth 5|Set-Content (Join-Path $package 'manifest.json') -Encoding UTF8
$rejected=$false
try{$null=[Dmc5SwitchLauncher.DesktopLauncher]::InvokeEngine($package,$game,'Install',$true)}catch{$rejected=$true}
if(!$rejected -or [IO.File]::ReadAllText((Join-Path $game 'sample.txt')) -ne 'original'){throw 'Wrong-version guard failed'}
$config=[Dmc5SwitchLauncher.ConfigStore]::ConfigPath($game)
New-Item -ItemType Directory -Path (Split-Path $config -Parent) -Force|Out-Null
[IO.File]::WriteAllText($config,'{"customSentinel":123}')
$bindings=New-Object Dmc5SwitchLauncher.Bindings
$bindings.Next=116;$bindings.Previous=117;$bindings.PadPrevious='LT';$bindings.PadNext='RT'
[Dmc5SwitchLauncher.ConfigStore]::Save($config,$bindings)
$saved=Get-Content -LiteralPath $config -Raw|ConvertFrom-Json
if($saved.customSentinel -ne 123 -or $saved.padPrevious -ne 'LT' -or $saved.nextKey -ne 116){throw 'Settings preservation failed'}
[pscustomobject]@{passed=$true;fixture=$test;checks='desktop backend install/restore zh/en; Chinese paths; version refusal; settings preservation'}|ConvertTo-Json
