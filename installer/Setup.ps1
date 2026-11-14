param([string]$GamePath,[ValidateSet('Install','Restore','Collect')][string]$Mode='Install',[ValidateSet('zh','en')][string]$Language,[switch]$NonInteractive)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$preference=Join-Path $PSScriptRoot 'language.txt'
if(!$Language){
 if(Test-Path -LiteralPath $preference){$Language=(Get-Content -LiteralPath $preference -Raw).Trim()}
 if($Language -notin @('zh','en')){$Language=if([Globalization.CultureInfo]::CurrentUICulture.Name -like 'zh*'){'zh'}else{'en'}}
}
$script:Language=$Language
. (Join-Path $PSScriptRoot 'Language.ps1')
function SwitchLanguage {
 $script:Language=if($script:Language -eq 'zh'){'en'}else{'zh'}
 try{[IO.File]::WriteAllText($preference,$script:Language)}catch{Write-Host (T 'NotSaved')}
}
if($NonInteractive){& (Join-Path $PSScriptRoot 'Engine.ps1') -GamePath $GamePath -Mode $Mode -Language $script:Language;return}
while($true){
 Clear-Host
 Write-Host ('=== '+(T 'Title')+' ===') -ForegroundColor Cyan
 Write-Host ''
 Write-Host ('  1  '+(T 'Install'))
 Write-Host ('  2  '+(T 'Collect'))
 Write-Host ('  3  '+(T 'Restore'))
 Write-Host '  L  中文 / English'
 Write-Host ('  0  '+(T 'Quit'))
 Write-Host '';Write-Host (T 'Hint')
 $key=[Console]::ReadKey($true).KeyChar.ToString().ToLowerInvariant()
 if($key -eq 'l'){SwitchLanguage;continue}
 if($key -eq '0'){return}
 if($key -notin @('1','2','3')){continue}
 $action=@{'1'='Install';'2'='Collect';'3'='Restore'}[$key]
 Write-Host '';Write-Host (T 'Working')
 try{& (Join-Path $PSScriptRoot 'Engine.ps1') -GamePath $GamePath -Mode $action -Language $script:Language | ForEach-Object {Write-Host $_}}
 catch{Write-Host (T 'Error') -ForegroundColor Red;Write-Host $_.Exception.Message -ForegroundColor Red}
 Write-Host '';Write-Host $(if($script:Language -eq 'zh'){'按任意键返回，按 L 切换语言。'}else{'Press any key to return, or L to switch language.'})
 if([Console]::ReadKey($true).KeyChar.ToString().ToLowerInvariant() -eq 'l'){SwitchLanguage}
}
