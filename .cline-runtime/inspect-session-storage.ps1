Write-Output '===== .CLINE SESIJOS ====='
$roots=@('C:\Users\M\.cline\data\sessions','C:\Users\M\AppData\Roaming\Code\User\globalStorage\saoudrizwan.claude-dev\tasks','C:\Users\M\AppData\Roaming\Cursor\User\globalStorage\saoudrizwan.claude-dev\tasks')
foreach($root in $roots){
 Write-Output ('--- '+$root+' ---')
 if(Test-Path -LiteralPath $root){
  $dirs=Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5
  foreach($d in $dirs){
   Write-Output ('DIR '+$d.Name+'|'+$d.LastWriteTime)
   Get-ChildItem -LiteralPath $d.FullName -File -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
  }
 } else { Write-Output 'NERA' }
}
Write-Output '===== KONTEKSTO SARGO KODAS ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\tools\konteksto-sargas.py' -Raw -Encoding UTF8
