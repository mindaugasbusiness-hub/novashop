$script = 'C:\Users\M\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py'
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$backupDir = "C:\Users\M\CLINE\BACKUPS\$stamp\Desktop\pakeitimai 111"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$backup = Join-Path $backupDir '_vilkas_global_hotkeys.py'
Copy-Item -LiteralPath $script -Destination $backup
$text = [IO.File]::ReadAllText($script)
$pattern = 'if ok1 and ok6 and ok7 and ok8 and ok9 and ok10 and ok11:\r?\n\s+return True'
$matches = [regex]::Matches($text, $pattern)
if ($matches.Count -ne 1) { throw "Nerasta lygiai viena keiciama vieta; rasta=$($matches.Count)" }
$replacement = "if ok6 and ok7 and ok8 and ok9 and ok10 and ok11:`r`n            if not ok1:`r`n                sys.stderr.write(`"ISPEJIMAS: F1 uzimtas kito proceso; F6-F11 veikia.`n`")`r`n            return True"
$newText = [regex]::Replace($text, $pattern, $replacement, 1)
[IO.File]::WriteAllText($script, $newText, [Text.UTF8Encoding]::new($false))
Write-Output ('BACKUP=' + $backup)
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -m py_compile $script
if ($LASTEXITCODE -ne 0) { throw 'Python sintakes patikra nepavyko' }
Write-Output 'PY_COMPILE=OK'
Select-String -LiteralPath $script -Pattern 'if ok6|F1 uzimtas' -Context 1,2
