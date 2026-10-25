$python = 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe'
$script = 'C:\Users\M\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py'
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$out = "C:\Users\M\CLINE\f6-diagnostic-$stamp.out.log"
$err = "C:\Users\M\CLINE\f6-diagnostic-$stamp.err.log"
$p = Start-Process -FilePath $python -ArgumentList ('"' + $script + '"') -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Start-Sleep -Seconds 7
Write-Output ('PID=' + $p.Id + ' EXITED=' + $p.HasExited)
Write-Output '===== STDOUT ====='
if (Test-Path -LiteralPath $out) { Get-Content -LiteralPath $out -Raw -Encoding UTF8 }
Write-Output '===== STDERR ====='
if (Test-Path -LiteralPath $err) { Get-Content -LiteralPath $err -Raw -Encoding UTF8 }
Write-Output '===== HTTP ====='
try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8766/' -UseBasicParsing -TimeoutSec 5; Write-Output ('STATUS=' + $r.StatusCode + ' LENGTH=' + $r.Content.Length) } catch { Write-Output ('HTTP_ERROR=' + $_.Exception.Message) }
Write-Output '===== PROCESS ====='
Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)" | Select-Object ProcessId, Name, CommandLine | Format-List
