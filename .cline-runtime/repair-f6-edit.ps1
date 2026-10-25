$script = 'C:\Users\M\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py'
$backup = 'C:\Users\M\CLINE\BACKUPS\2026-10-25_125157\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py'
Copy-Item -LiteralPath $backup -Destination $script -Force
$lines = [System.Collections.Generic.List[string]]::new()
Get-Content -LiteralPath $script -Encoding UTF8 | ForEach-Object { $lines.Add($_) }
$old = '        if ok1 and ok6 and ok7 and ok8 and ok9 and ok10 and ok11:'
$index = $lines.IndexOf($old)
if ($index -lt 0 -or $lines[$index + 1] -ne '            return True') { throw 'Nepavyko rasti tikslaus originalaus bloko' }
$lines[$index] = '        if ok6 and ok7 and ok8 and ok9 and ok10 and ok11:'
$lines.RemoveAt($index + 1)
$lines.Insert($index + 1, '            if not ok1:')
$lines.Insert($index + 2, '                sys.stderr.write("ISPEJIMAS: F1 uzimtas kito proceso; F6-F11 veikia.\n")')
$lines.Insert($index + 3, '            return True')
[IO.File]::WriteAllLines($script, $lines, [Text.UTF8Encoding]::new($false))
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -m py_compile $script 2>&1 | Out-String -Width 4096
if ($LASTEXITCODE -ne 0) { throw 'Python sintakes patikra nepavyko po taisymo' }
Write-Output 'PY_COMPILE=OK'
Get-Content -LiteralPath $script -Encoding UTF8 | Select-Object -Skip 328 -First 14
