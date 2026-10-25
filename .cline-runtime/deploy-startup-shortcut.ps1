$ErrorActionPreference='Stop'
$target='C:\Users\M\CLINE\tools\startup-automation.ps1'
if(Test-Path -LiteralPath $target){throw 'Jau yra: '+$target}
[IO.File]::WriteAllBytes($target,[Convert]::FromBase64String('JEVycm9yQWN0aW9uUHJlZmVyZW5jZSA9ICdDb250aW51ZScKJHB5dGhvbiA9ICdDOlxVc2Vyc1xNXEFwcERhdGFcTG9jYWxcUHJvZ3JhbXNcUHl0aG9uXFB5dGhvbjMxMlxweXRob24uZXhlJwokY29sbGVjdG9yID0gJ0M6XFVzZXJzXE1cQ0xJTkVcdG9vbHNcc3VyaW5rdGktdmlza2EucHknCiRlbnN1cmUgPSAnQzpcVXNlcnNcTVxDTElORVx0b29sc1x6dmVyaXMtZW5zdXJlLnBzMScKJGxvZyA9ICdDOlxVc2Vyc1xNXENMSU5FXFNUQVJUVVBfQVVUT01BVElPTl9MT0cudHh0JwpmdW5jdGlvbiBMb2coW3N0cmluZ10kdGV4dCkgeyBBZGQtQ29udGVudCAtTGl0ZXJhbFBhdGggJGxvZyAtVmFsdWUgKCdbezB9XSB7MX0nIC1mIChHZXQtRGF0ZSAtRm9ybWF0ICd5eXl5LU1NLWRkIEhIOm1tOnNzJyksICR0ZXh0KSAtRW5jb2RpbmcgVVRGOCB9CnRyeSB7CiAgICAmICRweXRob24gLVggdXRmOCAkY29sbGVjdG9yIDI+JjEgfCBGb3JFYWNoLU9iamVjdCB7IExvZyAoJ1NVUklOS0lNQVM6ICcgKyAkXykgfQogICAgTG9nICgnU1VSSU5LSU1BU19FWElUPScgKyAkTEFTVEVYSVRDT0RFKQp9IGNhdGNoIHsgTG9nICgnU1VSSU5LSU1PX0tMQUlEQTogJyArICRfLkV4Y2VwdGlvbi5NZXNzYWdlKSB9CnRyeSB7CiAgICAmICdDOlxXaW5kb3dzXFN5c3RlbTMyXFdpbmRvd3NQb3dlclNoZWxsXHYxLjBccG93ZXJzaGVsbC5leGUnIC1Ob1Byb2ZpbGUgLU5vbkludGVyYWN0aXZlIC1FeGVjdXRpb25Qb2xpY3kgQnlwYXNzIC1GaWxlICRlbnN1cmUgMj4mMSB8IEZvckVhY2gtT2JqZWN0IHsgTG9nICgnWlZFUklTOiAnICsgJF8pIH0KICAgIExvZyAoJ1pWRVJJU19FWElUPScgKyAkTEFTVEVYSVRDT0RFKQp9IGNhdGNoIHsgTG9nICgnWlZFUklTX0tMQUlEQTogJyArICRfLkV4Y2VwdGlvbi5NZXNzYWdlKSB9Cg=='))
$startup=[Environment]::GetFolderPath('Startup')
$lnkPath=Join-Path $startup 'CLINE-SURINKTI.lnk'
if(Test-Path -LiteralPath $lnkPath){throw 'Nuoroda jau yra: '+$lnkPath}
$ws=New-Object -ComObject WScript.Shell
$lnk=$ws.CreateShortcut($lnkPath)
$lnk.TargetPath='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$lnk.Arguments='-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\M\CLINE\tools\startup-automation.ps1"'
$lnk.WorkingDirectory='C:\Users\M\CLINE'
$lnk.Description='CLINE - surinkti VISKAS istorija ir patikrinti Zveris paleidziant PC'
$lnk.Save()
$check=$ws.CreateShortcut($lnkPath)
Write-Output ('SHORTCUT='+$lnkPath)
Write-Output ('TARGET='+$check.TargetPath)
Write-Output ('ARGS='+$check.Arguments)
Get-Item -LiteralPath $target,$lnkPath|Select-Object FullName,Length,LastWriteTime|Format-Table -AutoSize
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $target 2>&1 | Out-String -Width 2000
Write-Output ('STARTUP_TEST_EXIT='+$LASTEXITCODE)
Get-Content -LiteralPath 'C:\Users\M\CLINE\STARTUP_AUTOMATION_LOG.txt' -Encoding UTF8 -Tail 10 -ErrorAction SilentlyContinue
