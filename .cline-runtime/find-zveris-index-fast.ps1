$roots=@('C:\Users\M\CLINE\BACKUPS','C:\Users\M\CLINE\TRASH','C:\Users\M\CLINE\ISIMTA','C:\Users\M\Desktop\pakeitimai 111','C:\Users\M\Desktop\New folder','C:\workspace')
foreach($root in $roots){
 if(Test-Path -LiteralPath $root){
  Write-Output ('===== '+$root+' =====')
  Get-ChildItem -LiteralPath $root -Recurse -File -Filter 'index.html*' -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
 }
}
