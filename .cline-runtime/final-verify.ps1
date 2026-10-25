Write-Output '===== ZVERIS AUTO + API ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\ZVERIS_AUTO_LOG.txt' -Encoding UTF8 -Tail 5
Write-Output '===== ISTORIJOS FAILAI ====='
Get-Item 'C:\Users\M\CLINE\VISKAS\00_VISKAS_PILNA_ISTORIJA.md','C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md','C:\Users\M\CLINE\VISKAS\06_DABARTINE_BUSENA.md'|Select-Object Name,Length,LastWriteTime|Format-Table -AutoSize
Write-Output '===== DUOK NAUJAM ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\VISKAS\DUOK_NAUJAM_AI.txt' -Raw -Encoding UTF8
Write-Output '===== SERVISAI ====='
foreach($p in @(5678,8091,8766,8790,8792,8795,8099,9222)){{$ok=$false;try{{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',$p);$c.Close();$ok=$true}}catch{{}};Write-Output (':'+$p+'='+$ok)}}
