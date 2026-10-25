Write-Output '===== 5678 SAVININKAS ====='
$conn=Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if($conn){Write-Output ('PID='+$conn.OwningProcess);Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)" | Select-Object ProcessId,ParentProcessId,Name,CommandLine | Format-List}else{Write-Output 'NĖRA'}
Write-Output '===== VISI N8N PROCESAI ====='
Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'node.exe' -and $_.CommandLine -match 'n8n'} | Select-Object ProcessId,ParentProcessId,CommandLine | Format-List
Write-Output '===== PIDS FAILAS ====='
Get-Content -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\pids.json' -Raw
Write-Output '===== NAUJO PROCESO BUSENA ====='
Get-Process -Id 5652 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime
