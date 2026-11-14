param([Parameter(Mandatory=$true)][string]$PayloadPackage,[Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if(Test-Path -LiteralPath $OutputDirectory){throw 'Use an empty output directory'}
$manifest=Get-Content -LiteralPath (Join-Path $root 'installer/manifest.json') -Raw|ConvertFrom-Json
foreach($f in $manifest.files){
 if((Get-FileHash -LiteralPath (Join-Path $PayloadPackage ('payload/'+$f.path))).Hash -ne $f.sha256){throw "Payload mismatch: $($f.path)"}
}
New-Item -ItemType Directory -Path $OutputDirectory|Out-Null
foreach($folder in @('payload','Licenses','SourceChanges')){Copy-Item -LiteralPath (Join-Path $PayloadPackage $folder) -Destination $OutputDirectory -Recurse}
Get-ChildItem -LiteralPath (Join-Path $root 'installer') -File|Copy-Item -Destination $OutputDirectory
& (Join-Path $PSScriptRoot 'Build-DesktopLauncher.ps1') -OutputDirectory $OutputDirectory
if(!(Test-Path -LiteralPath (Join-Path $OutputDirectory 'DMC5SwitchLauncher.exe'))){throw 'Launcher missing'}
