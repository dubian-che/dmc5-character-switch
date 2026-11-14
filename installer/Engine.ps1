param([string]$GamePath,[ValidateSet('Install','Restore','Collect')][string]$Mode='Install',[ValidateSet('zh','en')][string]$Language='zh')
$script:Language=$Language
. (Join-Path $PSScriptRoot 'Language.ps1')
$ErrorActionPreference='Stop'
if(!$GamePath){
 Add-Type -AssemblyName System.Windows.Forms
 $picker=New-Object System.Windows.Forms.OpenFileDialog
 $picker.Title=(T 'Pick');$picker.Filter='Devil May Cry 5|DevilMayCry5.exe'
 if($picker.ShowDialog() -ne 'OK'){Write-Output (T 'Cancelled');return}
 $GamePath=Split-Path $picker.FileName -Parent
}
$GamePath=[IO.Path]::GetFullPath($GamePath)
if(!(Test-Path -LiteralPath (Join-Path $GamePath 'DevilMayCry5.exe'))){throw (T 'Folder')}
$manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw|ConvertFrom-Json
function Target([string]$relative){
 $full=[IO.Path]::GetFullPath((Join-Path $GamePath $relative))
 if(!$full.StartsWith($GamePath.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)){throw (T 'Path')}
 return $full
}
$backupBase=Join-Path $GamePath '.dmc5-test-20261114'
if($Mode -eq 'Collect'){
 $out=Join-Path ([Environment]::GetFolderPath('Desktop')) ('DMC5-Test-Diagnostics-'+(Get-Date -Format yyyyMMdd-HHmmss)+'.zip')
 $stage=Join-Path ([IO.Path]::GetTempPath()) ('DMC5-Diagnostics-'+[guid]::NewGuid())
 New-Item -ItemType Directory -Path $stage|Out-Null
 foreach($r in @('re2_framework_log.txt','Collab Trainer/Log/DMC5_collab_trainer_log.txt','reframework/data/dmc5_switch_config.json')){
  $p=Target $r;if(Test-Path -LiteralPath $p){Copy-Item -LiteralPath $p -Destination (Join-Path $stage ([IO.Path]::GetFileName($p)))}
 }
 $slots=Target 'reframework/data/dmc5_support'
 if(Test-Path -LiteralPath $slots){Copy-Item -LiteralPath $slots -Destination (Join-Path $stage 'dmc5_support') -Recurse}
 $hashes=foreach($f in $manifest.files){$p=Target $f.path;[pscustomobject]@{path=$f.path;hash=if(Test-Path -LiteralPath $p){(Get-FileHash -LiteralPath $p).Hash}else{'missing'}}}
 $hashes|ConvertTo-Json -Depth 4|Set-Content (Join-Path $stage 'installed-hashes.json') -Encoding UTF8
 Compress-Archive -LiteralPath (Get-ChildItem -LiteralPath $stage).FullName -DestinationPath $out
 Write-Output (T 'Exported' @($out));return
}
if(Get-Process DevilMayCry5 -ErrorAction SilentlyContinue){throw (T 'Running')}
if($Mode -eq 'Restore'){
 $latest=Join-Path $backupBase 'latest.txt'
 if(!(Test-Path -LiteralPath $latest)){throw (T 'NoBackup')}
 $backup=[IO.Path]::GetFullPath((Get-Content -LiteralPath $latest -Raw).Trim())
 if(!$backup.StartsWith($backupBase+'\',[StringComparison]::OrdinalIgnoreCase)){throw (T 'BackupPath')}
 $receipt=Get-Content -LiteralPath (Join-Path $backup 'receipt.json') -Raw|ConvertFrom-Json
 foreach($f in $receipt){$p=Target $f.path;if(!(Test-Path -LiteralPath $p) -or (Get-FileHash -LiteralPath $p).Hash -ne $f.installedHash){throw (T 'Changed' @($f.path))}}
 foreach($f in $receipt){$p=Target $f.path;if($f.existed){Copy-Item -LiteralPath (Join-Path $backup $f.path) -Destination $p -Force}else{Remove-Item -LiteralPath $p}}
 Write-Output (T 'Restored');return
}
if((Get-FileHash -LiteralPath (Target 'DevilMayCry5.exe')).Hash -ne $manifest.gameExeSha256){throw (T 'Version')}
foreach($f in $manifest.files){
 $null=Target $f.path
 $p=Join-Path (Join-Path $PSScriptRoot 'payload') $f.path
 if((Get-FileHash -LiteralPath $p).Hash -ne $f.sha256){throw (T 'Integrity' @($f.path))}
}
$backup=Join-Path $backupBase ((Get-Date -Format yyyyMMdd-HHmmss)+'-'+[guid]::NewGuid().ToString('N').Substring(0,6))
New-Item -ItemType Directory -Path $backup -Force|Out-Null
$receipt=@()
foreach($f in $manifest.files){
 $p=Target $f.path;$exists=Test-Path -LiteralPath $p
 if($f.preserveExisting -and $exists){continue}
 if($exists){$b=Join-Path $backup $f.path;New-Item -ItemType Directory -Path (Split-Path $b -Parent) -Force|Out-Null;Copy-Item -LiteralPath $p -Destination $b}
 $receipt+=@([pscustomobject]@{path=$f.path;existed=$exists;installedHash=$f.sha256})
}
$receipt|ConvertTo-Json -Depth 4|Set-Content -LiteralPath (Join-Path $backup 'receipt.json') -Encoding UTF8
try{
 foreach($f in $receipt){
  $p=Target $f.path;New-Item -ItemType Directory -Path (Split-Path $p -Parent) -Force|Out-Null
  Copy-Item -LiteralPath (Join-Path (Join-Path $PSScriptRoot 'payload') $f.path) -Destination $p -Force
  if((Get-FileHash -LiteralPath $p).Hash -ne $f.installedHash){throw (T 'Hash' @($f.path))}
 }
}catch{
 foreach($f in $receipt){$p=Target $f.path;if($f.existed){Copy-Item -LiteralPath (Join-Path $backup $f.path) -Destination $p -Force}elseif(Test-Path -LiteralPath $p){Remove-Item -LiteralPath $p}}
 throw
}
[IO.File]::WriteAllText((Join-Path $backupBase 'latest.txt'),$backup,[Text.UTF8Encoding]::new($false))
Write-Output (T 'Installed')
Write-Output (T 'Backup' @($backup))
