$roots=@('C:\Users\M\Desktop','C:\Users\M\CLINE\BACKUPS','C:\Users\M\CLINE\TRASH','C:\Users\M\CLINE\ISIMTA','C:\workspace')
Write-Output '===== INDEX.HTML FAILAI ====='
foreach($root in $roots){
 if(Test-Path -LiteralPath $root){
  Get-ChildItem -LiteralPath $root -Recurse -File -Filter 'index.html' -ErrorAction SilentlyContinue | ForEach-Object {
   $match=Select-String -LiteralPath $_.FullName -Pattern 'Žvėris|Zveris|Kareivis|anti-hallucination' -Quiet -ErrorAction SilentlyContinue
   Write-Output ($_.FullName+'|'+$_.Length+'|ZVERIS_MATCH='+$match)
  }
 }
}
Write-Output '===== ZVERIS HTML BAK KOPIJOS ====='
foreach($root in $roots){if(Test-Path -LiteralPath $root){Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue | Where-Object {$_.Name -match 'zveris.*\.(html|zip|bak)$|index\.html\.'} | Select-Object -First 80 FullName,Length,LastWriteTime | Format-Table -AutoSize}}
