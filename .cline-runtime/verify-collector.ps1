$short='C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md';$full='C:\Users\M\CLINE\VISKAS\00_VISKAS_PILNA_ISTORIJA.md'
Write-Output '===== TRUMPAS FAILAS ====='
Get-Item -LiteralPath $short|Select-Object Name,Length,LastWriteTime|Format-List
foreach($s in @('Perskaityk C:\Users\M\CLINE\VISKAS\00_SKAITYK_NAUJAUSIA.md','00_VISKAS_PILNA_ISTORIJA.md','DABARTINĖ BŪSENA','VISKAS VIENAME FAILE')){Write-Output ($s+'|'+(Select-String -LiteralPath $short -SimpleMatch $s -Quiet))}
Write-Output '===== PILNAS FAILAS ====='
Get-Item -LiteralPath $full|Select-Object Name,Length,LastWriteTime|Format-List
foreach($s in @('A) SERVISAI','B) AUKCIONAS','C) VPS','VISOS VIETINĖS CLINE SESIJOS','CLINE - Žvėris ir VISKAS automatiškai','clineAuto0000001')){Write-Output ($s+'|'+(Select-String -LiteralPath $full -SimpleMatch $s -Quiet))}
Write-Output '===== BUSENA ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\VISKAS\00_SURINKIMO_BUSENA.json' -Raw -Encoding UTF8
