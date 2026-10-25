Write-Output '===== DABARTINE BUSENA ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\VISKAS\06_DABARTINE_BUSENA.md' -Encoding UTF8 -TotalCount 22
Write-Output '===== NAUJAUSIA / PILNA ====='
foreach($f in @('C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md','C:\Users\M\CLINE\VISKAS\00_VISKAS_PILNA_ISTORIJA.md')){ $x=Get-Item $f; Write-Output ($x.Name+' | '+$x.Length+' B | '+$x.LastWriteTime+' | automatika='+(Select-String -LiteralPath $f -SimpleMatch 'automatika ĮRODYTA' -Quiet)) }
Write-Output '===== NUORODOS ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\VISKAS\DUOK_NAUJAM_AI.txt' -Raw -Encoding UTF8
$ws=New-Object -ComObject WScript.Shell;$lnk=$ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'CLINE-SURINKTI.lnk'));Write-Output ('STARTUP='+$lnk.TargetPath+' '+$lnk.Arguments)
Write-Output '===== API ====='
Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue|Select-Object LocalPort,OwningProcess|Format-Table -AutoSize
