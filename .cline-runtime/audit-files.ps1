$root='C:\Users\M\CLINE'
$v=Join-Path $root 'VISKAS'
Write-Output '===== VISKAS FAILAI ====='
$expected=@('VISKAS_VISKAS.md','00_SKAITYK_PIRMA.md','01_PRISIJUNGIMAI_IR_RAKTAI.md','02_ATLIKTI_DARBAI.md','03_SISTEMA_IR_SERVISAI.md','04_SIANDIENOS_TVARKYMAS.md','05_TODO.md','06_IRANKIAI.md','06_DABARTINE_BUSENA.md','07_SESIJA_2026-10-25.md','08_VISKAS_LOG.txt','09_ATSTATYMO_LOG.txt','viskas-atnaujinti.ps1','viskas-atstatyti.ps1','DUOK_NAUJAM_AI.txt')
foreach($name in $expected){$p=Join-Path $v $name;if(Test-Path -LiteralPath $p){$f=Get-Item -LiteralPath $p;Write-Output ($name+'|YRA|'+$f.Length+'|'+$f.LastWriteTime)}else{Write-Output ($name+'|NERA')}}
foreach($dir in @('SEIFAS','KODAS')){$p=Join-Path $v $dir;if(Test-Path -LiteralPath $p){$files=Get-ChildItem -LiteralPath $p -Recurse -File;Write-Output ($dir+'|failu='+$files.Count+'|bytes='+(($files|Measure-Object Length -Sum).Sum))}else{Write-Output ($dir+'|NERA')}}
Write-Output '===== DARBALAUKIO NUORODOS ====='
$desktop='C:\Users\M\Desktop';$shell=New-Object -ComObject WScript.Shell
foreach($name in @('CLINE VISKAS.lnk','CLINE ATSTATYTI.lnk','CLINE NUORODA.lnk','AUSYS.lnk','AKYS.lnk')){$p=Join-Path $desktop $name;if(Test-Path -LiteralPath $p){$s=$shell.CreateShortcut($p);Write-Output ($name+'|YRA|'+$s.TargetPath+'|'+$s.Arguments)}else{Write-Output ($name+'|NERA')}}
Write-Output '===== KOPIJU FAILAI ====='
$backupNames=@('pultas.py.bak-2026-10-25-cline','sesijos-pradzia.ps1.bak-2026-10-25-cline','sesijos-pradzia.ps1.bak2-2026-10-25-cline','vilkas-budejimas.ps1.bak-2026-10-25-cline','grafiko-CLINE_Budejimas.bak-2026-10-25.xml','pranesti.ps1.bak-2026-10-25-cline')
$searchRoots=@($root,(Join-Path $root 'tools'),(Join-Path $root 'pultas'))
foreach($name in $backupNames){$found=Get-ChildItem -LiteralPath $searchRoots -File -Filter $name -ErrorAction SilentlyContinue|Select-Object -First 1;if($found){Write-Output ($name+'|YRA|'+$found.Length+'|'+$found.FullName)}else{Write-Output ($name+'|NERA')}}
$kp='C:\Users\M\AppData\Local\Zveris\keepalive.ps1.bak-2026-10-25-cline';Write-Output ('keepalive backup|'+(Test-Path -LiteralPath $kp))
Write-Output '===== PULTAS IR SARGU KODAS ====='
$checks=@(
 @('pultas.py','Servisai veikia:'), @('pultas.py','PASEN'), @('pultas.py','NEVEIKIA'),
 @('..\tools\sesijos-pradzia.ps1','--headless=new'), @('..\tools\sesijos-pradzia.ps1','9222'),
 @('..\tools\vilkas-budejimas.ps1','8790'), @('..\tools\vilkas-budejimas.ps1','9222'), @('..\tools\vilkas-budejimas.ps1','8795'),
 @('..\tools\pranesti.ps1','ntfy.sh'), @('..\tools\pranesti.ps1','SMS')
)
foreach($c in $checks){$p=Join-Path (Join-Path $root 'pultas') $c[0];Write-Output ($c[0]+'|'+$c[1]+'|'+(Select-String -LiteralPath $p -SimpleMatch $c[1] -Quiet))}
$keep='C:\Users\M\AppData\Local\Zveris\keepalive.ps1';foreach($s in @('8091','8090','18765','182.224.239.168','desktop_bridge.py')){Write-Output ('keepalive|'+$s+'|'+(Select-String -LiteralPath $keep -SimpleMatch $s -Quiet))}
Write-Output '===== AUSYS AKYS VAST ====='
foreach($p in @((Join-Path $root 'AUSYS.txt'),(Join-Path $root 'ausys\ausys-server.py'),(Join-Path $root 'ausys\index.html'),(Join-Path $root 'akys\akys.ps1'),(Join-Path $root 'akys\NAUJAUSIA.txt'),(Join-Path $root 'tools\ffmpeg.exe'),(Join-Path $root 'vast-istrinta.txt'))){$f=Get-Item -LiteralPath $p -ErrorAction SilentlyContinue;if($f){Write-Output ($p+'|YRA|'+$f.Length)}else{Write-Output ($p+'|NERA')}}
$akysFiles=Get-ChildItem -LiteralPath (Join-Path $root 'akys') -File -ErrorAction SilentlyContinue
foreach($ext in @('png','mp4')){$group=$akysFiles|Where-Object { $_.Extension -eq ('.'+$ext) };Write-Output ('akys '+$ext+'|'+$group.Count)}
Get-Content -LiteralPath (Join-Path $root 'vast-istrinta.txt') -Encoding UTF8 -ErrorAction SilentlyContinue
