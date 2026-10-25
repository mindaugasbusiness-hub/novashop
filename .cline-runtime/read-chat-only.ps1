$file='C:\Users\M\Desktop\pakeitimai 111\_zveris_watch\ui_app.py'
$hit=Select-String -LiteralPath $file -Pattern '^@app.post\("/api/chat"'
$lines=Get-Content -LiteralPath $file -Encoding UTF8
if($hit){$lines|Select-Object -Skip ($hit.LineNumber-1) -First 75}
