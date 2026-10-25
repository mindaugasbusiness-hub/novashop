Write-Output '===== N8N PROCESAS ====='
Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'n8n' -and $_.Name -match 'node|cmd|powershell'} | Select-Object ProcessId,Name,CommandLine | Format-List
Write-Output '===== DUOMENU BAZES ====='
foreach($root in @('C:\Users\M\Desktop\Kumstis\runtime\n8n-data','C:\Users\M\.n8n')){if(Test-Path -LiteralPath $root){Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.sqlite*' -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize}}
Write-Output '===== WORKFLOW FAILAI ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis' -File -Filter '*workflow*.json' -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== N8N STARTAS ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\tools\start-n8n.cmd' -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
